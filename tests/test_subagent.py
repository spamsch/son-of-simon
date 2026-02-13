"""Tests for the subagent system."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from macbot.config import Settings
from macbot.core.subagent import (
    PROFILE_PROMPTS,
    PROFILE_TOOLS,
    SubagentResult,
    build_subagent_prompt,
    create_scoped_registry,
    resolve_model,
    run_subagent,
)
from macbot.tasks.base import Task
from macbot.tasks.registry import TaskRegistry
from macbot.tasks.subagent import RunSubagentTask


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _DummyTask(Task):
    """Minimal task for registry tests."""

    def __init__(self, task_name: str) -> None:
        self._name = task_name

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return f"Dummy task: {self._name}"

    async def execute(self, **kwargs) -> str:
        return "ok"


def _make_registry(names: list[str]) -> TaskRegistry:
    """Build a registry with dummy tasks for the given names."""
    reg = TaskRegistry()
    for n in names:
        reg.register(_DummyTask(n))
    return reg


def _make_settings(**overrides) -> Settings:
    """Create a Settings instance with test defaults."""
    defaults = {
        "model": "anthropic/claude-sonnet-4-20250514",
        "anthropic_api_key": "test-key",
    }
    defaults.update(overrides)
    return Settings(**defaults)


# ---------------------------------------------------------------------------
# resolve_model tests
# ---------------------------------------------------------------------------


class TestResolveModel:
    def test_fast_anthropic(self) -> None:
        config = _make_settings(model="anthropic/claude-sonnet-4-20250514")
        assert resolve_model(config, "fast") == "anthropic/claude-haiku-4-5-20251001"

    def test_fast_openai(self) -> None:
        config = _make_settings(model="openai/gpt-4o")
        assert resolve_model(config, "fast") == "openai/gpt-4o-mini"

    def test_fast_pico_fallback(self) -> None:
        """Pico is not in PROVIDER_FAST_MODELS → falls back to parent model."""
        config = _make_settings(model="pico/llama3")
        assert resolve_model(config, "fast") == "pico/llama3"

    def test_main_tier(self) -> None:
        config = _make_settings(model="anthropic/claude-sonnet-4-20250514")
        assert resolve_model(config, "main") == "anthropic/claude-sonnet-4-20250514"

    def test_config_override(self) -> None:
        """subagent_model in config takes priority over tier logic."""
        config = _make_settings(subagent_model="openai/gpt-4o")
        assert resolve_model(config, "fast") == "openai/gpt-4o"
        assert resolve_model(config, "main") == "openai/gpt-4o"


# ---------------------------------------------------------------------------
# create_scoped_registry tests
# ---------------------------------------------------------------------------


class TestCreateScopedRegistry:
    def test_mail_profile(self) -> None:
        all_names = list(PROFILE_TOOLS["mail_research"]) + ["run_subagent", "other_tool"]
        parent = _make_registry(all_names)
        scoped = create_scoped_registry(parent, "mail_research")

        scoped_names = set(scoped.list_names())
        assert scoped_names == PROFILE_TOOLS["mail_research"]
        assert "run_subagent" not in scoped_names
        assert "other_tool" not in scoped_names

    def test_general_excludes_run_subagent(self) -> None:
        parent = _make_registry(["get_current_time", "run_subagent", "search_emails"])
        scoped = create_scoped_registry(parent, "general")

        scoped_names = set(scoped.list_names())
        assert "run_subagent" not in scoped_names
        assert "get_current_time" in scoped_names
        assert "search_emails" in scoped_names

    def test_unknown_profile_raises(self) -> None:
        parent = _make_registry(["get_current_time"])
        with pytest.raises(ValueError, match="Unknown subagent profile"):
            create_scoped_registry(parent, "nonexistent_profile")


# ---------------------------------------------------------------------------
# build_subagent_prompt tests
# ---------------------------------------------------------------------------


class TestBuildSubagentPrompt:
    def test_contains_profile_guidance(self) -> None:
        for profile, guidance in PROFILE_PROMPTS.items():
            prompt = build_subagent_prompt(profile)
            assert guidance in prompt

    def test_contains_base_instructions(self) -> None:
        prompt = build_subagent_prompt("general")
        assert "focused assistant" in prompt
        assert "Do not ask for confirmation" in prompt


# ---------------------------------------------------------------------------
# RunSubagentTask schema test
# ---------------------------------------------------------------------------


class TestRunSubagentTaskSchema:
    def test_tool_schema(self) -> None:
        task = RunSubagentTask()
        schema = task.to_tool_schema()

        assert schema["name"] == "run_subagent"
        props = schema["input_schema"]["properties"]
        assert "goal" in props
        assert "profile" in props
        assert "context" in props
        assert "tier" in props
        assert len(props) == 4

    def test_required_params(self) -> None:
        task = RunSubagentTask()
        schema = task.to_tool_schema()
        assert schema["input_schema"]["required"] == ["goal"]


# ---------------------------------------------------------------------------
# Integration test with mock provider
# ---------------------------------------------------------------------------


class TestSubagentExecution:
    @pytest.mark.asyncio
    async def test_run_subagent_mock(self) -> None:
        """Run a subagent with a mocked LLM provider that returns a canned response."""
        config = _make_settings(subagent_max_iterations=5, subagent_timeout=10)
        parent = _make_registry(["get_current_time", "search_emails", "run_subagent"])

        mock_response = "Found 3 unread emails from today."

        with patch("macbot.providers.litellm_provider.LiteLLMProvider"), \
             patch("macbot.core.agent.Agent") as MockAgent:

            mock_agent_instance = MagicMock()
            mock_agent_instance.run = AsyncMock(return_value=mock_response)
            mock_agent_instance.iteration = 2
            mock_agent_instance.get_token_stats.return_value = {
                "session_input_tokens": 500,
                "session_output_tokens": 100,
                "session_total_tokens": 600,
                "context_tokens": 0,
                "message_count": 0,
            }
            MockAgent.return_value = mock_agent_instance

            result = await run_subagent(
                config=config,
                parent_registry=parent,
                goal="Find my unread emails",
                profile="mail_research",
                tier="fast",
            )

        assert isinstance(result, SubagentResult)
        assert result.success is True
        assert result.response == mock_response
        assert result.profile == "mail_research"
        assert result.model == "anthropic/claude-haiku-4-5-20251001"
        assert result.iterations == 2
        assert result.input_tokens == 500
        assert result.output_tokens == 100
        assert result.elapsed_seconds > 0

    @pytest.mark.asyncio
    async def test_run_subagent_timeout(self) -> None:
        """Subagent timeout returns a failure result."""
        import asyncio

        config = _make_settings(subagent_max_iterations=5, subagent_timeout=1)
        parent = _make_registry(["get_current_time"])

        async def slow_run(*args, **kwargs):
            await asyncio.sleep(10)
            return "done"

        with patch("macbot.providers.litellm_provider.LiteLLMProvider"), \
             patch("macbot.core.agent.Agent") as MockAgent:

            mock_agent_instance = MagicMock()
            mock_agent_instance.run = slow_run
            MockAgent.return_value = mock_agent_instance

            result = await run_subagent(
                config=config,
                parent_registry=parent,
                goal="Do something slow",
                profile="general",
            )

        assert result.success is False
        assert "timed out" in result.response

    @pytest.mark.asyncio
    async def test_run_subagent_with_context(self) -> None:
        """Context is prepended to the goal."""
        config = _make_settings(subagent_max_iterations=5, subagent_timeout=10)
        parent = _make_registry(["get_current_time"])

        captured_goal = None

        async def capture_run(goal, **kwargs):
            nonlocal captured_goal
            captured_goal = goal
            return "done"

        with patch("macbot.providers.litellm_provider.LiteLLMProvider"), \
             patch("macbot.core.agent.Agent") as MockAgent:

            mock_agent_instance = MagicMock()
            mock_agent_instance.run = capture_run
            mock_agent_instance.iteration = 1
            mock_agent_instance.get_token_stats.return_value = {
                "session_input_tokens": 0,
                "session_output_tokens": 0,
                "session_total_tokens": 0,
                "context_tokens": 0,
                "message_count": 0,
            }
            MockAgent.return_value = mock_agent_instance

            await run_subagent(
                config=config,
                parent_registry=parent,
                goal="Find invoices",
                context="User is looking for Medpex invoices from January",
                profile="general",
            )

        assert captured_goal is not None
        assert "Context:" in captured_goal
        assert "Medpex invoices from January" in captured_goal
        assert "Task:" in captured_goal
        assert "Find invoices" in captured_goal
