import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import List, AsyncGenerator, Any

from fastapi.responses import StreamingResponse
from openai import AsyncOpenAI
from pydantic import BaseModel

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
        # Generate structured plan via planning prompt
        messages = [
            {"role": "system", "content": PLAN},
            {"role": "user", "content": prompt}
        ]
        response = await self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.0,
            top_p=1.0,
            max_tokens=1024,
        )
        content = response.choices[0].message.content
        root = ET.fromstring(content)
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

    async def execute(self, request: ChatCompletionRequest) -> StreamingResponse:
        # Extract last user prompt text
        prompt_text = request.messages[-1].content
        # Generate plan
        plan = await self.plan(prompt_text)

        async def stream_all_steps() -> AsyncGenerator[str, None]:
            # Emit plan metadata as SSE
            plan_event = SSEData(content={
                "type": "plan",
                "task_title": plan.task_title,
                "task_description": plan.task_description,
                "steps": [step.title for step in plan.steps]
            })
            event_dict = sse_event(plan_event)
            yield event_dict['data'] + "\n\n"

            # Execute each step
            for step in plan.steps:
                async for sse_chunk in self.execute_step(plan, step):
                    yield sse_chunk

        from sse_starlette import EventSourceResponse
        # Return SSE-formatted response
        return EventSourceResponse(stream_all_steps())

    def execute_step(self, plan: Plan, step: Step) -> AsyncGenerator[str, None]:
        # Build per-step system prompt
        system_prompt = STUDIO + (
            f"\nCurrent Task: {plan.task_title}\n"
            f"Step: {step.title} - {step.description}"
        )

        async def step_stream() -> AsyncGenerator[str, None]:
            # Stream LLM responses and tool calls
            stream = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": step.description}
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
                # If tool_calls present, extract name and arguments
                if hasattr(delta, 'tool_calls') and delta.tool_calls:
                    calls = []
                    for call in delta.tool_calls:
                        calls.append({
                            "name": call.function.name,
                            "arguments": call.function.arguments
                        })
                    data = SSEData(content=None, tool_calls=calls)
                else:
                    data = SSEData(content=delta.content, tool_calls=None)
                event_dict = sse_event(data)
                yield event_dict['data'] + "\n\n"

        return step_stream()