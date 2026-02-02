"""Core components for the agent loop."""

from macbot.core.agent import Agent
from macbot.core.command_queue import CommandLane, CommandQueue, LaneState, QueueEntry
from macbot.core.followup_queue import (
    DropPolicy,
    FollowupItem,
    FollowupQueue,
    QueueMode,
)
from macbot.core.scheduler import TaskScheduler
from macbot.core.task import Task, TaskRegistry

__all__ = [
    # Agent
    "Agent",
    # Scheduler
    "TaskScheduler",
    # Task system (re-exported for backwards compatibility)
    "Task",
    "TaskRegistry",
    # Command queue
    "CommandQueue",
    "CommandLane",
    "QueueEntry",
    "LaneState",
    # Followup queue
    "FollowupQueue",
    "FollowupItem",
    "QueueMode",
    "DropPolicy",
]
