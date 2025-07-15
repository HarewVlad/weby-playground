import time
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, status
from openai import AsyncOpenAI, AsyncStream
from openai.types.completion import Completion
from sse_starlette import EventSourceResponse

from app.schemas.types import CodeCompletionRequest, ErrorResponse, CodeCompletionResponseChunk
from app.utils.client.openai.openai_client import get_client
from app.utils.schemas.sse_event import sse_event
from app.utils.logger import logger

router = APIRouter(tags=["code-completion"])


@router.post(
    "/v1/completions",
    summary="Native Code Completion Endpoint (OpenAI-Compatible)",
    description="Streams raw text completions (non-chat) for IDE-like code completion.",
    response_model=CodeCompletionResponseChunk
)
async def native_code_completion(
    request: CodeCompletionRequest,
    client: AsyncOpenAI = Depends(get_client),
):
    try:
        logger.info("Received native code completion request")

        async def stream_response() -> AsyncGenerator[dict, None]:
            try:
                stream: AsyncStream[Completion] = await client.completions.create(
                    model=request.model,
                    prompt=request.prompt,
                    stream=True,
                    max_tokens=request.max_tokens,
                    temperature=request.temperature,
                    top_p=request.top_p,
                    stop=request.stop,
                    suffix=request.suffix,
                )

                async for chunk in stream:
                    yield sse_event(CodeCompletionResponseChunk(data=chunk))

            except Exception as stream_error:
                logger.exception("Streaming error")
                yield sse_event(CodeCompletionResponseChunk(
                    error=ErrorResponse(
                        details=str(stream_error),
                        status_code=500,
                        timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
                    )
                ))

        return EventSourceResponse(stream_response())

    except Exception as e:
        logger.exception("Code completion failed")

        if isinstance(e, HTTPException):
            raise e

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Code completion error: {str(e)}"
        )
