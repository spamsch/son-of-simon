"""Time tracking module for MacBot.

Provides time tracking functionality with start/stop timers and reporting.
"""

from macbot.time_tracking.storage import TimeTrackingStorage, format_duration, get_storage

__all__ = ["TimeTrackingStorage", "get_storage", "format_duration"]
