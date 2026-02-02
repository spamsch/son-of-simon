"""Lane-based command queue for task serialization.

This module provides a queue system with named lanes, allowing different types
of tasks to be processed with configurable concurrency limits per lane.
Inspired by the OpenClaw architecture.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CommandLane(str, Enum):
    """Predefined command lanes for different task types."""

    MAIN = "main"  # Default agent workflow
    CRON = "cron"  # Scheduled job processing
    SUBAGENT = "subagent"  # Sub-agent execution


@dataclass
class QueueEntry:
    """An entry in the command queue.

    Attributes:
        task: The async callable to execute.
        future: Future to set with the result.
        enqueued_at: Timestamp when the entry was queued.
        warn_after_ms: Log a warning if task waits longer than this.
    """

    task: Callable[[], Awaitable[Any]]
    future: asyncio.Future[Any]
    enqueued_at: float = field(default_factory=time.time)
    warn_after_ms: int = 5000

    @property
    def wait_time_ms(self) -> float:
        """Get the time this entry has been waiting in milliseconds."""
        return (time.time() - self.enqueued_at) * 1000


@dataclass
class LaneState:
    """State for a single command lane.

    Attributes:
        name: Lane identifier.
        queue: The async queue holding pending entries.
        active: Number of currently executing tasks.
        max_concurrent: Maximum concurrent tasks allowed.
        draining: Whether the lane is draining (no new tasks accepted).
    """

    name: str
    queue: asyncio.Queue[QueueEntry] = field(default_factory=asyncio.Queue)
    active: int = 0
    max_concurrent: int = 1
    draining: bool = False
    _processor_task: asyncio.Task[None] | None = field(default=None, repr=False)


class CommandQueue:
    """Lane-based task queue with configurable concurrency.

    The command queue organizes tasks into named lanes, each with its own
    concurrency limit. This allows different types of tasks (main workflow,
    cron jobs, sub-agents) to be processed independently without blocking
    each other unnecessarily.

    Example:
        queue = CommandQueue()
        queue.set_lane_concurrency(CommandLane.MAIN, 1)
        queue.set_lane_concurrency(CommandLane.SUBAGENT, 2)

        # Enqueue a task
        result = await queue.enqueue(my_async_task, lane=CommandLane.MAIN)
    """

    def __init__(self, warn_after_ms: int = 5000) -> None:
        """Initialize the command queue.

        Args:
            warn_after_ms: Default warning threshold for queue wait time.
        """
        self._lanes: dict[str, LaneState] = {}
        self._warn_after_ms = warn_after_ms
        self._started = False

    def _get_lane(self, lane: str | CommandLane) -> LaneState:
        """Get or create a lane state.

        Args:
            lane: Lane name or CommandLane enum value.

        Returns:
            The LaneState for the specified lane.
        """
        lane_name = lane.value if isinstance(lane, CommandLane) else lane
        if lane_name not in self._lanes:
            self._lanes[lane_name] = LaneState(name=lane_name)
        return self._lanes[lane_name]

    def set_lane_concurrency(
        self, lane: str | CommandLane, max_concurrent: int
    ) -> None:
        """Set the maximum concurrency for a lane.

        Args:
            lane: Lane name or CommandLane enum value.
            max_concurrent: Maximum concurrent tasks for this lane.
        """
        state = self._get_lane(lane)
        state.max_concurrent = max_concurrent
        logger.debug(f"Lane '{state.name}' concurrency set to {max_concurrent}")

    async def enqueue(
        self,
        task: Callable[[], Awaitable[T]],
        lane: str | CommandLane = CommandLane.MAIN,
        warn_after_ms: int | None = None,
    ) -> T:
        """Enqueue a task for execution in the specified lane.

        The task will be executed when a slot becomes available in the lane.
        This method blocks until the task completes.

        Args:
            task: Async callable to execute.
            lane: Lane to queue the task in.
            warn_after_ms: Override default warning threshold.

        Returns:
            The result of the task execution.

        Raises:
            RuntimeError: If the lane is draining and not accepting new tasks.
            Exception: Any exception raised by the task.
        """
        state = self._get_lane(lane)

        if state.draining:
            raise RuntimeError(f"Lane '{state.name}' is draining, not accepting new tasks")

        # Ensure processor is running
        self._ensure_processor_running(state)

        loop = asyncio.get_running_loop()
        future: asyncio.Future[T] = loop.create_future()

        entry = QueueEntry(
            task=task,
            future=future,
            warn_after_ms=warn_after_ms if warn_after_ms is not None else self._warn_after_ms,
        )

        await state.queue.put(entry)
        logger.debug(f"Task enqueued in lane '{state.name}', queue size: {state.queue.qsize()}")

        return await future

    def _ensure_processor_running(self, state: LaneState) -> None:
        """Ensure the processor task is running for a lane."""
        if state._processor_task is None or state._processor_task.done():
            state._processor_task = asyncio.create_task(
                self._process_lane(state),
                name=f"command_queue_processor_{state.name}",
            )

    async def _process_lane(self, state: LaneState) -> None:
        """Process tasks from a lane's queue.

        This runs continuously, executing tasks up to the concurrency limit.

        Args:
            state: The lane state to process.
        """
        while True:
            try:
                # Wait for a task if at capacity
                entry = await state.queue.get()

                # Check wait time and warn if needed
                wait_time = entry.wait_time_ms
                if wait_time > entry.warn_after_ms:
                    logger.warning(
                        f"Task in lane '{state.name}' waited {wait_time:.0f}ms "
                        f"(threshold: {entry.warn_after_ms}ms)"
                    )

                # Wait for a slot if at capacity
                while state.active >= state.max_concurrent:
                    await asyncio.sleep(0.01)

                # Execute the task
                state.active += 1
                try:
                    asyncio.create_task(
                        self._execute_entry(state, entry),
                        name=f"command_queue_task_{state.name}",
                    )
                except Exception:
                    state.active -= 1
                    raise

            except asyncio.CancelledError:
                logger.debug(f"Lane '{state.name}' processor cancelled")
                break
            except Exception as e:
                logger.error(f"Error in lane '{state.name}' processor: {e}")

    async def _execute_entry(self, state: LaneState, entry: QueueEntry) -> None:
        """Execute a single queue entry.

        Args:
            state: The lane state.
            entry: The queue entry to execute.
        """
        try:
            result = await entry.task()
            if not entry.future.done():
                entry.future.set_result(result)
        except Exception as e:
            if not entry.future.done():
                entry.future.set_exception(e)
        finally:
            state.active -= 1
            state.queue.task_done()

    async def drain_lane(
        self, lane: str | CommandLane, timeout: float | None = None
    ) -> None:
        """Drain a lane, waiting for all pending tasks to complete.

        Once draining starts, no new tasks are accepted in the lane.

        Args:
            lane: Lane to drain.
            timeout: Maximum time to wait for drain (None for no limit).

        Raises:
            asyncio.TimeoutError: If timeout is exceeded.
        """
        state = self._get_lane(lane)
        state.draining = True

        try:
            if timeout is not None:
                await asyncio.wait_for(state.queue.join(), timeout=timeout)
            else:
                await state.queue.join()
        finally:
            state.draining = False

        logger.info(f"Lane '{state.name}' drained")

    async def drain_all(self, timeout: float | None = None) -> None:
        """Drain all lanes.

        Args:
            timeout: Maximum time to wait for all lanes to drain.

        Raises:
            asyncio.TimeoutError: If timeout is exceeded.
        """
        tasks = [self.drain_lane(lane) for lane in self._lanes]
        if timeout is not None:
            await asyncio.wait_for(asyncio.gather(*tasks), timeout=timeout)
        else:
            await asyncio.gather(*tasks)

    def get_lane_stats(self, lane: str | CommandLane) -> dict[str, Any]:
        """Get statistics for a lane.

        Args:
            lane: Lane to get stats for.

        Returns:
            Dictionary with lane statistics.
        """
        state = self._get_lane(lane)
        return {
            "name": state.name,
            "queue_size": state.queue.qsize(),
            "active": state.active,
            "max_concurrent": state.max_concurrent,
            "draining": state.draining,
        }

    def get_all_stats(self) -> dict[str, dict[str, Any]]:
        """Get statistics for all lanes.

        Returns:
            Dictionary mapping lane names to their statistics.
        """
        return {name: self.get_lane_stats(name) for name in self._lanes}

    async def shutdown(self, timeout: float = 5.0) -> None:
        """Gracefully shutdown the queue.

        Args:
            timeout: Maximum time to wait for pending tasks.
        """
        logger.info("Shutting down command queue...")

        # Stop accepting new tasks
        for state in self._lanes.values():
            state.draining = True

        # Wait for pending tasks
        try:
            await asyncio.wait_for(self.drain_all(), timeout=timeout)
        except asyncio.TimeoutError:
            logger.warning("Timeout waiting for tasks to complete during shutdown")

        # Cancel processor tasks
        for state in self._lanes.values():
            if state._processor_task and not state._processor_task.done():
                state._processor_task.cancel()
                try:
                    await state._processor_task
                except asyncio.CancelledError:
                    pass

        logger.info("Command queue shutdown complete")
