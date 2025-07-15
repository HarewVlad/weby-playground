import json
from typing import Any, List, Dict

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam
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
                    ...(self.client.chat.completions.messages),
                ],
                stream=True,
                temperature=request.temperature,
                top_p=request.top_p,
                max_tokens=request.max_tokens,
                tools=TOOLS,
                tool_choice="auto"
            )

            ongoing_calls: List[Dict[str, str]] = []
            async for chunk in stream:
                delta = chunk.choices[0].delta
                finish = getattr(chunk.choices[0], 'finish_reason', None)

                if getattr(delta, 'tool_calls', None):
                    for call in delta.tool_calls:
                        if len(ongoing_calls) == 0 or call.function.name is not None:
                            ongoing_calls.append({"name": call.function.name or "", "arguments": ""})
                        ongoing_calls[len(ongoing_calls) - 1]["arguments"] += call.function.arguments or ""
                    continue

                if finish == "tool_calls" and len(ongoing_calls) > 0:
                    for call in ongoing_calls:
                        try:
                            parsed_args = json.loads(call["arguments"])
                        except Exception:
                            parsed_args = {}

                        calls = [{"name": call["name"], "arguments": parsed_args}]
                        yield sse_event(SSEData(content=None, tool_calls=calls))

                    await stream.close()

                if delta.content:
                    yield sse_event(SSEData(content=delta.content, tool_calls=None))

        return EventSourceResponse(stream_response())
