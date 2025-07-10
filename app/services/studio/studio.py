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


class Studio:
    def __init__(self, client: AsyncOpenAI):
        self.client = client

    async def plan(self, prompt: str) -> Plan:
        messages = [
            ChatCompletionSystemMessageParam(role="system", content=PLAN),
            ChatCompletionUserMessageParam(role="user", content=prompt)
        ]

        response = await self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.0,
            top_p=1.0,
            max_tokens=1024,
        )

        content = response.choices[0].message.content
        root = ElementTree.fromstring(content)

        title = root.findtext('task_title', default='').strip()
        description = root.findtext('task_description', default='').strip()
        steps: List[Step] = []
        steps_node = root.find('steps')

        if steps_node:
            for node in steps_node.findall('step'):
                steps.append(Step(
                    title=node.findtext('title', '').strip(),
                    description=node.findtext('description', '').strip()
                ))

        return Plan(task_title=title, task_description=description, steps=steps)

    async def execute(self, request: ChatCompletionRequest) -> EventSourceResponse:
        # Extract prompt and generate plan
        prompt_text = request.messages[-1].content
        plan = await self.plan(prompt_text)

        async def stream_all_steps() -> AsyncGenerator[dict | str, None]:
            # Plan event
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

            # Execute each step
            for step in plan.steps:
                async for evt in self.execute_step(plan, step):
                    yield evt

        return EventSourceResponse(stream_all_steps())

    def execute_step(self, plan: Plan, step: Step) -> AsyncGenerator[dict, None]:
        system_prompt = (
                STUDIO
                + f"\nCurrent Task: {plan.task_title}\nStep: {step.title} - {step.description}"
        )

        async def step_stream() -> AsyncGenerator[dict, None]:
            stream = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    ChatCompletionSystemMessageParam(role="system", content=system_prompt),
                    ChatCompletionUserMessageParam(role="user", content=step.description)
                ],
                stream=True,
                temperature=0.7,
                top_p=1.0,
                max_tokens=512,
                tools=TOOLS,
                tool_choice="auto",
            )
            async for chunk in stream:
                delta = chunk.choices[0].delta

                if getattr(delta, 'tool_calls', None):
                    calls = [{
                        "name": call.function.name,
                        "arguments": call.function.arguments
                    } for call in delta.tool_calls]
                    data = SSEData(content=None, tool_calls=calls)
                else:
                    data = SSEData(content=delta.content, tool_calls=None)
                yield sse_event(data)

        return step_stream()
