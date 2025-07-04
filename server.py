import logging
import time
from functools import lru_cache
from typing import Dict, List, Optional, Literal, Any, Union, AsyncGenerator

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
from openai import AsyncOpenAI, AsyncStream
from openai.types.chat import ChatCompletionChunk
from pydantic import BaseModel, Field, validator, ConfigDict
from sse_starlette.sse import EventSourceResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest

from config import Config


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("weby_api.log"),
    ],
)
logger = logging.getLogger("weby_api")


# Models with enhanced validation
class Message(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["user", "assistant"] = Field(
        ..., description="The role of the message author"
    )
    content: str = Field(..., description="The content of the message")

    @validator("content")
    def content_not_empty(cls, v):
        if not v.strip():
            raise ValueError("Message content cannot be empty")
        return v


class BaseFileItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str = Field(..., description="Content of the file")

    @validator("content")
    def validate_content(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Content cannot be empty")
        return v


class ProjectFileItem(BaseFileItem):
    file_path: str = Field(
        ..., description="Relative path to the file within the project"
    )

    @validator("file_path")
    def validate_file_path(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("File path cannot be empty")
        return v.strip()


class UploadedFileItem(BaseFileItem):
    file_name: str = Field(..., description="Original name of the uploaded file")

    @validator("file_name")
    def validate_file_name(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("File name cannot be empty")
        return v.strip()


class ChatCompletionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    messages: List[Message] = Field(
        ..., description="A list of messages comprising the conversation so far"
    )
    project_files: Optional[List[ProjectFileItem]] = Field(
        default=[], description="A list of project files with their paths and contents"
    )
    uploaded_files: Optional[List[UploadedFileItem]] = Field(
        default=[], description="A list of files with their names and contents"
    )
    temperature: Optional[float] = Field(
        default=0.6, ge=0.0, le=1.0, description="Controls randomness in the response"
    )
    top_p: Optional[float] = Field(
        default=0.95, ge=0.0, le=1.0, description="Controls the nucleus sampling"
    )
    max_tokens: Optional[int] = Field(
        default=16384, description="Maximum tokens in response"
    )
    framework: Optional[Literal["Nextjs", "Flutter", "HTML"]] = Field(
        default="Nextjs", description="The framework to use for code generation"
    )
    model: Optional[str] = Field(
        default=Config.CODE_GENERATION_MODEL,
        description="Model for code generation",
    )
    nextjs_system_prompt: Optional[str] = Field(
        default=Config.NEXTJS_SYSTEM_PROMPT, description="Nexj.js system prompt"
    )

    @validator("messages")
    def validate_messages(cls, v):
        if not v:
            raise ValueError("At least one message is required")
        return v


class ErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    details: str
    status_code: int = Field(default=500)
    timestamp: str = Field(default_factory=lambda: time.strftime("%Y-%m-%d %H:%M:%S"))


class ChatCompletionResponseChunk(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: Optional[ChatCompletionChunk] = Field(default=None)
    error: Optional[ErrorResponse] = Field(default=None)


# TODO: Combine with /weby, many similar fields
class PromptEnhanceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: Message = Field(..., description="The user message to enhance")
    temperature: Optional[float] = Field(
        default=0.6, ge=0.0, le=1.0, description="Controls randomness in the response"
    )
    top_p: Optional[float] = Field(
        default=0.95, ge=0.0, le=1.0, description="Controls the nucleus sampling"
    )
    model: Optional[str] = Field(
        default=Config.CODE_GENERATION_MODEL,
        description="Model for prompt enhance",
    )


class PromptEnhanceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enhanced_message: Message = Field(..., description="The enhanced user message")
    processing_time: float = Field(
        ..., description="Time taken to process the request in seconds"
    )


class ProjectNameRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prompt: str = Field(..., description="User input to generate a project name from")
    temperature: Optional[float] = Field(
        default=0.7, ge=0.0, le=1.0, description="Controls randomness in the response"
    )
    top_p: Optional[float] = Field(
        default=0.95, ge=0.0, le=1.0, description="Controls the nucleus sampling"
    )

    @validator("prompt")
    def prompt_not_empty(cls, v):
        if not v.strip():
            raise ValueError("Prompt cannot be empty")
        return v


class ProjectNameResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_name: str = Field(..., description="Generated project name")
    processing_time: float = Field(
        ..., description="Time taken to process the request in seconds"
    )


# API Key Authorization
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


# Rate limiting middleware
class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, rate_limit_per_minute: int = 60):
        super().__init__(app)
        self.rate_limit = rate_limit_per_minute
        self.requests = {}

    async def dispatch(self, request: StarletteRequest, call_next):
        client_ip = request.client.host
        current_time = time.time()

        # Clean up old entries
        self.requests = {
            ip: times
            for ip, times in self.requests.items()
            if any(t > current_time - 60 for t in times)
        }

        # Get or create request times for this IP
        request_times = self.requests.get(client_ip, [])

        # Filter to requests in the last minute
        request_times = [t for t in request_times if t > current_time - 60]

        # Check if rate limit exceeded
        if len(request_times) >= self.rate_limit:
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"error": "Rate limit exceeded. Please try again later."},
            )

        # Add this request
        request_times.append(current_time)
        self.requests[client_ip] = request_times

        # Process the request
        return await call_next(request)


# Request logging middleware
class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: StarletteRequest, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time

        logger.info(
            f"Request: {request.method} {request.url.path} - "
            f"Status: {response.status_code} - "
            f"Time: {process_time:.4f}s - "
            f"Client: {request.client.host}"
        )

        return response


# Create the FastAPI app with enhanced metadata
app = FastAPI(
    title="Weby API",
    description="Production-ready API for Weby code generation service",
    version="1.0.0",
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    contact={
        "name": "Weby Support",
        "email": "support@weby.example.com",
    },
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=Config.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    RateLimitMiddleware,
    rate_limit_per_minute=Config.RATE_LIMIT,
)


# Dependency for API key validation
async def verify_api_key(api_key: str = Depends(api_key_header)):
    if Config.API_KEYS:
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key is missing",
                headers={"WWW-Authenticate": "ApiKey"},
            )

        if not Config.API_KEYS or api_key not in Config.API_KEYS:
            logger.warning(f"Invalid API key attempt: {api_key[:5]}...")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid API key",
                headers={"WWW-Authenticate": "ApiKey"},
            )

    return api_key


