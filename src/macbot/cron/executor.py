"""Job execution logic for the cron system.

This module handles the actual execution of cron job payloads,
including agent turns and system events.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable

from macbot.cron.types import CronJob, CronPayload

logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    """Result of executing a cron job.

    Attributes:
        success: Whether execution succeeded.
        output: Result output on success.
        error: Error message on failure.
        duration_ms: Execution duration in milliseconds.
    """

    success: bool
    output: Any = None
    error: str | None = None
    duration_ms: float = 0


# Type alias for execution handlers
ExecutionHandler = Callable[[CronPayload], Awaitable[ExecutionResult]]


class CronExecutor:
    """Executor for cron job payloads.

    Manages execution of different payload types with configurable
    handlers and timeout support.

    Example:
        executor = CronExecutor()

        @executor.register_handler("agent_turn")
        async def handle_agent_turn(payload: CronPayload) -> ExecutionResult:
            # Process the agent turn
            return ExecutionResult(success=True, output="Done")

        result = await executor.execute(job)
    """

    def __init__(self) -> None:
        """Initialize the executor."""
        self._handlers: dict[str, ExecutionHandler] = {}
        self._default_timeout = 120

    def register_handler(
        self,
        payload_kind: str,
    ) -> Callable[[ExecutionHandler], ExecutionHandler]:
        """Decorator to register a payload handler.

        Args:
            payload_kind: The payload kind this handler processes.

        Returns:
            Decorator function.

        Example:
            @executor.register_handler("agent_turn")
            async def handle(payload):
                ...
        """
        def decorator(handler: ExecutionHandler) -> ExecutionHandler:
            self._handlers[payload_kind] = handler
            logger.debug(f"Registered handler for payload kind: {payload_kind}")
            return handler
        return decorator

    def set_handler(self, payload_kind: str, handler: ExecutionHandler) -> None:
        """Set a handler for a payload kind.

        Args:
            payload_kind: The payload kind.
            handler: The handler function.
        """
        self._handlers[payload_kind] = handler

    async def execute(self, job: CronJob) -> ExecutionResult:
        """Execute a cron job.

        Args:
            job: The job to execute.

        Returns:
            Execution result.
        """
        start_time = datetime.now(timezone.utc)
        payload = job.payload

        logger.info(f"Executing cron job: {job.name} ({job.id})")

        # Get the handler
        handler = self._handlers.get(payload.kind)
        if handler is None:
            error = f"No handler registered for payload kind: {payload.kind}"
            logger.error(error)
            return ExecutionResult(success=False, error=error)

        # Execute with timeout
        timeout = payload.timeout_seconds or self._default_timeout

        try:
            result = await asyncio.wait_for(
                handler(payload),
                timeout=timeout,
            )
            duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            result.duration_ms = duration_ms

            if result.success:
                logger.info(
                    f"Cron job completed: {job.name} ({job.id}) "
                    f"in {duration_ms:.0f}ms"
                )
            else:
                logger.warning(
                    f"Cron job failed: {job.name} ({job.id}) - {result.error}"
                )

            return result

        except asyncio.TimeoutError:
            duration_ms = timeout * 1000
            error = f"Job timed out after {timeout} seconds"
            logger.error(f"Cron job timeout: {job.name} ({job.id})")
            return ExecutionResult(
                success=False,
                error=error,
                duration_ms=duration_ms,
            )

        except Exception as e:
            duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            error = str(e)
            logger.exception(f"Cron job error: {job.name} ({job.id})")
            return ExecutionResult(
                success=False,
                error=error,
                duration_ms=duration_ms,
            )


# Default executor instance
default_executor = CronExecutor()


# Register default handlers
@default_executor.register_handler("system_event")
async def handle_system_event(payload: CronPayload) -> ExecutionResult:
    """Handle system event payloads.

    System events are logged but don't trigger agent processing.

    Args:
        payload: The payload to handle.

    Returns:
        Execution result.
    """
    logger.info(f"System event: {payload.message}")
    return ExecutionResult(success=True, output=f"Event logged: {payload.message}")


@default_executor.register_handler("agent_turn")
async def handle_agent_turn(payload: CronPayload) -> ExecutionResult:
    """Handle agent turn payloads.

    This is a placeholder that logs the message. The actual agent
    integration should be configured when setting up the cron service.

    Args:
        payload: The payload to handle.

    Returns:
        Execution result.
    """
    # This is a placeholder - actual implementation would call the agent
    logger.info(f"Agent turn requested: {payload.message}")
    return ExecutionResult(
        success=True,
        output=f"Agent turn queued: {payload.message}",
    )
