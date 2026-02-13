"""Subagent orchestration for delegating focused tasks.

A subagent is a fresh Agent instance with a scoped tool registry,
an optional cheaper model, and an isolated conversation context.
Subagents run to completion and return a summary string.
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any

from macbot.config import Settings
from macbot.tasks.registry import TaskRegistry

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROVIDER_FAST_MODELS: dict[str, str] = {
    "anthropic": "anthropic/claude-haiku-4-5-20251001",
    "openai": "openai/gpt-4o-mini",
    "openrouter": "openrouter/anthropic/claude-haiku-4-5-20251001",
}

PROFILE_TOOLS: dict[str, set[str]] = {
    "mail_research": {
        "search_emails",
        "get_unread_emails",
        "download_attachments",
        "mark_emails_read",
        "check_email_processed",
        "mark_email_processed",
        "get_agent_memory",
        "get_current_time",
        "read_file",
    },
    "calendar_planner": {
        "get_today_events",
        "get_week_events",
        "create_calendar_event",
        "list_calendars",
        "get_due_today_reminders",
        "create_reminder",
        "get_current_time",
        "search_emails",
    },
    "web_researcher": {
        "web_fetch",
        "web_search",
        "fetch_url",
        "browser_navigate",
        "browser_snapshot",
        "browser_click",
        "browser_type",
        "browser_execute_js",
        "browser_close_tab",
        "browser_screenshot",
        "get_current_time",
    },
    "general": set(),  # special: all tasks except run_subagent
}

PROFILE_PROMPTS: dict[str, str] = {
    "mail_research": (
        "You are a mail research assistant. Search and read emails efficiently.\n"
        "Summarize findings clearly. Use message IDs for precise lookups.\n"
        "Check agent memory before searching to avoid duplicate work."
    ),
    "calendar_planner": (
        "You are a calendar planning assistant. Work with events and reminders.\n"
        "Be precise with dates, times, and time zones.\n"
        "Cross-reference emails when relevant to calendar planning."
    ),
    "web_researcher": (
        "You are a web research assistant. Search the web and extract information.\n"
        "Prefer simple web_fetch/web_search over browser automation when possible.\n"
        "Summarize findings concisely with source URLs."
    ),
    "general": (
        "You are a general-purpose assistant with access to macOS automation tools.\n"
        "Complete the task using the most appropriate tools available.\n"
        "Be efficient and direct."
    ),
}


@dataclass
class SubagentResult:
    """Result from a subagent execution."""

    success: bool
    response: str
    profile: str
    model: str
    elapsed_seconds: float
    iterations: int
    input_tokens: int
    output_tokens: int


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def resolve_model(config: Settings, tier: str) -> str:
    """Resolve which model to use for the subagent.

    Args:
        config: Application settings.
        tier: 'fast' for cheaper model, 'main' for same as parent.

    Returns:
        Model string in provider/model format.
    """
    if config.subagent_model:
        return config.subagent_model

    if tier == "fast":
        provider = config.get_provider()
        return PROVIDER_FAST_MODELS.get(provider, config.get_model())

    return config.get_model()


def create_scoped_registry(
    parent_registry: TaskRegistry, profile: str
) -> TaskRegistry:
    """Create a new registry with only the tools allowed by the profile.

    Args:
        parent_registry: The parent agent's full registry.
        profile: One of the PROFILE_TOOLS keys.

    Returns:
        A new TaskRegistry with scoped tasks.

    Raises:
        ValueError: If the profile is unknown.
    """
    if profile not in PROFILE_TOOLS:
        raise ValueError(
            f"Unknown subagent profile: {profile!r}. "
            f"Valid profiles: {', '.join(PROFILE_TOOLS.keys())}"
        )

    registry = TaskRegistry()
    allowed = PROFILE_TOOLS[profile]

    for task in parent_registry.list_tasks():
        if profile == "general":
            # General: all tasks except run_subagent (no nesting)
            if task.name != "run_subagent":
                registry.register(task)
        elif task.name in allowed:
            registry.register(task)

    return registry


def build_subagent_prompt(profile: str) -> str:
    """Build the system prompt for a subagent.

    Args:
        profile: The subagent profile name.

    Returns:
        System prompt string (system context is appended by Agent).
    """
    guidance = PROFILE_PROMPTS.get(profile, PROFILE_PROMPTS["general"])
    return (
        "You are a focused assistant performing a specific task.\n"
        "Complete the task efficiently using available tools. "
        "Return a clear summary when done.\n"
        "Do not ask for confirmation — just execute.\n\n"
        f"{guidance}"
    )


async def run_subagent(
    config: Settings,
    parent_registry: TaskRegistry,
    goal: str,
    profile: str = "general",
    context: str = "",
    tier: str = "fast",
    on_event: Any | None = None,
) -> SubagentResult:
    """Run a subagent to completion.

    Args:
        config: Application settings.
        parent_registry: The parent agent's task registry.
        goal: The task for the subagent to accomplish.
        profile: Tool profile (mail_research, calendar_planner, web_researcher, general).
        context: Optional context to prepend to the goal.
        tier: Model tier ('fast' or 'main').
        on_event: Optional event callback for tool call/result events.

    Returns:
        SubagentResult with the outcome.
    """
    from macbot.core.agent import Agent
    from macbot.providers.litellm_provider import LiteLLMProvider
    from macbot.skills.registry import SkillsRegistry

    model = resolve_model(config, tier)
    start = time.monotonic()

    try:
        scoped_registry = create_scoped_registry(parent_registry, profile)

        api_key = config.get_api_key_for_model(model)
        api_base = config.get_api_base_for_model(model)
        provider = LiteLLMProvider(model=model, api_key=api_key, api_base=api_base)

        subagent_config = config.model_copy(
            update={"max_iterations": config.subagent_max_iterations}
        )

        agent = Agent(
            task_registry=scoped_registry,
            provider=provider,
            config=subagent_config,
            skills_registry=SkillsRegistry(),  # empty — subagents don't use skills
            system_prompt=build_subagent_prompt(profile),
        )

        # Build full goal with optional context
        full_goal = goal
        if context:
            full_goal = f"Context:\n{context}\n\nTask:\n{goal}"

        response = await asyncio.wait_for(
            agent.run(full_goal, stream=False, on_event=on_event),
            timeout=config.subagent_timeout,
        )

        stats = agent.get_token_stats()
        elapsed = time.monotonic() - start

        return SubagentResult(
            success=True,
            response=response,
            profile=profile,
            model=model,
            elapsed_seconds=elapsed,
            iterations=agent.iteration,
            input_tokens=stats["session_input_tokens"],
            output_tokens=stats["session_output_tokens"],
        )

    except TimeoutError:
        elapsed = time.monotonic() - start
        logger.warning(f"Subagent timed out after {elapsed:.1f}s (profile={profile})")
        return SubagentResult(
            success=False,
            response=f"Subagent timed out after {config.subagent_timeout}s",
            profile=profile,
            model=model,
            elapsed_seconds=elapsed,
            iterations=0,
            input_tokens=0,
            output_tokens=0,
        )

    except Exception as e:
        elapsed = time.monotonic() - start
        logger.exception(f"Subagent failed (profile={profile})")
        return SubagentResult(
            success=False,
            response=f"Subagent error: {e}",
            profile=profile,
            model=model,
            elapsed_seconds=elapsed,
            iterations=0,
            input_tokens=0,
            output_tokens=0,
        )
