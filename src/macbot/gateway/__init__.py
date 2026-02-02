"""Gateway service for orchestrating the MacBot system.

This package provides the main gateway server that coordinates
all components including command queue, followup queue, cron service,
and the run loop with signal handling.

Example:
    from macbot.gateway import GatewayServer

    server = GatewayServer()
    await server.start()
"""

from macbot.gateway.lanes import CommandLane, DEFAULT_LANE_CONCURRENCY
from macbot.gateway.run_loop import GatewayRunLoop, LoopState, LoopStats
from macbot.gateway.server import GatewayServer

__all__ = [
    # Server
    "GatewayServer",
    # Run loop
    "GatewayRunLoop",
    "LoopState",
    "LoopStats",
    # Lanes
    "CommandLane",
    "DEFAULT_LANE_CONCURRENCY",
]
