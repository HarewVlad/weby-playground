from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from openai import AsyncOpenAI
import json
import uvicorn

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
        base_url="https://openrouter.ai/api/v1", api_key=Config.OPENROUTER_API_KEY
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
                "The stream may include error objects like `{\"error\": \"...\"}` within the data field.\n\n"
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
)
async def weby(
    request: ChatCompletionRequest, client: AsyncOpenAI = Depends(get_client)
) -> StreamingResponse:
    try:
        if any(msg.role == "system" for msg in request.messages):
            raise HTTPException(
                status_code=400,
                detail="Overriding the default system prompt is not allowed",
            )

        messages = [{"role": "system", "content": Config.SYSTEM_PROMPT + "\n\n" + Config.SHADCN_DOCUMENTATION}]

        messages.extend([serialize_object(msg) for msg in request.messages])

        if request.files:
            project_structure = [
                {"file_path": file.file_path, "content": file.content}
                for file in request.files
            ]
            project_context = f"Current project structure: {json.dumps(project_structure, indent=2)}\n\n"

            if messages[-1]["role"] == "user":
                messages[-1]["content"] = project_context + "Request: " + messages[-1]["content"]

        async def generate():
            try:
                stream = await client.chat.completions.create(
                    model="deepseek/deepseek-r1-distill-llama-70b:nitro",
                    messages=messages,
                    stream=True,
                    temperature=request.temperature,
                    top_p=request.top_p,
                )

                async for chunk in stream:
                    chunk_data = serialize_object(chunk)
                    yield f"data: {json.dumps(chunk_data)}\n\n"

                yield "data: [DONE]\n\n"
            except Exception as e:
                error_data = {"error": str(e)}
                yield f"data: {json.dumps(error_data)}\n\n"
                yield "data: [DONE]\n\n"

        return StreamingResponse(generate(), media_type="text/event-stream")

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
