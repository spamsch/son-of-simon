"""Subagent task — exposes run_subagent as an LLM tool."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from macbot.config import settings
from macbot.core.subagent import run_subagent
from macbot.tasks.base import Task

if TYPE_CHECKING:
    from macbot.config import Settings
    from macbot.tasks.registry import TaskRegistry


class RunSubagentTask(Task):
    """Delegate a focused task to a subagent with scoped tools."""

    def __init__(
        self,
        config: Settings | None = None,
        parent_registry: TaskRegistry | None = None,
    ) -> None:
        self._config = config
        self._parent_registry = parent_registry

    @property
    def name(self) -> str:
        return "run_subagent"

    @property
    def description(self) -> str:
        return (
            "Delegate a focused task to a subagent that runs with its own context and tools.\n"
            "Use this for multi-step research or actions that benefit from isolated focus.\n"
            "\n"
            "Profiles:\n"
            "- mail_research: Email searching, reading, processing\n"
            "- calendar_planner: Calendar events, reminders\n"
            "- web_researcher: Web search, browsing, extraction\n"
            "- general: All tools (for tasks that don't fit a specific profile)\n"
            "\n"
            "Tiers (model selection):\n"
            "- fast: Cheaper/faster model (default, good for most delegated tasks)\n"
            "- main: Same model as you (for tasks requiring high reasoning)"
        )

    async def execute(
        self,
        goal: str,
        profile: str = "general",
        context: str = "",
        tier: str = "fast",
    ) -> str:
        """Run a subagent with the given parameters.

        Args:
            goal: The task for the subagent to accomplish.
            profile: Tool profile (mail_research, calendar_planner, web_researcher, general).
            context: Optional context to prepend to the goal.
            tier: Model tier — 'fast' (cheaper) or 'main' (same as parent).

        Returns:
            Subagent response with metadata footer.
        """
        config = self._config or settings
        registry = self._parent_registry
        if registry is None:
            from macbot.tasks import create_default_registry
            registry = create_default_registry()

        result = await run_subagent(
            config=config,
            parent_registry=registry,
            goal=goal,
            profile=profile,
            context=context,
            tier=tier,
        )

        footer = (
            f"\n\n---\n[subagent: {result.profile}, model: {result.model}, "
            f"{result.iterations} steps, {result.elapsed_seconds:.1f}s, "
            f"{result.input_tokens + result.output_tokens} tokens]"
        )
        return result.response + footer
