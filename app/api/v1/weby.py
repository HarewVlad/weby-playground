import time
from typing import AsyncGenerator

from fastapi import Depends, HTTPException, APIRouter
from openai import AsyncOpenAI, AsyncStream
from openai.types.chat import ChatCompletionChunk
from sse_starlette import EventSourceResponse
from starlette import status

from app.components.prompts.generation.flutter import FLUTTER_SYSTEM_PROMPT
from app.components.prompts.generation.html import HTML_SYSTEM_PROMPT
from app.schemas.types import ChatCompletionResponseChunk, ErrorResponse, ChatCompletionRequest
from app.components.config import Config
from app.utils.client.openai_client import get_client
from app.utils.client.serialize_object import serialize_object
from app.utils.client.verify_api_key import verify_api_key
from app.utils.logger import logger
from app.utils.schemas.sse_event import sse_event

router = APIRouter(tags=["weby"])


@router.post(
    "/v1/weby",
    summary="Create a streaming chat completion",
    description="Create a streaming chat completion with the provided messages. Returns Server-Sent Events (SSE) stream.",
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
async def weby(
        request: ChatCompletionRequest,
        api_key: str = Depends(verify_api_key),
        client: AsyncOpenAI = Depends(get_client),
):
    logger.info(f"Processing weby streaming request with framework={request.framework}")

    try:
        # Validate request
        if any(msg.role == "system" for msg in request.messages):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Overriding the default system prompt is not allowed",
            )

        # Prepare the appropriate system prompt based on framework
        if request.framework == "Nextjs":
            messages = [
                {
                    "role": "system",
                    "content": request.nextjs_system_prompt,
                }
            ]
        elif request.framework == "HTML":
            messages = [
                {
                    "role": "system",
                    "content": HTML_SYSTEM_PROMPT,
                }
            ]
        else:  # Flutter
            messages = [
                {
                    "role": "system",
                    "content": FLUTTER_SYSTEM_PROMPT,
                }
            ]

        # Add user messages, limiting to configured history size
        messages.extend(
            [
                serialize_object(msg)
                for msg in request.messages[-Config.MAX_CHAT_HISTORY_SIZE:]
            ]
        )

        # Include file context if provided
        # if request.project_files:
        #     logger.info(f"Request includes {len(request.project_files)} files")
        #     project_structure = [
        #         {"file_path": file.file_path, "content": file.content}
        #         for file in request.project_files
        #     ]
        #     project_context = (
        #         f"Additional files: {json.dumps(project_structure, indent=2)}\n\n"
        #     )

        #     if messages[-1]["role"] == "user":
        #         messages[-1]["content"] = (
        #             "Request: " + messages[-1]["content"] + project_context
        #         )

        # Streaming response
        async def stream_generator() -> AsyncGenerator[dict, None]:
            """Generator for streaming response."""
            try:
                stream: AsyncStream[
                    ChatCompletionChunk
                ] = await client.chat.completions.create(
                    model=request.model,
                    messages=messages,
                    stream=True,
                    temperature=request.temperature,
                    top_p=request.top_p,
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
                logger.exception(f"Error during streaming: {str(e)}")
                error_response = ChatCompletionResponseChunk(
                    error=ErrorResponse(
                        details=str(e),
                        status_code=500,
                        timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
                    )
                )
                yield sse_event(error_response)

        logger.info("Starting SSE response stream")
        return EventSourceResponse(stream_generator())

    except Exception as e:
        logger.exception(f"Error processing request: {str(e)}")

        if isinstance(e, HTTPException):
            raise e

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process request: {str(e)}",
        )
