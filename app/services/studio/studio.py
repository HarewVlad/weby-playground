import json

from xml.etree import ElementTree
from dataclasses import dataclass
from typing import List, AsyncGenerator, Any

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam
from pydantic import BaseModel
from sse_starlette import EventSourceResponse

from app.components.prompts.studio.planning import PLAN
from app.components.prompts.studio.studio import STUDIO
from app.components.prompts.studio.tools import TOOLS
from app.schemas.types import ChatCompletionRequest
from app.utils.schemas.sse_event import sse_event


@dataclass
class Step:
    title: str
    description: str


@dataclass
class Plan:
    task_title: str
    task_description: str
    steps: List[Step]


class SSEData(BaseModel):
    content: Any = None
    tool_calls: Any = None


class InterruptGeneration(Exception):
    """Raised to interrupt the overall step execution generation."""


class Studio:
    def __init__(self, client: AsyncOpenAI):
        self.client = client

    async def plan(self, request: ChatCompletionRequest, prompt: str) -> Plan:
        messages = [
            ChatCompletionSystemMessageParam(role="system", content=PLAN),
            ChatCompletionUserMessageParam(role="user", content=prompt)
        ]

        response = await self.client.chat.completions.create(
            model=request.model,
            messages=messages,
            temperature=request.temperature,
            top_p=request.top_p,
            max_tokens=request.max_tokens,
        )

        content = response.choices[0].message.content

        root: ElementTree
        try:
            root = ElementTree.fromstring(content)
        except ElementTree.ParseError:
            return Plan(task_title=content, task_description=content, steps=[Step(content, content)])

        title = root.findtext('task_title', default='').strip()
        description = root.findtext('task_description', default='').strip()
        steps: List[Step] = []
        steps_node = root.find('steps')

        if steps_node:
            for node in steps_node.findall('step'):
                steps.append(
                    Step(
                        title=node.findtext('title', '').strip(),
                        description=node.findtext('description', '').strip()
                    )
                )

        return Plan(task_title=title, task_description=description, steps=steps)

    async def execute(self, request: ChatCompletionRequest) -> EventSourceResponse:
        prompt_text = request.messages[-1].content
        plan = await self.plan(request, prompt_text)

        async def stream_all_steps() -> AsyncGenerator[dict | str, None]:
            plan_event = SSEData(
                content={
                    "type": "plan",
                    "task_title": plan.task_title,
                    "task_description": plan.task_description,
                    "steps": [step.title for step in plan.steps]
                },
                tool_calls=None
            )
            yield sse_event(plan_event)

            for step in plan.steps:
                try:
                    async for evt in self.execute_step(request, plan, step):
                        yield evt
                except InterruptGeneration:
                    return

        return EventSourceResponse(stream_all_steps())

    def execute_step(self, request: ChatCompletionRequest, plan: Plan, step: Step) -> AsyncGenerator[dict, None]:
        system_prompt = (
                STUDIO
                + f"\nCurrent Task: {plan.task_title}\nStep: {step.title} - {step.description}"
        )

        async def step_stream() -> AsyncGenerator[dict, None]:
            stream = await self.client.chat.completions.create(
                model=request.model,
                messages=[
                    ChatCompletionSystemMessageParam(role="system", content=system_prompt),
                    ChatCompletionUserMessageParam(role="user", content=step.description)
                ],
                stream=True,
                temperature=request.temperature,
                top_p=request.top_p,
                max_tokens=request.max_tokens,
                tools=TOOLS,
                tool_choice="auto"
            )

            ongoing_call: dict[str, str] | None = None

            async for chunk in stream:
                delta = chunk.choices[0].delta
                finish = getattr(chunk.choices[0], 'finish_reason', None)

                if getattr(delta, 'tool_calls', None):
                    for call in delta.tool_calls:
                        if ongoing_call is None:
                            ongoing_call = {"name": call.function.name or "", "arguments": ""}
                        ongoing_call["arguments"] += call.function.arguments or ""
                    continue

                if finish == "tool_calls" and ongoing_call:
                    try:
                        parsed_args = json.loads(ongoing_call["arguments"])
                    except Exception:
                        parsed_args = {}

                    calls = [{"name": ongoing_call["name"], "arguments": parsed_args}]
                    data = SSEData(content=None, tool_calls=calls)

                    yield sse_event(data)

                    if ongoing_call["name"] not in ("write_file", "edit_file"):
                        await stream.close()
                        raise InterruptGeneration()

                if delta.content:
                    data = SSEData(content=delta.content, tool_calls=None)
                    yield sse_event(data)

            if ongoing_call:
                try:
                    parsed_args = json.loads(ongoing_call["arguments"])
                except Exception:
                    parsed_args = {}
                calls = [{"name": ongoing_call["name"], "arguments": parsed_args}]
                yield sse_event(SSEData(content=None, tool_calls=calls))

        return step_stream()
