"""Cron job system for scheduled task execution.

This package provides a complete cron job system including:
- Job scheduling with multiple schedule types (at, every, cron)
- JSON file persistence
- Async job execution with timeout support
- Integration with the agent system

Example:
    from macbot.cron import CronService, CronJobCreate, CronSchedule, CronPayload

    service = CronService()

    # Create a daily job
    job = service.schedule_cron(
        name="Daily reminder",
        cron_expr="0 9 * * *",
        message="Good morning! Time for daily tasks.",
    )

    # Start the service
    await service.start()
"""

from macbot.cron.executor import CronExecutor, ExecutionResult, default_executor
from macbot.cron.schedule import (
    compute_next_run,
    get_cron_description,
    time_until_next_run,
    validate_cron_expression,
)
from macbot.cron.service import CronService
from macbot.cron.storage import CronStorage
from macbot.cron.types import (
    CronJob,
    CronJobCreate,
    CronJobState,
    CronJobUpdate,
    CronPayload,
    CronSchedule,
    ScheduleKind,
)

__all__ = [
    # Service
    "CronService",
    # Types
    "CronJob",
    "CronJobCreate",
    "CronJobUpdate",
    "CronJobState",
    "CronSchedule",
    "CronPayload",
    "ScheduleKind",
    # Storage
    "CronStorage",
    # Executor
    "CronExecutor",
    "ExecutionResult",
    "default_executor",
    # Schedule utilities
    "compute_next_run",
    "validate_cron_expression",
    "get_cron_description",
    "time_until_next_run",
]