# Cached OpenAI client to reduce connection overhead
@lru_cache(maxsize=1)
def get_openai_client():
    return AsyncOpenAI(
        base_url=Config.OPENAI_API_BASE,
        api_key=Config.OPENAI_API_KEY,
        timeout=Config.TIMEOUT,
    )


async def get_client():
    return get_openai_client()

def serialize_object(obj: Any) -> dict:
    """Safely serialize objects to dictionaries."""
    if hasattr(obj, "model_dump"):
        # For newer Pydantic/OpenAI SDK versions
        return obj.model_dump()
    elif hasattr(obj, "dict"):
        # For older Pydantic/OpenAI SDK versions
        return obj.dict()
    else:
        # Fallback for other objects
        try:
            return dict(obj)
        except (TypeError, ValueError):
            logger.warning(f"Could not serialize object of type {type(obj)}")
            return {"error": "Unserializable object"}


def sse_event(data: BaseModel) -> dict:
    """Format data for Server-Sent Events."""
    return {"data": data.model_dump_json()}


@app.post(
    "/prompt_enhance",
    summary="Enhance a user prompt",
    description="Process a user message to enhance it for better response generation",
    response_model=PromptEnhanceResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse, "description": "Bad request"},
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
                {"role": "system", "content": Config.ENHANCER_SYSTEM_PROMPT},
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


@app.post(
    "/v1/chatty",
    summary="Create a streaming chat completion with file support",
    description="Create a streaming chat completion with the provided messages and optional file context. Returns Server-Sent Events (SSE) stream.",
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
                "content": Config.CHAT_SYSTEM_PROMPT + project_files_context,
            }
        ]

        # Add conversation messages
        conversation_messages = [
            serialize_object(msg)
            for msg in request.messages[-Config.MAX_CHAT_HISTORY_SIZE :]
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


@app.post(
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
                    "content": Config.PROJECT_NAME_SYSTEM_PROMPT,
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


@app.post(
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
                    "content": Config.HTML_SYSTEM_PROMPT,
                }
            ]
        else:  # Flutter
            messages = [
                {
                    "role": "system",
                    "content": Config.FLUTTER_SYSTEM_PROMPT,
                }
            ]

        # Add user messages, limiting to configured history size
        messages.extend(
            [
                serialize_object(msg)
                for msg in request.messages[-Config.MAX_CHAT_HISTORY_SIZE :]
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


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Enhanced HTTP exception handler with logging."""
    logger.warning(f"HTTP Exception: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            details=exc.detail,
            status_code=exc.status_code,
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
        ).model_dump(),
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled exceptions."""
    logger.exception(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            details=f"An unexpected error occurred: {str(exc)}",
            status_code=500,
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
        ).model_dump(),
    )


@app.get(
    "/health",
    summary="Health check",
    description="Check if the API is running and connected to required services",
    response_model=Dict[str, Union[str, Dict[str, str]]],
    status_code=status.HTTP_200_OK,
)
async def health_check():
    """Enhanced health check that verifies connectivity to external services."""
    health_status = {
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "services": {},
    }

    # Check OpenAI connectivity
    try:
        client = get_openai_client()
        # Just make a simple request to check connectivity
        await client.models.list()
        health_status["services"]["openai"] = "connected"
    except Exception as e:
        logger.warning(f"OpenAI health check failed: {str(e)}")
        health_status["services"]["openai"] = f"error: {str(e)[:100]}"

    return health_status


if __name__ == "__main__":
    # Print startup banner
    logger.info("=" * 50)
    logger.info("Starting Weby API Server")
    logger.info("Version: 1.0.0")
    logger.info(f"Environment: {'Production' if not Config.DEBUG else 'Development'}")
    logger.info("=" * 50)

    # Start the server
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8000,
        reload=Config.DEBUG,
        log_level="info",
    )
