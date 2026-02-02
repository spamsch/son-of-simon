"""OpenAI LLM provider implementation."""

import json
from typing import Any

from openai import AsyncOpenAI

from macbot.providers.base import LLMProvider, LLMResponse, Message, ToolCall


class OpenAIProvider(LLMProvider):
    """LLM provider for OpenAI models."""

    def __init__(self, api_key: str, model: str = "gpt-4o") -> None:
        super().__init__(api_key, model)
        self.client = AsyncOpenAI(api_key=api_key)

    async def chat(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
        system_prompt: str | None = None,
    ) -> LLMResponse:
        """Send a chat completion request to OpenAI."""
        # Convert messages to OpenAI format
        openai_messages: list[dict[str, Any]] = []

        if system_prompt:
            openai_messages.append({"role": "system", "content": system_prompt})

        for msg in messages:
            openai_messages.append({"role": msg.role, "content": msg.content})

        # Build request kwargs
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": openai_messages,
        }

        if tools:
            # Convert from Anthropic-style to OpenAI-style tool format
            openai_tools = []
            for tool in tools:
                openai_tool = {
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool.get("description", ""),
                        "parameters": tool.get("input_schema", {}),
                    },
                }
                openai_tools.append(openai_tool)
            kwargs["tools"] = openai_tools

        # Make the API call
        response = await self.client.chat.completions.create(**kwargs)

        # Parse response
        choice = response.choices[0]
        message = choice.message

        content = message.content
        tool_calls = []

        if message.tool_calls:
            for tc in message.tool_calls:
                arguments = {}
                if tc.function.arguments:
                    try:
                        arguments = json.loads(tc.function.arguments)
                    except json.JSONDecodeError:
                        arguments = {"raw": tc.function.arguments}

                tool_calls.append(
                    ToolCall(
                        id=tc.id,
                        name=tc.function.name,
                        arguments=arguments,
                    )
                )

        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            stop_reason=choice.finish_reason,
            usage={
                "input_tokens": response.usage.prompt_tokens if response.usage else 0,
                "output_tokens": response.usage.completion_tokens if response.usage else 0,
            },
        )

    def format_tool_result(self, tool_call_id: str, result: str) -> Message:
        """Format a tool result for OpenAI's format."""
        # OpenAI expects tool results as tool messages
        return Message(role="tool", content=result)

    def format_tool_results_batch(
        self, tool_calls: list[ToolCall], results: list[str]
    ) -> list[dict[str, Any]]:
        """Format multiple tool results for OpenAI.

        Args:
            tool_calls: Original tool calls
            results: Results from executing the tools

        Returns:
            List of message dicts in OpenAI's expected format
        """
        return [
            {
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result,
            }
            for tc, result in zip(tool_calls, results)
        ]
