import json
from typing import Dict, List, Optional, Literal

import uvicorn
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from openai import AsyncOpenAI, AsyncStream
from openai.types.chat import ChatCompletionChunk
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from config import Config


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
    framework: Optional[Literal["Nextjs", "Flutter"]] = Field(
        default="Nextjs", description="The framework to use for code generation"
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
            # model="deepseek/deepseek-chat-v3-0324:nitro",
            # model="thudm/glm-4-32b:nitro",
            model="qwen/qwen3-30b-a3b:nitro",
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

        if request.framework == "Nextjs":
            messages = [
                {
                    "role": "system",
                    "content": Config.NEXTJS_SYSTEM_PROMPT + "\n\n" + Config.SHADCN_DOCUMENTATION,
                }
            ]
        else:
            messages = [
                {
                    "role": "system",
                    "content": Config.FLUTTER_SYSTEM_PROMPT,
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
                    # model="deepseek/deepseek-chat-v3-0324:Lambda",
                    model="qwen/qwen3-235b-a22b:nitro",
                    messages=messages,
                    stream=True,
                    temperature=request.temperature,
                    top_p=request.top_p,
                )

                async for chunk in stream:
                    # Extract content safely from the chunk, regardless of its structure
                    openai_chunk = ChatCompletionResponseChunk(data=chunk)
                    # Forward the chunk to the client
                    yield sse_event(openai_chunk)

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
