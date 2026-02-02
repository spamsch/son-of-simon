"""Lane configuration for the gateway.

This module defines the command lanes used by the gateway
for organizing different types of work.
"""

from enum import Enum


class CommandLane(str, Enum):
    """Predefined command lanes for different task types.

    Lanes provide isolation and concurrency control for different
    types of work processed by the gateway.

    Attributes:
        MAIN: Default agent workflow lane. Single-threaded to ensure
              conversation coherence.
        CRON: Scheduled job processing lane. May run concurrently
              with main lane.
        SUBAGENT: Sub-agent execution lane. Can have higher concurrency
                  for parallel sub-agent processing.
    """

    MAIN = "main"
    CRON = "cron"
    SUBAGENT = "subagent"


# Default concurrency settings for each lane
DEFAULT_LANE_CONCURRENCY = {
    CommandLane.MAIN: 1,
    CommandLane.CRON: 1,
    CommandLane.SUBAGENT: 2,
}
