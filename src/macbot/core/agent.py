"""Core agent loop implementation.

The agent follows a ReAct-style pattern:
1. Receive input/goal
2. Reason about what to do
3. Execute a tool if needed
4. Observe the result
5. Repeat until done or max iterations reached
"""

import json
import logging
from typing import Any

from rich.console import Console
from rich.panel import Panel

from macbot.config import Settings, settings
from macbot.core.task import TaskRegistry, TaskResult
from macbot.providers.anthropic import AnthropicProvider
from macbot.providers.base import LLMProvider, LLMResponse, Message
from macbot.providers.openai import OpenAIProvider

logger = logging.getLogger(__name__)
console = Console()


class Agent:
    """An agent that can execute tasks using an LLM.

    The agent maintains a conversation with the LLM and can execute
    registered tasks based on the LLM's tool calls.
    """

    def __init__(
        self,
        task_registry: TaskRegistry,
        provider: LLMProvider | None = None,
        config: Settings | None = None,
    ) -> None:
        """Initialize the agent.

        Args:
            task_registry: Registry of available tasks
            provider: LLM provider (auto-configured from settings if not provided)
            config: Settings (uses global settings if not provided)
        """
        self.config = config or settings
        self.task_registry = task_registry
        self.provider = provider or self._create_provider()
        self.messages: list[Message] = []
        self.iteration = 0

    def _create_provider(self) -> LLMProvider:
        """Create an LLM provider based on configuration."""
        from macbot.config import LLMProviderType

        provider_config = self.config.get_provider_config()

        if self.config.llm_provider == LLMProviderType.ANTHROPIC:
            return AnthropicProvider(
                api_key=provider_config["api_key"],
                model=provider_config["model"],
            )
        else:
            return OpenAIProvider(
                api_key=provider_config["api_key"],
                model=provider_config["model"],
            )

    async def run(self, goal: str, verbose: bool = False) -> str:
        """Run the agent loop to achieve a goal.

        Args:
            goal: The objective for the agent to achieve
            verbose: Whether to print detailed output

        Returns:
            The final response from the agent
        """
        self.messages = [Message(role="user", content=goal)]
        self.iteration = 0

        if verbose:
            console.print(Panel(f"[bold]Goal:[/bold] {goal}", title="Agent Started"))

        while self.iteration < self.config.max_iterations:
            self.iteration += 1

            if verbose:
                console.print(f"\n[dim]Iteration {self.iteration}/{self.config.max_iterations}[/dim]")

            # Get LLM response
            response = await self._get_llm_response()

            if verbose and response.content:
                console.print(Panel(response.content, title="Assistant"))

            # Check if we have tool calls to execute
            if response.tool_calls:
                await self._execute_tool_calls(response, verbose)
            else:
                # No tool calls means the agent has finished
                return response.content or "Task completed."

        return "Reached maximum iterations without completing the goal."

    async def _get_llm_response(self) -> LLMResponse:
        """Get a response from the LLM."""
        tools = self.task_registry.get_tool_schemas()

        return await self.provider.chat(
            messages=self.messages,
            tools=tools if tools else None,
            system_prompt=self.config.agent_system_prompt,
        )

    async def _execute_tool_calls(
        self, response: LLMResponse, verbose: bool = False
    ) -> None:
        """Execute tool calls from the LLM response."""
        # Add assistant message with tool calls to history
        if response.content:
            self.messages.append(Message(role="assistant", content=response.content))

        # Execute each tool call
        for tool_call in response.tool_calls:
            if verbose:
                console.print(
                    f"[yellow]Executing:[/yellow] {tool_call.name}({json.dumps(tool_call.arguments)})"
                )

            result = await self.task_registry.execute(
                tool_call.name, **tool_call.arguments
            )

            if verbose:
                status = "[green]Success[/green]" if result.success else "[red]Failed[/red]"
                console.print(f"  {status}: {result.output or result.error}")

            # Format and add tool result to messages
            result_str = self._format_tool_result(result)
            tool_msg = self.provider.format_tool_result(tool_call.id, result_str)
            self.messages.append(tool_msg)

    def _format_tool_result(self, result: TaskResult) -> str:
        """Format a task result as a string for the LLM."""
        if result.success:
            if isinstance(result.output, (dict, list)):
                return json.dumps(result.output)
            return str(result.output)
        else:
            return f"Error: {result.error}"

    async def run_single_task(
        self, task_name: str, verbose: bool = False, **kwargs: Any
    ) -> TaskResult:
        """Run a single task directly without LLM involvement.

        Args:
            task_name: Name of the task to execute
            verbose: Whether to print output
            **kwargs: Task parameters

        Returns:
            Task result
        """
        if verbose:
            console.print(f"[yellow]Executing task:[/yellow] {task_name}")

        result = await self.task_registry.execute(task_name, **kwargs)

        if verbose:
            status = "[green]Success[/green]" if result.success else "[red]Failed[/red]"
            console.print(f"  {status}: {result.output or result.error}")

        return result

    def reset(self) -> None:
        """Reset the agent state."""
        self.messages = []
        self.iteration = 0
