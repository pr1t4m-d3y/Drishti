"""A scripted LLM for deterministic agent tests. No network, no credentials."""

from __future__ import annotations

from collections.abc import AsyncGenerator, Callable

from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types

Script = Callable[[set[str], types.Content | None, list[types.FunctionResponse]], list[types.Part]]


def tool_names(req: LlmRequest) -> set[str]:
    names: set[str] = set()
    for t in (req.config.tools if req.config and req.config.tools else []):
        for fd in getattr(t, "function_declarations", None) or []:
            names.add(fd.name)
    return names


class FakeLlm(BaseLlm):
    model: str = "fake-llm"
    script: Script
    calls: list[set[str]] = []

    model_config = {"arbitrary_types_allowed": True}

    async def generate_content_async(self, llm_request: LlmRequest, stream: bool = False) -> AsyncGenerator[LlmResponse, None]:
        names = tool_names(llm_request)
        self.calls.append(names)
        last = llm_request.contents[-1] if llm_request.contents else None
        responses = [p.function_response for p in (last.parts if last else []) if p.function_response]
        parts = self.script(names, last, responses)
        yield LlmResponse(
            content=types.Content(role="model", parts=parts),
            usage_metadata=types.GenerateContentResponseUsageMetadata(
                prompt_token_count=100, candidates_token_count=20, total_token_count=120),
        )


def call(name: str, **args) -> types.Part:
    return types.Part(function_call=types.FunctionCall(name=name, args=args))


def text(t: str) -> types.Part:
    return types.Part(text=t)
