"""Modular task system for the agent.

This module re-exports the task system from macbot.tasks for backwards compatibility.
New code should import directly from macbot.tasks.

Example:
    # Preferred (new code)
    from macbot.tasks import Task, TaskRegistry, task_registry

    # Still works (backwards compatible)
    from macbot.core.task import Task, TaskRegistry
"""

# Re-export everything from the new locations
from macbot.tasks.base import (
    FunctionTask,
    Task,
    TaskDefinition,
    TaskParameter,
    TaskResult,
)
from macbot.tasks.registry import TaskRegistry, task_registry

__all__ = [
    "Task",
    "FunctionTask",
    "TaskParameter",
    "TaskDefinition",
    "TaskResult",
    "TaskRegistry",
    "task_registry",
]
