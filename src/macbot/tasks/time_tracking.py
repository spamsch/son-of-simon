"""Tasks: Time Tracking

Provides agent tools for tracking time spent on tasks with start/stop timers
and reporting capabilities.
"""

from typing import Any

from macbot.tasks.base import Task
from macbot.time_tracking import get_storage, format_duration


class TimerStartTask(Task):
    """Start tracking time on a task."""

    @property
    def name(self) -> str:
        return "timer_start"

    @property
    def description(self) -> str:
        return (
            "Start a timer to track time spent on a task. "
            "If a timer is already running, it will be automatically stopped and saved. "
            "Use this when the user says things like 'start a timer for X' or 'track time on X'."
        )

    async def execute(self, task_name: str) -> dict[str, Any]:
        """Start tracking time on a task.

        Args:
            task_name: Name of the task to track (e.g., "Operayo Work", "Code Review")

        Returns:
            Dictionary with start info
        """
        storage = get_storage()
        result = storage.start_timer(task_name)

        # Format response message
        if result.get("previous_timer"):
            prev = result["previous_timer"]
            result["message"] = (
                f"Started timer for '{task_name}'. "
                f"Previous timer for '{prev['task_name']}' stopped ({prev['duration']})."
            )
        else:
            result["message"] = f"Started timer for '{task_name}'."

        return result


class TimerStopTask(Task):
    """Stop the current timer and record the time entry."""

    @property
    def name(self) -> str:
        return "timer_stop"

    @property
    def description(self) -> str:
        return (
            "Stop the currently running timer and save the time entry. "
            "Use this when the user says 'stop the timer', 'stop tracking', or 'I'm done with X'."
        )

    async def execute(self, notes: str | None = None) -> dict[str, Any]:
        """Stop the current timer.

        Args:
            notes: Optional notes to add to the time entry

        Returns:
            Dictionary with stop info
        """
        storage = get_storage()
        result = storage.stop_timer(notes=notes)

        if not result.get("success"):
            return result

        if result.get("was_active"):
            result["message"] = (
                f"Stopped timer for '{result['task_name']}'. "
                f"Duration: {result['duration']}."
            )
        else:
            result["message"] = "No timer was running."

        return result


class TimerStatusTask(Task):
    """Show what's currently being tracked."""

    @property
    def name(self) -> str:
        return "timer_status"

    @property
    def description(self) -> str:
        return (
            "Check if a timer is currently running and show what task is being tracked. "
            "Use this when the user asks 'what am I working on?', 'is a timer running?', "
            "or 'what am I tracking?'."
        )

    async def execute(self) -> dict[str, Any]:
        """Get the current timer status.

        Returns:
            Dictionary with timer status
        """
        storage = get_storage()
        result = storage.get_status()

        if result.get("active"):
            result["message"] = (
                f"Currently tracking '{result['task_name']}' "
                f"(started {result['elapsed']} ago)."
            )
        else:
            result["message"] = "No timer is currently running."

        return result


class TimerReportTask(Task):
    """Show time entries and summary for a period."""

    @property
    def name(self) -> str:
        return "timer_report"

    @property
    def description(self) -> str:
        return (
            "Show a time report with totals by task for a given period. "
            "Use this when the user asks for 'time report', 'show my time', 'how much time did I spend', "
            "or 'time summary for this week/today'."
        )

    async def execute(
        self,
        days: int = 7,
        task_name: str | None = None,
    ) -> dict[str, Any]:
        """Get a time report.

        Args:
            days: Number of days to include (default: 7 for weekly report, use 1 for today)
            task_name: Filter by specific task name to see individual entries

        Returns:
            Dictionary with time report
        """
        storage = get_storage()
        result = storage.get_summary(days=days, task_name=task_name)

        # Build summary message
        if not result.get("by_task"):
            result["message"] = f"No time entries found for {result['period'].lower()}."
        else:
            lines = [f"Time Report - {result['period']}:", f"Total: {result['total']}", ""]
            for task in result["by_task"]:
                lines.append(f"  {task['task']}: {task['total']} ({task['entries']} entries)")
            result["message"] = "\n".join(lines)

        return result


def register_time_tracking_tasks(registry) -> None:
    """Register all time tracking tasks with a registry.

    Args:
        registry: TaskRegistry to register tasks with.
    """
    registry.register(TimerStartTask())
    registry.register(TimerStopTask())
    registry.register(TimerStatusTask())
    registry.register(TimerReportTask())
