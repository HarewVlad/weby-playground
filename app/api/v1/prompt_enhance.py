import time

from fastapi import status, Depends, HTTPException, APIRouter
from openai import AsyncOpenAI

from app.components.prompts.features.prompt_enhance import ENHANCER_SYSTEM_PROMPT
from app.schemas.types import ErrorResponse, PromptEnhanceResponse, PromptEnhanceRequest, Message
from app.utils.client.openai_client import get_client
from app.utils.client.serialize_object import serialize_object
from app.utils.client.verify_api_key import verify_api_key
from app.utils.logger import logger

router = APIRouter(tags=["prompt_enhance"])


@router.post(
    "/prompt_enhance",
    summary="Enhance a user prompt",
    description="Process a user message to enhance it for better response generation",
    response_model=PromptEnhanceResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"modeА ты пl": ErrorResponse, "description": "Bad request"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def prompt_enhance(
        request: PromptEnhanceRequest,
        api_key: str = Depends(verify_api_key),
        client: AsyncOpenAI = Depends(get_client),
):
    start_time = time.time()

    try:
        # Input validation
        if request.message.role != "user":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only user messages can be enhanced",
            )

        logger.info(
            f"Enhancing prompt with temperature={request.temperature}, top_p={request.top_p}"
        )

        completion = await client.chat.completions.create(
            model=request.model,
            messages=[
                {"role": "system", "content": ENHANCER_SYSTEM_PROMPT},
                serialize_object(request.message),
            ],
            temperature=request.temperature,
            top_p=request.top_p,
        )

        # Create enhanced message with same role but updated content
        enhanced_content = completion.choices[0].message.content
        if not enhanced_content:
            raise ValueError("Received empty response from LLM")

        enhanced_message = Message(role=request.message.role, content=enhanced_content)

        processing_time = time.time() - start_time
        logger.info(f"Prompt enhanced successfully in {processing_time:.2f}s")

        return PromptEnhanceResponse(
            enhanced_message=enhanced_message, processing_time=processing_time
        )

    except Exception as e:
        processing_time = time.time() - start_time
        logger.exception(f"Error enhancing prompt: {str(e)}")

        if isinstance(e, HTTPException):
            raise e

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to enhance prompt: {str(e)}",
        )
