import time

from fastapi import status, Depends, HTTPException, APIRouter
from openai import AsyncOpenAI

from app.components.prompts.features.project_name import PROJECT_NAME_SYSTEM_PROMPT
from app.schemas.types import ErrorResponse, ProjectNameResponse, \
    ProjectNameRequest
from app.components.config import Config
from app.utils.client.openai_client import get_client
from app.utils.client.verify_api_key import verify_api_key
from app.utils.logger import logger

router = APIRouter(tags=["project_name"])


@router.post(
    "/project_name",
    summary="Generate a project name",
    description="Generate a project name based on user input",
    response_model=ProjectNameResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse, "description": "Bad request"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def generate_project_name(
        request: ProjectNameRequest,
        api_key: str = Depends(verify_api_key),
        client: AsyncOpenAI = Depends(get_client),
):
    start_time = time.time()

    try:
        logger.info(f"Generating project name for prompt: '{request.prompt[:50]}...'")

        # Call the AI model to generate a project name
        completion = await client.chat.completions.create(
            model=Config.CODE_GENERATION_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": PROJECT_NAME_SYSTEM_PROMPT,
                },
                {"role": "user", "content": request.prompt},
            ],
            temperature=request.temperature,
            top_p=request.top_p,
        )

        # Extract the project name from the response
        project_name = completion.choices[0].message.content.strip()
        if not project_name:
            raise ValueError("Received empty project name from LLM")

        processing_time = time.time() - start_time
        logger.info(
            f"Project name '{project_name}' generated in {processing_time:.2f}s"
        )

        return ProjectNameResponse(
            project_name=project_name, processing_time=processing_time
        )

    except Exception as e:
        processing_time = time.time() - start_time
        logger.exception(f"Error generating project name: {str(e)}")

        if isinstance(e, HTTPException):
            raise e

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate project name: {str(e)}",
        )
