"""Process loop with signal handling for the gateway.

This module provides the run loop that manages the gateway lifecycle,
including graceful shutdown and restart capabilities via Unix signals.
"""

import asyncio
import logging
import signal
import sys
from dataclasses import dataclass, field
from enum import Enum
from typing import Awaitable, Callable

logger = logging.getLogger(__name__)


class LoopState(str, Enum):
    """State of the run loop.

    Attributes:
        STARTING: Loop is initializing.
        RUNNING: Loop is actively processing.
        RESTARTING: Loop is restarting components.
        STOPPING: Loop is shutting down.
        STOPPED: Loop has stopped.
    """

    STARTING = "starting"
    RUNNING = "running"
    RESTARTING = "restarting"
    STOPPING = "stopping"
    STOPPED = "stopped"


@dataclass
class LoopStats:
    """Statistics for the run loop.

    Attributes:
        start_count: Number of times the loop has started.
        restart_count: Number of restarts triggered.
        last_start_time: Timestamp of last start.
        total_runtime_seconds: Total time spent running.
    """

    start_count: int = 0
    restart_count: int = 0
    last_start_time: float = 0
    total_runtime_seconds: float = 0


# Type aliases for callbacks
StartupCallback = Callable[[], Awaitable[None]]
ShutdownCallback = Callable[[], Awaitable[None]]
RestartCallback = Callable[[], Awaitable[None]]


