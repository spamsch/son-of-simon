"""Schedule computation for cron jobs.

This module handles computing the next run time for different
schedule types (at, every, cron expression).
"""

import logging
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from croniter import croniter

from macbot.cron.types import CronSchedule, ScheduleKind

logger = logging.getLogger(__name__)


def compute_next_run(
    schedule: CronSchedule,
    last_run: datetime | None = None,
    now: datetime | None = None,
) -> datetime | None:
    """Compute the next run time for a schedule.

    Args:
        schedule: The schedule configuration.
        last_run: Time of the last execution (for recurring schedules).
        now: Current time (defaults to UTC now).

    Returns:
        Next run time as datetime, or None if the job won't run again.
    """
    now = now or datetime.now(timezone.utc)

    if schedule.kind == ScheduleKind.AT:
        return _compute_at_next_run(schedule, now)
    elif schedule.kind == ScheduleKind.EVERY:
        return _compute_every_next_run(schedule, last_run, now)
    elif schedule.kind == ScheduleKind.CRON:
        return _compute_cron_next_run(schedule, now)
    else:
        logger.error(f"Unknown schedule kind: {schedule.kind}")
        return None


def _compute_at_next_run(
    schedule: CronSchedule,
    now: datetime,
) -> datetime | None:
    """Compute next run for one-shot 'at' schedule.

    Args:
        schedule: The schedule configuration.
        now: Current time.

    Returns:
        The scheduled time if in the future, None otherwise.
    """
    if schedule.at_ms is None:
        return None

    target = datetime.fromtimestamp(schedule.at_ms / 1000, tz=timezone.utc)

    # One-shot schedules only run once
    if target <= now:
        return None

    return target


def _compute_every_next_run(
    schedule: CronSchedule,
    last_run: datetime | None,
    now: datetime,
) -> datetime | None:
    """Compute next run for recurring 'every' schedule.

    Args:
        schedule: The schedule configuration.
        last_run: Time of last execution.
        now: Current time.

    Returns:
        Next run time.
    """
    if schedule.every_ms is None:
        return None

    interval = timedelta(milliseconds=schedule.every_ms)

    if last_run is None:
        # First run: schedule immediately
        return now + interval

    # Ensure last_run has timezone info
    if last_run.tzinfo is None:
        last_run = last_run.replace(tzinfo=timezone.utc)

    next_run = last_run + interval

    # If we're past the next run time, schedule from now
    if next_run <= now:
        # Calculate how many intervals have passed
        elapsed = (now - last_run).total_seconds() * 1000
        intervals_passed = int(elapsed / schedule.every_ms)
        next_run = last_run + timedelta(milliseconds=schedule.every_ms * (intervals_passed + 1))

    return next_run


def _compute_cron_next_run(
    schedule: CronSchedule,
    now: datetime,
) -> datetime | None:
    """Compute next run for cron expression schedule.

    Args:
        schedule: The schedule configuration.
        now: Current time.

    Returns:
        Next run time based on cron expression.
    """
    if schedule.cron_expr is None:
        return None

    try:
        # Get the timezone
        tz = ZoneInfo(schedule.timezone)

        # Convert now to the schedule's timezone
        now_tz = now.astimezone(tz) if now.tzinfo else now.replace(tzinfo=tz)

        # Create croniter and get next run
        cron = croniter(schedule.cron_expr, now_tz)
        next_run = cron.get_next(datetime)

        # Convert back to UTC
        return next_run.astimezone(timezone.utc)

    except Exception as e:
        logger.error(f"Error computing cron schedule: {e}")
        return None


def validate_cron_expression(expr: str) -> bool:
    """Validate a cron expression.

    Args:
        expr: The cron expression to validate.

    Returns:
        True if the expression is valid.
    """
    try:
        croniter(expr)
        return True
    except Exception:
        return False


def get_cron_description(expr: str) -> str:
    """Get a human-readable description of a cron expression.

    Args:
        expr: The cron expression.

    Returns:
        Human-readable description or error message.
    """
    try:
        # Parse the expression
        parts = expr.split()
        if len(parts) < 5:
            return "Invalid cron expression"

        minute, hour, day, month, dow = parts[:5]

        descriptions = []

        # Minute
        if minute == "*":
            descriptions.append("every minute")
        elif minute == "0":
            descriptions.append("at minute 0")
        else:
            descriptions.append(f"at minute {minute}")

        # Hour
        if hour == "*":
            descriptions.append("of every hour")
        elif hour != "*":
            descriptions.append(f"past hour {hour}")

        # Day of month
        if day != "*":
            descriptions.append(f"on day {day}")

        # Month
        if month != "*":
            descriptions.append(f"in month {month}")

        # Day of week
        dow_names = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
        if dow != "*":
            try:
                dow_idx = int(dow)
                descriptions.append(f"on {dow_names[dow_idx]}")
            except ValueError:
                descriptions.append(f"on {dow}")

        return " ".join(descriptions)

    except Exception:
        return "Complex cron expression"


def time_until_next_run(
    schedule: CronSchedule,
    last_run: datetime | None = None,
    now: datetime | None = None,
) -> timedelta | None:
    """Get the time remaining until the next scheduled run.

    Args:
        schedule: The schedule configuration.
        last_run: Time of last execution.
        now: Current time.

    Returns:
        Time until next run, or None if no future runs.
    """
    now = now or datetime.now(timezone.utc)
    next_run = compute_next_run(schedule, last_run, now)

    if next_run is None:
        return None

    return next_run - now
