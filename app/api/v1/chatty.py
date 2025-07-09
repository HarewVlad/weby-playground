import time
from typing import AsyncGenerator

from fastapi import status, Depends, HTTPException, APIRouter
from openai import AsyncOpenAI, AsyncStream
from openai.types.chat import ChatCompletionChunk
from sse_starlette import EventSourceResponse

from app.components.config import Config
from app.components.prompts.chat import CHAT_SYSTEM_PROMPT
from app.schemas.types import ChatCompletionResponseChunk, ErrorResponse, ChatCompletionRequest
from app.utils.logger import logger
from app.utils.client.openai_client import get_client
from app.utils.client.serialize_object import serialize_object
from app.utils.schemas.sse_event import sse_event
from app.utils.client.verify_api_key import verify_api_key

router = APIRouter(tags=["chatty"])


@router.post(
    "/v1/chatty",
    summary="Create a streaming chat completion with file support",
    description="Create a streaming chat completion with the provided messages and optional file context. Returns "
                "Server-Sent Events (SSE) stream.",
    response_model=ChatCompletionResponseChunk,
    responses={
        200: {
            "description": "Server-Sent Events stream of chat completion chunks",
            "content": {
                "text/event-stream": {
                    "schema": {
                        "type": "string",
                        "example": 'data: {"data": {"id": "...", "object": "chat.completion.chunk", ...}}\n\n',
                    }
                }
            },
        },
        400: {"model": ErrorResponse, "description": "Bad request"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def chatty(
        request: ChatCompletionRequest,
        api_key: str = Depends(verify_api_key),
        client: AsyncOpenAI = Depends(get_client),
):
    logger.info(
        f"Processing chat completion request with {len(request.messages)} messages"
    )

    try:
        if request.project_files:
            logger.info(f"Request includes {len(request.project_files)} project files")

            project_files_context = []
            for file in request.project_files:
                file_context = f"""
Project file: {file.file_path}
```
{file.content}
```
"""
                project_files_context.append(file_context)

            project_files_context = "\n".join(project_files_context)
        else:
            project_files_context = ""

        messages = [
            {
                "role": "system",
                "content": CHAT_SYSTEM_PROMPT + project_files_context,
            }
        ]

        # Add conversation messages
        conversation_messages = [
            serialize_object(msg)
            for msg in request.messages[-Config.MAX_CHAT_HISTORY_SIZE:]
        ]

        # Process files if provided
        if request.uploaded_files:
            logger.info(
                f"Request includes {len(request.uploaded_files)} uploaded files"
            )

            uploaded_file_contexts = []
            for file in request.uploaded_files:
                file_context = f"""
File: {file.file_path}
```
{file.content}
```
"""
                uploaded_file_contexts.append(file_context)

            files_context = "\n".join(uploaded_file_contexts)

            # Add file context to the last user message or create a new context message
            if conversation_messages and conversation_messages[-1]["role"] == "user":
                # Append file context to the last user message
                conversation_messages[-1]["content"] = (
                        conversation_messages[-1]["content"]
                        + f"\n\n## Provided Files:\n{files_context}"
                )
            else:
                # Add a separate context message
                conversation_messages.append(
                    {"role": "user", "content": f"## Provided Files:\n{files_context}"}
                )

        messages.extend(conversation_messages)

        # Streaming response
        async def stream_generator() -> AsyncGenerator[dict, None]:
            """Generator for streaming chat response."""
            try:
                stream: AsyncStream[
                    ChatCompletionChunk
                ] = await client.chat.completions.create(
                    model=request.model,
                    messages=messages,
                    stream=True,
                    temperature=request.temperature,
                    top_p=request.top_p,
                    max_tokens=request.max_tokens,
                    extra_body={
                        "provider": {
                            "order": ["deepinfra/fp4"],
                            "allow_fallbacks": False,
                        }
                    },
                )

                # Stream chunks to the client
                async for chunk in stream:
                    response_chunk = ChatCompletionResponseChunk(data=chunk)
                    yield sse_event(response_chunk)

            except Exception as e:
                logger.exception(f"Error during chat streaming: {str(e)}")
                error_response = ChatCompletionResponseChunk(
                    error=ErrorResponse(
                        details=str(e),
                        status_code=500,
                        timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
                    )
                )
                yield sse_event(error_response)

        logger.info("Starting chat SSE response stream")
        return EventSourceResponse(stream_generator())

    except Exception as e:
        logger.exception(f"Error processing chat request: {str(e)}")

        if isinstance(e, HTTPException):
            raise e

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process chat request: {str(e)}",
        )