class GatewayRunLoop:
    """Run loop with signal handling for the gateway.

    The run loop manages the lifecycle of the gateway, handling:
    - Graceful startup and shutdown
    - Signal-based restart (SIGUSR1)
    - Signal-based shutdown (SIGTERM, SIGINT)
    - State tracking and statistics

    Example:
        loop = GatewayRunLoop()

        @loop.on_startup
        async def startup():
            print("Starting up...")

        @loop.on_shutdown
        async def shutdown():
            print("Shutting down...")

        await loop.run()

    Signals:
        SIGUSR1: Trigger a restart
        SIGTERM: Graceful shutdown
        SIGINT: Graceful shutdown (Ctrl+C)
    """

    def __init__(self) -> None:
        """Initialize the run loop."""
        self._state = LoopState.STOPPED
        self._shutdown_event = asyncio.Event()
        self._restart_event = asyncio.Event()
        self._stats = LoopStats()

        self._startup_callbacks: list[StartupCallback] = []
        self._shutdown_callbacks: list[ShutdownCallback] = []
        self._restart_callbacks: list[RestartCallback] = []

        self._main_task: asyncio.Task | None = None

    @property
    def state(self) -> LoopState:
        """Get the current loop state."""
        return self._state

    @property
    def stats(self) -> LoopStats:
        """Get loop statistics."""
        return self._stats

    @property
    def is_running(self) -> bool:
        """Check if the loop is running."""
        return self._state == LoopState.RUNNING

    def on_startup(self, callback: StartupCallback) -> StartupCallback:
        """Register a startup callback.

        Args:
            callback: Async function to call on startup.

        Returns:
            The callback (for decorator use).
        """
        self._startup_callbacks.append(callback)
        return callback

    def on_shutdown(self, callback: ShutdownCallback) -> ShutdownCallback:
        """Register a shutdown callback.

        Args:
            callback: Async function to call on shutdown.

        Returns:
            The callback (for decorator use).
        """
        self._shutdown_callbacks.append(callback)
        return callback

    def on_restart(self, callback: RestartCallback) -> RestartCallback:
        """Register a restart callback.

        Args:
            callback: Async function to call on restart.

        Returns:
            The callback (for decorator use).
        """
        self._restart_callbacks.append(callback)
        return callback

    def _setup_signals(self) -> None:
        """Set up Unix signal handlers."""
        # Only set up signals on Unix systems
        if sys.platform == "win32":
            logger.warning("Signal handling not fully supported on Windows")
            return

        loop = asyncio.get_running_loop()

        # SIGUSR1 triggers a restart
        loop.add_signal_handler(signal.SIGUSR1, self._handle_restart_signal)

        # SIGTERM and SIGINT trigger shutdown
        loop.add_signal_handler(signal.SIGTERM, self._handle_shutdown_signal)
        loop.add_signal_handler(signal.SIGINT, self._handle_shutdown_signal)

        logger.debug("Signal handlers installed")

    def _remove_signals(self) -> None:
        """Remove signal handlers."""
        if sys.platform == "win32":
            return

        loop = asyncio.get_running_loop()

        try:
            loop.remove_signal_handler(signal.SIGUSR1)
            loop.remove_signal_handler(signal.SIGTERM)
            loop.remove_signal_handler(signal.SIGINT)
        except Exception:
            pass

    def _handle_restart_signal(self) -> None:
        """Handle SIGUSR1 signal for restart."""
        logger.info("Received SIGUSR1 - triggering restart")
        self._restart_event.set()

    def _handle_shutdown_signal(self) -> None:
        """Handle SIGTERM/SIGINT signal for shutdown."""
        logger.info("Received shutdown signal")
        self._shutdown_event.set()

    async def _run_startup(self) -> None:
        """Run startup callbacks."""
        self._state = LoopState.STARTING
        logger.info("Running startup callbacks...")

        for callback in self._startup_callbacks:
            try:
                await callback()
            except Exception as e:
                logger.exception(f"Error in startup callback: {e}")
                raise

        import time
        self._stats.start_count += 1
        self._stats.last_start_time = time.time()

    async def _run_shutdown(self) -> None:
        """Run shutdown callbacks."""
        self._state = LoopState.STOPPING
        logger.info("Running shutdown callbacks...")

        # Run in reverse order (LIFO)
        for callback in reversed(self._shutdown_callbacks):
            try:
                await callback()
            except Exception as e:
                logger.exception(f"Error in shutdown callback: {e}")

        import time
        if self._stats.last_start_time > 0:
            self._stats.total_runtime_seconds += time.time() - self._stats.last_start_time

    async def _run_restart(self) -> None:
        """Run restart callbacks."""
        self._state = LoopState.RESTARTING
        logger.info("Running restart callbacks...")
        self._stats.restart_count += 1

        for callback in self._restart_callbacks:
            try:
                await callback()
            except Exception as e:
                logger.exception(f"Error in restart callback: {e}")

    async def _wait_for_signal(self) -> str:
        """Wait for either shutdown or restart signal.

        Returns:
            "shutdown" or "restart" depending on which signal was received.
        """
        # Create tasks for both events
        shutdown_task = asyncio.create_task(
            self._shutdown_event.wait(),
            name="wait_shutdown",
        )
        restart_task = asyncio.create_task(
            self._restart_event.wait(),
            name="wait_restart",
        )

        # Wait for either
        done, pending = await asyncio.wait(
            [shutdown_task, restart_task],
            return_when=asyncio.FIRST_COMPLETED,
        )

        # Cancel pending tasks
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        # Determine which completed
        if shutdown_task in done:
            return "shutdown"
        return "restart"

    async def run(self, main_task: Callable[[], Awaitable[None]] | None = None) -> None:
        """Run the main loop.

        Args:
            main_task: Optional main task to run alongside signal handling.
                      If provided, the loop will also stop when this task completes.
        """
        self._setup_signals()

        try:
            await self._run_startup()
            self._state = LoopState.RUNNING
            logger.info("Gateway run loop started")

            while True:
                self._shutdown_event.clear()
                self._restart_event.clear()

                # Create tasks
                tasks = []

                if main_task:
                    self._main_task = asyncio.create_task(
                        main_task(),
                        name="main_task",
                    )
                    tasks.append(self._main_task)

                signal_task = asyncio.create_task(
                    self._wait_for_signal(),
                    name="signal_wait",
                )
                tasks.append(signal_task)

                # Wait for something to happen
                done, pending = await asyncio.wait(
                    tasks,
                    return_when=asyncio.FIRST_COMPLETED,
                )

                # Cancel pending tasks
                for task in pending:
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass

                # Check what completed
                for task in done:
                    if task.get_name() == "signal_wait":
                        result = task.result()
                        if result == "shutdown":
                            logger.info("Shutdown requested")
                            await self._run_shutdown()
                            self._state = LoopState.STOPPED
                            return
                        elif result == "restart":
                            logger.info("Restart requested")
                            await self._run_restart()
                            # Continue loop
                            continue
                    elif task.get_name() == "main_task":
                        # Main task completed
                        if task.exception():
                            logger.error(f"Main task failed: {task.exception()}")
                        else:
                            logger.info("Main task completed")
                        await self._run_shutdown()
                        self._state = LoopState.STOPPED
                        return

        except Exception as e:
            logger.exception(f"Error in run loop: {e}")
            await self._run_shutdown()
            self._state = LoopState.STOPPED
            raise

        finally:
            self._remove_signals()

    def request_shutdown(self) -> None:
        """Request a shutdown from outside the loop."""
        self._shutdown_event.set()

    def request_restart(self) -> None:
        """Request a restart from outside the loop."""
        self._restart_event.set()
