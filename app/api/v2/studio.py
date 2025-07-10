from fastapi import APIRouter, Depends

from openai import AsyncOpenAI

from app.schemas.types import ChatCompletionRequest, ChatCompletionResponseChunk, ErrorResponse
from app.services.studio.studio import Studio
from app.utils.client.openai.openai_client import get_client

router = APIRouter(tags=["studio"])


async def get_studio(client: AsyncOpenAI = Depends(get_client)) -> Studio:
    svc = Studio(client)
    return svc


@router.post(
    "/v2/studio",
    summary="Create a Studio Mode chat completion",
    description="Pair-programming assistant using Studio class for planning and execution.",
    response_model=ChatCompletionResponseChunk,
    responses={
        400: {"model": ErrorResponse, "description": "Bad request"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def studio(
        request: ChatCompletionRequest,
        svc: Studio = Depends(get_studio),
):
    return await svc.execute(request)
