"""Anthropic (Claude) LLM provider implementation."""

import json
from typing import Any

from anthropic import AsyncAnthropic

from macbot.providers.base import LLMProvider, LLMResponse, Message, ToolCall


class AnthropicProvider(LLMProvider):
    """LLM provider for Anthropic's Claude models."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514") -> None:
        super().__init__(api_key, model)
        self.client = AsyncAnthropic(api_key=api_key)

    async def chat(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
        system_prompt: str | None = None,
    ) -> LLMResponse:
        """Send a chat completion request to Claude."""
        # Convert messages to Anthropic format
        anthropic_messages = []
        for msg in messages:
            if msg.role == "system":
                # System messages are handled separately in Anthropic
                continue
            anthropic_messages.append({"role": msg.role, "content": msg.content})

        # Build request kwargs
        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": 4096,
            "messages": anthropic_messages,
        }

        if system_prompt:
            kwargs["system"] = system_prompt

        if tools:
            kwargs["tools"] = tools

        # Make the API call
        response = await self.client.messages.create(**kwargs)

        # Parse response
        content = None
        tool_calls = []

        for block in response.content:
            if block.type == "text":
                content = block.text
            elif block.type == "tool_use":
                tool_calls.append(
                    ToolCall(
                        id=block.id,
                        name=block.name,
                        arguments=dict(block.input) if block.input else {},
                    )
                )

        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            stop_reason=response.stop_reason,
            usage={
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            },
        )

    def format_tool_result(self, tool_call_id: str, result: str) -> Message:
        """Format a tool result for Anthropic's format."""
        # Anthropic expects tool results as user messages with tool_result content
        content = json.dumps(
            [{"type": "tool_result", "tool_use_id": tool_call_id, "content": result}]
        )
        return Message(role="user", content=content)

    def format_tool_results_batch(
        self, results: list[tuple[str, str]]
    ) -> dict[str, Any]:
        """Format multiple tool results for Anthropic.

        Args:
            results: List of (tool_call_id, result) tuples

        Returns:
            Message dict in Anthropic's expected format
        """
        return {
            "role": "user",
            "content": [
                {"type": "tool_result", "tool_use_id": tool_id, "content": result}
                for tool_id, result in results
            ],
        }
