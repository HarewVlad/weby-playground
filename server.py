import json
import os
import re
from typing import Dict, List, Optional

import uvicorn
import aiohttp
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from openai import AsyncOpenAI, AsyncStream
from openai.types.chat import ChatCompletionChunk
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from config import Config
from utils import fix_lucide_imports_filtered


# Configuration for Next.js server
NEXTJS_SERVER_URL = os.environ.get("NEXTJS_SERVER_URL", "http://localhost:3000")


class Message(BaseModel):
    role: str = Field(
        ..., description="The role of the message author (system, user, or assistant)"
    )
    content: str = Field(..., description="The content of the message")


class FileItem(BaseModel):
    file_path: str = Field(..., description="Path to the file")
    content: str = Field(..., description="Content of the file")


class ChatCompletionRequest(BaseModel):
    messages: List[Message] = Field(
        ..., description="A list of messages comprising the conversation so far"
    )
    files: Optional[List[FileItem]] = Field(
        default=[], description="A list of files with their paths and contents"
    )
    temperature: Optional[float] = Field(
        default=0.6, ge=0.0, le=1.0, description="Controls randomness in the response"
    )
    top_p: Optional[float] = Field(
        default=0.95, ge=0.0, le=1.0, description="Controls the nucleus sampling"
    )


class ErrorResponse(BaseModel):
    details: str


class ChatCompletionResponseChunk(BaseModel):
    data: ChatCompletionChunk | None = Field(default=None)
    error: ErrorResponse | None = Field(default=None)


class PromptEnhanceRequest(BaseModel):
    message: Message = Field(..., description="The user message to enhance")
    temperature: Optional[float] = Field(
        default=0.6, ge=0.0, le=1.0, description="Controls randomness in the response"
    )
    top_p: Optional[float] = Field(
        default=0.95, ge=0.0, le=1.0, description="Controls the nucleus sampling"
    )


class PromptEnhanceResponse(BaseModel):
    enhanced_message: Message = Field(..., description="The enhanced user message")


app = FastAPI(
    title="Weby API",
    description="Weby server using FastAPI",
    version="1.0.0",
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def get_client():
    return AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=Config.OPENROUTER_API_KEY,
        timeout=Config.TIMEOUT,
    )


def serialize_object(obj):
    if hasattr(obj, "model_dump"):
        # For newer Pydantic/OpenAI SDK versions
        return obj.model_dump()
    elif hasattr(obj, "dict"):
        # For older Pydantic/OpenAI SDK versions
        return obj.dict()
    else:
        # Fallback for other objects
        return dict(obj)


def sse_event[T: BaseModel](data: T) -> dict:
    return {"data": data.model_dump_json()}


def extract_content_from_chunk(chunk):
    """
    Extract content from the specific chunk structure we're receiving.
    Returns an empty string if no content can be found.
    """
    try:
        # The chunk is a dictionary with a 'data' key containing a JSON string
        if isinstance(chunk, dict) and "data" in chunk:
            # Parse the JSON string in 'data'
            data_json = json.loads(chunk["data"])

            # Navigate to the content field
            if (
                "data" in data_json
                and "choices" in data_json["data"]
                and data_json["data"]["choices"]
            ):
                choice = data_json["data"]["choices"][0]
                if "delta" in choice and "content" in choice["delta"]:
                    return choice["delta"]["content"] or ""

        # Fallback for different structures
        return ""
    except Exception as e:
        print(f"Error extracting content from chunk: {e}")
        print(f"Chunk structure: {chunk}")
        return ""


