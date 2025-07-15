import csv
import io
import time
import xml.etree.ElementTree as ET
from typing import AsyncGenerator, List, Optional

from fastapi import Depends, HTTPException, APIRouter
from openai import AsyncOpenAI, AsyncStream
from openai.types.chat import (
    ChatCompletionChunk,
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
    ChatCompletionMessageParam,
)
from sse_starlette import EventSourceResponse
from starlette import status

from app.components.prompts.generation.flutter import FLUTTER_SYSTEM_PROMPT
from app.components.prompts.generation.html import HTML_SYSTEM_PROMPT
from app.components.prompts.features.image_parsing import IMAGE_PARSING_SYSTEM_PROMPT
from app.schemas.types import (
    ChatCompletionResponseChunk,
    ErrorResponse,
    ChatCompletionRequest,
    FileItem,
)
from app.components.config import Config
from app.utils.client.openai.openai_client import get_client
from app.utils.client.verify_api_key import verify_api_key
from app.utils.logger import logger
from app.utils.schemas.sse_event import sse_event

router = APIRouter(tags=["weby"])


def is_image_file(file_name: str) -> bool:
    if not file_name or "." not in file_name:
        return False

    file_extension = file_name.lower().split(".")[-1]
    return file_extension in ["jpg", "jpeg", "png"]


async def describe_image(content: str, file_name: str, client: AsyncOpenAI) -> str:
    try:
        logger.debug(f"Generating description for image: {file_name}")

        # Prepare the image for the API call, assuming content is in base64
        image_data = content
        if not content.startswith("data:image"):
            # If it's raw base64, add the data URL prefix
            file_extension = file_name.lower().split(".")[-1]
            mime_type = f"image/{'jpeg' if file_extension in ['jpg', 'jpeg'] else file_extension}"
            image_data = f"data:{mime_type};base64,{content}"

        messages = [
            ChatCompletionSystemMessageParam(
                role="system", content=IMAGE_PARSING_SYSTEM_PROMPT
            ),
            ChatCompletionUserMessageParam(
                role="user",
                content=[
                    {
                        "type": "text",
                        "text": f"Please describe this image from file '{file_name}' in detail. Focus on elements that might be relevant for web development or UI design.",
                    },
                    {"type": "image_url", "image_url": {"url": image_data}},
                ],
            ),
        ]

        response = await client.chat.completions.create(
            model="google/gemma-3-27b-it",
            messages=messages,
            max_tokens=1024,
            temperature=0.3,
            extra_body={
                "provider": {
                    "order": ["deepinfra/bf16"],
                    "allow_fallbacks": False,
                }
            },
        )

        description = response.choices[0].message.content
        return f"Image Description for {file_name}:\n{description}"

    except Exception as e:
        logger.error(f"Error generating description for image {file_name}: {str(e)}")
        return f"Image: {file_name} (description unavailable: {str(e)})"


def parse_csv_content(content: str, file_name: str) -> str:
    try:
        csv_reader = csv.DictReader(io.StringIO(content))
        rows = list(csv_reader)

        if not rows:
            return f"The CSV file '{file_name}' is empty."

        # Get headers from the first row
        headers = list(rows[0].keys())

        # Start building the markdown table
        output = [f"Data from {file_name}:\n"]

        # Add headers
        output.append("| " + " | ".join(headers) + " |")
        output.append("|" + " | ".join(["---"] * len(headers)) + "|")

        # Add rows
        for row in rows:
            output.append(
                "| " + " | ".join(str(row.get(h, "")) for h in headers) + " |"
            )

        return "\n".join(output)

    except Exception as e:
        # If parsing fails, try simple line-by-line approach
        try:
            lines = content.strip().split("\n")
            if not lines:
                return f"The CSV file '{file_name}' is empty."

            # Use the simple csv reader
            csv_reader = csv.reader(io.StringIO(content))
            rows = list(csv_reader)

            if not rows:
                return f"The CSV file '{file_name}' is empty."

            headers = rows[0]
            output = [f"Data from {file_name}:\n"]
            output.append("| " + " | ".join(headers) + " |")
            output.append("|" + " | ".join(["---"] * len(headers)) + "|")

            for row in rows[1:]:
                # Pad row if needed
                padded_row = row + [""] * (len(headers) - len(row))
                output.append("| " + " | ".join(padded_row[: len(headers)]) + " |")

            return "\n".join(output)

        except:
            # Last resort: return raw content
            return f"Data from {file_name} (raw format):\n{content}"


