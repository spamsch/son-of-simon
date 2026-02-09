"""LiteLLM unified provider implementation.

Supports 100+ LLM providers through a single interface using the model string
format: provider/model (e.g., anthropic/claude-sonnet-4-20250514, openai/gpt-4o).
"""

import json
import os
import re
from typing import Any

import litellm

from macbot.providers.base import (
    LLMProvider,
    LLMResponse,
    Message,
    StreamCallback,
    ToolCall,
)


class LiteLLMProvider(LLMProvider):
    """Unified LLM provider using LiteLLM.

    Supports 100+ providers via model string format:
    - anthropic/claude-sonnet-4-20250514
    - openai/gpt-4o
    - groq/llama3-70b-8192
    - ollama/llama2

    API keys are routed based on the model prefix. You can either:
    1. Set them via environment variables (ANTHROPIC_API_KEY, OPENAI_API_KEY, etc.)
    2. Pass them via the api_key parameter (will be set in environment)
    """

    def __init__(self, model: str, api_key: str | None = None, api_base: str | None = None) -> None:
        """Initialize the LiteLLM provider.

        Args:
            model: Model string in provider/model format
            api_key: Optional API key (will be set in environment for the provider)
            api_base: Optional API base URL (e.g. for Pico/Ollama local servers)
        """
        # Translate pico/ prefix to ollama_chat/ for LiteLLM
        if model.startswith("pico/"):
            model = "ollama_chat/" + model[5:]

        super().__init__(api_key or "", model)
        self.api_base = api_base

        # Suppress LiteLLM's verbose logging
        litellm.suppress_debug_info = True

        # Set API key in environment if provided
        if api_key:
            provider = model.split("/")[0] if "/" in model else "openai"
            key_map = {
                "anthropic": "ANTHROPIC_API_KEY",
                "openai": "OPENAI_API_KEY",
                "openrouter": "OPENROUTER_API_KEY",
                "groq": "GROQ_API_KEY",
                "mistral": "MISTRAL_API_KEY",
                "cohere": "COHERE_API_KEY",
                "together_ai": "TOGETHER_API_KEY",
                "replicate": "REPLICATE_API_KEY",
            }
            if provider in key_map:
                os.environ[key_map[provider]] = api_key

    async def chat(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
        system_prompt: str | None = None,
        stream_callback: StreamCallback | None = None,
    ) -> LLMResponse:
        """Send a chat completion request via LiteLLM.

        Args:
            messages: Conversation history
            tools: Tool definitions for function calling
            system_prompt: System prompt to set context
            stream_callback: Optional callback for streaming text chunks

        Returns:
            LLM response with content and/or tool calls
        """
        # Build messages in OpenAI format (LiteLLM uses this internally)
        litellm_messages: list[dict[str, Any]] = []

        if system_prompt:
            litellm_messages.append({"role": "system", "content": system_prompt})

        for msg in messages:
            if msg.role == "assistant" and msg.tool_calls:
                # Assistant message with tool calls
                litellm_messages.append({
                    "role": "assistant",
                    "content": msg.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.name,
                                "arguments": json.dumps(tc.arguments),
                            },
                        }
                        for tc in msg.tool_calls
                    ],
                })
            elif msg.role == "tool":
                # Tool result message
                litellm_messages.append({
                    "role": "tool",
                    "tool_call_id": msg.tool_call_id,
                    "content": msg.content or "",
                })
            else:
                litellm_messages.append({
                    "role": msg.role,
                    "content": msg.content,
                })

        # Build request kwargs
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": litellm_messages,
        }

        if self.api_base:
            kwargs["api_base"] = self.api_base

        # Convert tools to OpenAI format (LiteLLM expects this)
        if tools:
            kwargs["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": t["name"],
                        "description": t.get("description", ""),
                        "parameters": t.get("input_schema", {}),
                    },
                }
                for t in tools
            ]

        if stream_callback:
            return await self._chat_stream(kwargs, stream_callback)

        # Non-streaming request
        response = await litellm.acompletion(**kwargs)
        return self._parse_response(response)

    async def _chat_stream(
        self,
        kwargs: dict[str, Any],
        stream_callback: StreamCallback,
    ) -> LLMResponse:
        """Handle streaming chat completion.

        Args:
            kwargs: Request parameters
            stream_callback: Callback for text chunks

        Returns:
            Complete LLM response after stream finishes
        """
        kwargs["stream"] = True
        kwargs["stream_options"] = {"include_usage": True}

        content_chunks: list[str] = []
        tool_calls_data: dict[int, dict[str, Any]] = {}
        finish_reason: str | None = None
        usage = {"input_tokens": 0, "output_tokens": 0}

        # Buffer for detecting and suppressing protocol tokens during streaming.
        # Once we know the stream is clean (no protocol tokens in first chunk)
        # or we've found the final channel marker, we forward directly.
        _stream_buf = ""
        _stream_forwarding = False  # True once we're past any protocol preamble
        _FINAL_MARKER = "<|channel|>final<|message|>"
        _PROTOCOL_START = "<|"

        response = await litellm.acompletion(**kwargs)

        async for chunk in response:
            # Handle usage if present (comes in final chunk)
            if hasattr(chunk, "usage") and chunk.usage:
                usage = {
                    "input_tokens": getattr(chunk.usage, "prompt_tokens", 0),
                    "output_tokens": getattr(chunk.usage, "completion_tokens", 0),
                }

            if not chunk.choices:
                continue

            choice = chunk.choices[0]
            delta = choice.delta

            if choice.finish_reason:
                finish_reason = choice.finish_reason

            # Handle content chunks
            if delta.content:
                content_chunks.append(delta.content)

                if _stream_forwarding:
                    # Already past protocol preamble — forward directly
                    stream_callback(delta.content)
                else:
                    # Still buffering — check for protocol tokens
                    _stream_buf += delta.content

                    if _FINAL_MARKER in _stream_buf:
                        # Found the final channel — forward everything after it
                        _, after = _stream_buf.split(_FINAL_MARKER, 1)
                        if after:
                            stream_callback(after)
                        _stream_forwarding = True
                    elif _PROTOCOL_START not in _stream_buf and len(_stream_buf) > 10:
                        # No protocol tokens detected — stream is clean, forward all
                        stream_callback(_stream_buf)
                        _stream_forwarding = True

            # Handle tool call chunks
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = tc.index
                    if idx not in tool_calls_data:
                        tool_calls_data[idx] = {"id": "", "name": "", "arguments": ""}
                    if tc.id:
                        tool_calls_data[idx]["id"] = tc.id
                    if tc.function:
                        if tc.function.name:
                            tool_calls_data[idx]["name"] = tc.function.name
                        if tc.function.arguments:
                            tool_calls_data[idx]["arguments"] += tc.function.arguments

        # Flush remaining buffer if stream ended while still buffering
        if not _stream_forwarding and _stream_buf:
            cleaned = self._strip_protocol_tokens(_stream_buf)
            if cleaned:
                stream_callback(cleaned)

        # Build final tool calls list
        tool_calls = []
        for idx in sorted(tool_calls_data.keys()):
            tc_data = tool_calls_data[idx]
            arguments = {}
            if tc_data["arguments"]:
                try:
                    arguments = json.loads(tc_data["arguments"])
                except json.JSONDecodeError:
                    arguments = {"raw": tc_data["arguments"]}
            tool_calls.append(
                ToolCall(
                    id=tc_data["id"],
                    name=tc_data["name"],
                    arguments=arguments,
                )
            )

        content = "".join(content_chunks) if content_chunks else None
        if content:
            content = self._strip_protocol_tokens(content)

        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            stop_reason=finish_reason,
            usage=usage,
        )

    @staticmethod
    def _strip_protocol_tokens(text: str) -> str:
        """Strip leaked model protocol/reasoning tokens from content.

        Some models (e.g. GPT-5.x) may leak internal channel markers like
        <|channel|>analysis<|message|>...<|end|><|start|>assistant<|channel|>final<|message|>...
        This extracts only the final user-facing content.
        """
        # If there's a final channel message, extract just that content
        final_match = re.search(
            r"<\|channel\|>final<\|message\|>",
            text,
        )
        if final_match:
            text = text[final_match.end():]
            # Strip trailing protocol tokens from the extracted content
            text = re.sub(r"<\|end\|>.*", "", text, flags=re.DOTALL)
            return text.strip()

        # No final channel — strip all protocol-enclosed blocks.
        # Pattern: <|token|>...(content)...<|end|> or <|token|>...(content)...<|start|>
        # Remove complete protocol blocks (analysis, commentary, etc.)
        text = re.sub(
            r"<\|(?:channel|start)\|>.*?(?=<\|(?:start|end)\|>|$)",
            "",
            text,
            flags=re.DOTALL,
        )

        # Strip any remaining individual protocol tokens
        text = re.sub(r"<\|(?:channel|message|start|end|constrain|system)\|>", "", text)

        return text.strip()

    def _parse_response(self, response: Any) -> LLMResponse:
        """Parse a non-streaming LiteLLM response.

        Args:
            response: LiteLLM completion response

        Returns:
            Parsed LLMResponse
        """
        choice = response.choices[0]
        message = choice.message

        # Parse tool calls if present
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

        content = message.content
        if content:
            content = self._strip_protocol_tokens(content)

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
        """Format a tool result as a message.

        Args:
            tool_call_id: ID of the tool call
            result: Result from the tool execution

        Returns:
            Formatted message for the conversation
        """
        return Message(role="tool", content=result, tool_call_id=tool_call_id)
