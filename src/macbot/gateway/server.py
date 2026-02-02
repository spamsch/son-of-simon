"""Gateway server for managing the agent system.

This module provides the main gateway server that orchestrates
all components of the MacBot system.
"""

import asyncio
import logging
from typing import Any

from macbot.core.command_queue import CommandQueue
from macbot.core.followup_queue import FollowupQueue, QueueMode, DropPolicy
from macbot.cron import CronService
from macbot.gateway.lanes import CommandLane, DEFAULT_LANE_CONCURRENCY
from macbot.gateway.run_loop import GatewayRunLoop

logger = logging.getLogger(__name__)


class GatewayServer:
    """Main gateway server for the MacBot system.

    The gateway server coordinates:
    - Command queue for task serialization
    - Followup queue for message buffering
    - Cron service for scheduled jobs
    - Run loop with signal handling

    Example:
        server = GatewayServer()
        await server.start()

        # Server is now running and handling:
        # - Incoming messages via followup queue
        # - Scheduled jobs via cron service
        # - All routed through command queue lanes
    """

    def __init__(
        self,
        cron_storage_path: str | None = None,
        main_lane_concurrency: int = 1,
        cron_lane_concurrency: int = 1,
        subagent_lane_concurrency: int = 2,
        queue_warn_after_ms: int = 5000,
        followup_mode: QueueMode = QueueMode.COLLECT,
        followup_cap: int = 100,
        followup_debounce_ms: int = 500,
        followup_drop_policy: DropPolicy = DropPolicy.OLD,
    ) -> None:
        """Initialize the gateway server.

        Args:
            cron_storage_path: Path for cron job storage.
            main_lane_concurrency: Max concurrent tasks in main lane.
            cron_lane_concurrency: Max concurrent tasks in cron lane.
            subagent_lane_concurrency: Max concurrent tasks in subagent lane.
            queue_warn_after_ms: Warning threshold for queue wait time.
            followup_mode: Mode for followup queue processing.
            followup_cap: Maximum followup queue size.
            followup_debounce_ms: Debounce delay for followup processing.
            followup_drop_policy: Policy when followup queue is full.
        """
        # Command queue
        self._command_queue = CommandQueue(warn_after_ms=queue_warn_after_ms)
        self._command_queue.set_lane_concurrency(CommandLane.MAIN, main_lane_concurrency)
        self._command_queue.set_lane_concurrency(CommandLane.CRON, cron_lane_concurrency)
        self._command_queue.set_lane_concurrency(CommandLane.SUBAGENT, subagent_lane_concurrency)

        # Followup queue
        self._followup_queue = FollowupQueue(
            mode=followup_mode,
            cap=followup_cap,
            debounce_ms=followup_debounce_ms,
            drop_policy=followup_drop_policy,
        )

        # Cron service
        self._cron_service = CronService(storage_path=cron_storage_path)

        # Run loop
        self._run_loop = GatewayRunLoop()
        self._setup_lifecycle_hooks()

    @property
    def command_queue(self) -> CommandQueue:
        """Get the command queue."""
        return self._command_queue

    @property
    def followup_queue(self) -> FollowupQueue:
        """Get the followup queue."""
        return self._followup_queue

    @property
    def cron_service(self) -> CronService:
        """Get the cron service."""
        return self._cron_service

    @property
    def run_loop(self) -> GatewayRunLoop:
        """Get the run loop."""
        return self._run_loop

    @property
    def is_running(self) -> bool:
        """Check if the server is running."""
        return self._run_loop.is_running

    def _setup_lifecycle_hooks(self) -> None:
        """Set up lifecycle callbacks for the run loop."""

        @self._run_loop.on_startup
        async def startup():
            logger.info("Starting gateway components...")
            await self._cron_service.start()
            logger.info("Gateway startup complete")

        @self._run_loop.on_shutdown
        async def shutdown():
            logger.info("Stopping gateway components...")
            await self._cron_service.stop()
            await self._command_queue.shutdown()
            logger.info("Gateway shutdown complete")

        @self._run_loop.on_restart
        async def restart():
            logger.info("Restarting gateway components...")
            # Reload cron jobs
            self._cron_service._load_jobs()
            logger.info("Gateway restart complete")

    async def start(self) -> None:
        """Start the gateway server.

        This starts all components and enters the main run loop.
        The server will run until a shutdown signal is received.
        """
        logger.info("Starting gateway server...")
        await self._run_loop.run()

    async def start_background(self) -> asyncio.Task:
        """Start the gateway server in the background.

        Returns:
            The background task running the server.
        """
        task = asyncio.create_task(
            self.start(),
            name="gateway_server",
        )
        # Give it a moment to start
        await asyncio.sleep(0.1)
        return task

    def stop(self) -> None:
        """Request the gateway server to stop."""
        self._run_loop.request_shutdown()

    def restart(self) -> None:
        """Request the gateway server to restart."""
        self._run_loop.request_restart()

    def get_stats(self) -> dict[str, Any]:
        """Get server statistics.

        Returns:
            Dictionary with server statistics.
        """
        return {
            "run_loop": {
                "state": self._run_loop.state.value,
                "start_count": self._run_loop.stats.start_count,
                "restart_count": self._run_loop.stats.restart_count,
                "total_runtime_seconds": self._run_loop.stats.total_runtime_seconds,
            },
            "command_queue": self._command_queue.get_all_stats(),
            "followup_queue": self._followup_queue.get_stats(),
            "cron": {
                "job_count": len(self._cron_service.list_jobs()),
                "storage_path": str(self._cron_service.storage_path),
            },
        }