async def process_edit_tags(text):
    """Process edit tags in the text and send changes to the Next.js update endpoint."""
    # Define a pattern to match edit tags
    pattern = r'<Edit filename="([^"]+)">(.+?)</Edit>'

    # Find all matches
    matches = re.findall(pattern, text, re.DOTALL)

    async with aiohttp.ClientSession() as session:
        # Process each match
        for _, content in matches:
            # Remove potential Markdown
            lines = content.splitlines()
            while lines and (not lines[0].strip() or lines[0].strip() == "```tsx"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            content = "\n".join(lines)

            # Prepare the payload
            file_path = "src/app/page.tsx"

            payload = {
                "file_path": file_path,
                "content": fix_lucide_imports_filtered(content, Config.LUCIDE_ICONS),
            }

            try:
                # Send the content to the Next.js update endpoint
                update_url = f"{NEXTJS_SERVER_URL}/update"
                async with session.post(update_url, json=payload) as response:
                    response_data = await response.json()

                    if response.status != 200:
                        print(f"Error updating file {file_path}: {response_data}")
                    else:
                        print(f"Successfully updated file: {file_path}")

            except Exception as e:
                print(f"Error sending update request for {file_path}: {str(e)}")

    return text


@app.post(
    "/prompt-enhance",
    summary="Enhance a user prompt",
    description="Process a user message to enhance it for better response generation",
    response_model=PromptEnhanceResponse,
)
async def enhance_prompt(
    request: PromptEnhanceRequest, client: AsyncOpenAI = Depends(get_client)
):
    try:
        # Call the AI model to enhance the prompt
        completion = await client.chat.completions.create(
            model="deepseek/deepseek-chat-v3-0324:nitro",
            messages=[
                {"role": "system", "content": Config.ENHANCER_SYSTEM_PROMPT},
                serialize_object(request.message),
            ],
            temperature=request.temperature,
            top_p=request.top_p,
        )

        # Create enhanced message with same role but updated content
        enhanced_message = Message(
            role=request.message.role, content=completion.choices[0].message.content
        )

        return PromptEnhanceResponse(enhanced_message=enhanced_message)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post(
    "/v1/weby",
    summary="Create a streaming chat completion",
    description="Create a streaming chat completion with the provided messages",
    response_description="Streaming response with chunks of the completion",
    responses={
        200: {
            "description": (
                "A stream of Server-Sent Events (SSE).\n\n"
                "Each event follows the format: `data: <json_object>\\n\\n`.\n\n"
                "The `<json_object>` represents a chunk of the chat completion, "
                "typically conforming to the `ChatCompletionChunk` schema.\n\n"
                'The stream may include error objects like `{"error": "..."}` within the data field.\n\n'
                "The stream terminates with a final event: `data: [DONE]\\n\\n`."
            ),
            "content": {
                "text/event-stream": {
                    "schema": {
                        "type": "string",
                        "description": "Server-Sent Events stream. See endpoint description for data format.",
                    }
                }
            },
        },
        400: {
            "description": "Bad Request - System prompt override not allowed",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "detail": {
                                "type": "string",
                                "example": "Overriding the default system prompt is not allowed",
                            }
                        },
                    }
                }
            },
        },
        500: {
            "description": "Internal Server Error",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "error": {
                                "type": "string",
                                "example": "An unexpected error occurred",
                            }
                        },
                    }
                }
            },
        },
    },
    response_model=ChatCompletionResponseChunk,
)
async def weby(
    request: ChatCompletionRequest, client: AsyncOpenAI = Depends(get_client)
):
    try:
        if any(msg.role == "system" for msg in request.messages):
            raise HTTPException(
                status_code=400,
                detail="Overriding the default system prompt is not allowed",
            )

        messages = [
            {
                "role": "system",
                "content": Config.SYSTEM_PROMPT + "\n\n" + Config.SHADCN_DOCUMENTATION,
            }
        ]

        messages.extend(
            [
                serialize_object(msg)
                for msg in request.messages[-Config.MAX_CHAT_HISTORY_SIZE :]
            ]
        )

        if request.files:
            project_structure = [
                {"file_path": file.file_path, "content": file.content}
                for file in request.files
            ]
            project_context = f"Current project structure: {json.dumps(project_structure, indent=2)}\n\n"

            if messages[-1]["role"] == "user":
                messages[-1]["content"] = (
                    project_context + "Request: " + messages[-1]["content"]
                )

        async def generator():
            try:
                stream: AsyncStream[
                    ChatCompletionChunk
                ] = await client.chat.completions.create(
                    model="deepseek/deepseek-chat-v3-0324:Lambda",
                    messages=messages,
                    stream=True,
                    temperature=request.temperature,
                    top_p=request.top_p,
                )

                # Buffer to accumulate text for processing edit tags
                buffer = ""

                async for chunk in stream:
                    # Extract content safely from the chunk, regardless of its structure
                    openai_chunk = ChatCompletionResponseChunk(data=chunk)

                    content = openai_chunk.data.choices[0].delta.content
                    if content:
                        # Add to buffer for processing
                        buffer += content

                    # Forward the chunk to the client
                    yield sse_event(openai_chunk)

                # Process any remaining content in the buffer
                if buffer:
                    await process_edit_tags(buffer)

            except Exception as e:
                yield sse_event(
                    ChatCompletionResponseChunk(error=ErrorResponse(details=str(e))),
                )

        return EventSourceResponse(generator())

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"error": str(exc)},
    )


@app.get(
    "/health",
    summary="Health check",
    description="Check if the API is running",
    response_model=Dict[str, str],
)
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
