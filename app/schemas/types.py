import time
from typing import List, Optional, Literal, Any

from openai.types.chat import ChatCompletionChunk
from pydantic import BaseModel, Field, field_validator, ConfigDict

from app.components.config import Config
from app.components.prompts.generation.nextjs import NEXTJS_SYSTEM_PROMPT


# Models with enhanced validation
class Message(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["user", "assistant"] = Field(
        ..., description="The role of the message author"
    )
    content: str = Field(..., description="The content of the message")
    text: Optional[str] = Field(None, description="The text of the message")

    @field_validator("content")
    def content_not_empty(cls, v):
        if not v.strip():
            raise ValueError("Message content cannot be empty")
        return v


class FileItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str = Field(..., description="Content of the file")
    filename: str = Field(..., description="Original name of the uploaded file")

    @field_validator("content")
    def validate_content(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Content cannot be empty")
        return v

    @field_validator("filename")
    def validate_filename(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("File name cannot be empty")
        return v.strip()


class CodeCompletionRequest(BaseModel):
    model: str
    prompt: str
    max_tokens: int = 256
    temperature: float = 0.0
    top_p: float = 1.0
    stop: Optional[List[str]] = None
    suffix: Optional[str] = None
    stream: Optional[bool] = False


class ChatCompletionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    messages: List[Message] = Field(
        ..., description="A list of messages comprising the conversation so far"
    )
    project_files: Optional[List[FileItem]] = Field(
        default=[], description="A list of project files"
    )
    uploaded_files: Optional[List[FileItem]] = Field(
        default=[], description="A list of uploaded files"
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
        default=NEXTJS_SYSTEM_PROMPT, description="Nexj.js system prompt"
    )
    stream: Optional[bool] = Field(
        default=True,
        description="Use streaming mode for code generation",
    )
    frequency_penalty: Optional[float] = Field(None)
    presence_penalty: Optional[float] = Field(None)


class ErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    details: str
    status_code: int = Field(default=500)
    timestamp: str = Field(default_factory=lambda: time.strftime("%Y-%m-%d %H:%M:%S"))


class CodeCompletionResponseChunk(BaseModel):
    data: Optional[Any] = None
    error: Optional["ErrorResponse"] = None


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

    @field_validator("prompt")
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