def parse_xml_content(content: str, file_name: str) -> str:
    try:
        root = ET.fromstring(content)

        output = [f"Data from {file_name}:\n"]

        def extract_data(elem: ET.Element, path: str = "") -> List[str]:
            """Extract data from XML elements in a flat format."""
            results = []

            # Build the current path
            current_path = f"{path}/{elem.tag}" if path else elem.tag

            # If element has text content, add it
            if elem.text and elem.text.strip():
                results.append(f"{current_path}: {elem.text.strip()}")

            # Add attributes
            for attr_name, attr_value in elem.attrib.items():
                results.append(f"{current_path}[@{attr_name}]: {attr_value}")

            # Process children
            for child in elem:
                results.extend(extract_data(child, current_path))

            return results

        # Extract all data
        data_lines = extract_data(root)
        output.extend(data_lines)

        return "\n".join(output)

    except ET.ParseError:
        # If XML parsing fails, try to extract key information
        try:
            # Simple pattern matching for common XML patterns
            lines = []
            for line in content.split("\n"):
                line = line.strip()
                if line and not line.startswith("<?") and not line.startswith("<!"):
                    # Remove XML tags but keep content
                    import re

                    text = re.sub(r"<[^>]+>", " ", line).strip()
                    if text:
                        lines.append(text)

            if lines:
                return f"Data from {file_name}:\n" + "\n".join(lines)
            else:
                return f"Data from {file_name} (raw format):\n{content}"

        except:
            return f"Data from {file_name} (raw format):\n{content}"


async def process_file_content(
    file_name: str, content: str, client: AsyncOpenAI
) -> str:
    if is_image_file(file_name):
        logger.debug(f"Processing image file: {file_name}")
        return await describe_image(content, file_name, client)

    # Determine file type by extension
    file_extension = file_name.lower().split(".")[-1] if "." in file_name else ""

    if file_extension == "csv":
        logger.debug(f"Using CSV parser for {file_name}")
        return parse_csv_content(content, file_name)
    elif file_extension == "xml":
        logger.debug(f"Using XML parser for {file_name}")
        return parse_xml_content(content, file_name)
    else:
        # For all other file types, return content as-is
        return f"File: {file_name}\n```\n{content}\n```"


async def process_files(files: List[FileItem], client: AsyncOpenAI) -> Optional[str]:
    if not files:
        return None

    processed_contents = []
    for file in files:
        processed_content = await process_file_content(
            file.filename, file.content, client
        )
        processed_contents.append(f"\n{processed_content}")

    return "\n".join(processed_contents)


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

        messages: List[ChatCompletionMessageParam] = []

        # Process project files
        if request.project_files:
            project_files_context = (
                "\nProject files:\n"
                + await process_files(request.project_files, client)
                or ""
            )
        else:
            project_files_context = ""

        # Prepare an appropriate system prompt based on the framework
        if request.framework == "Nextjs":
            messages = [
                ChatCompletionSystemMessageParam(
                    role="system",
                    content=request.nextjs_system_prompt + project_files_context,
                ),
            ]
        elif request.framework == "HTML":
            messages = [
                ChatCompletionSystemMessageParam(
                    role="system", content=HTML_SYSTEM_PROMPT + project_files_context
                )
            ]
        elif request.framework == "Flutter":
            messages = [
                ChatCompletionSystemMessageParam(
                    role="system", content=FLUTTER_SYSTEM_PROMPT + project_files_context
                )
            ]
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported framework",
            )

        # Add user messages, limiting to configured history size
        user_messages = [
            ChatCompletionUserMessageParam(role="user", content=msg.content)
            for msg in request.messages[-Config.MAX_CHAT_HISTORY_SIZE :]
        ]

        # Process uploaded files (with async support for images) and add to last user message
        uploaded_files_context = await process_files(request.uploaded_files, client)
        if uploaded_files_context:
            if user_messages and user_messages[-1]["role"] == "user":
                user_messages[-1] = ChatCompletionUserMessageParam(
                    role="user",
                    content=user_messages[-1]["content"]
                    + f"\n\n## Additional Context:\n{uploaded_files_context}",
                )
            else:
                logger.warning(
                    "Uploaded files were not added. Last message is not from the user"
                )

        # Add all user messages
        messages.extend(user_messages)

        # Streaming response
        async def stream_generator() -> AsyncGenerator[dict, None]:
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
