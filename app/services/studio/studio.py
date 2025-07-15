import json
from typing import Any, Dict

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionSystemMessageParam
from pydantic import BaseModel
from sse_starlette import EventSourceResponse

from app.components.prompts.studio.studio import STUDIO
from app.components.prompts.studio.tools import TOOLS
from app.schemas.types import ChatCompletionRequest
from app.utils.schemas.sse_event import sse_event


class SSEData(BaseModel):
    content: Any = None
    tool_calls: Any = None


class Studio:
    def __init__(self, client: AsyncOpenAI):
        self.client = client

    async def execute(self, request: ChatCompletionRequest) -> EventSourceResponse:
        system_prompt = STUDIO

        async def stream_response():
            stream = await self.client.chat.completions.create(
                model=request.model,
                messages=[
                    ChatCompletionSystemMessageParam(role="system", content=system_prompt),
                ] + request.messages,
                stream=True,
                temperature=request.temperature,
                top_p=request.top_p,
                max_tokens=request.max_tokens,
                tools=TOOLS,
                tool_choice="auto"
            )

            ongoing_call: Dict[str, str] | None = None
            async for chunk in stream:
                delta = chunk.choices[0].delta
                finish = getattr(chunk.choices[0], 'finish_reason', None)
                tool_calls = getattr(delta, 'tool_calls', []) or []

                if tool_calls is not None and len(tool_calls) > 0:
                    call = delta.tool_calls[0]

                    if call.function.name is not None:
                        if ongoing_call is not None:
                            try:
                                parsed_args = json.loads(ongoing_call["arguments"])
                            except Exception as e:
                                print(e)
                                parsed_args = {}

                            calls = [{"name": ongoing_call["name"], "arguments": parsed_args}]
                            yield sse_event(SSEData(content=None, tool_calls=calls))
                            ongoing_call = None

                        ongoing_call = {"name": call.function.name, "arguments": ""}

                    ongoing_call["arguments"] += call.function.arguments or ""
                    continue

                if (finish == "tool_calls" or len(tool_calls) == 0) and ongoing_call is not None:
                    try:
                        parsed_args = json.loads(ongoing_call["arguments"])
                    except Exception as e:
                        parsed_args = {}

                    calls = [{"name": ongoing_call["name"], "arguments": parsed_args}]
                    yield sse_event(SSEData(content=None, tool_calls=calls))

                    if finish == "tool_calls" and ongoing_call["name"] not in ["write_file", "edit_file"]:
                        await stream.close()

                    ongoing_call = None

                if delta.content:
                    yield sse_event(SSEData(content=delta.content, tool_calls=None))

        return EventSourceResponse(stream_response())
