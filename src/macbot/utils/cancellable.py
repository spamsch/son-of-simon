"""Run async tasks with Escape key cancellation support."""

import asyncio
import sys
import termios
import tty
from typing import Any, Coroutine, TypeVar

T = TypeVar("T")


class EscapeCancelled(Exception):
    """Raised when operation is cancelled via Escape key."""
    pass


async def _check_escape(stop_event: asyncio.Event) -> None:
    """Monitor for Escape key press in a non-blocking way.

    Args:
        stop_event: Event to signal when Escape is pressed
    """
    loop = asyncio.get_event_loop()
    fd = sys.stdin.fileno()

    # Save original terminal settings
    old_settings = termios.tcgetattr(fd)

    try:
        # Set terminal to raw mode (no buffering, immediate char read)
        tty.setraw(fd)

        while not stop_event.is_set():
            # Check if there's input available (non-blocking)
            ready = await loop.run_in_executor(
                None,
                lambda: _select_stdin(0.1)  # 100ms timeout
            )

            if ready:
                # Read one character
                char = await loop.run_in_executor(None, lambda: sys.stdin.read(1))
                if char == '\x1b':  # Escape key
                    stop_event.set()
                    return
    finally:
        # Restore terminal settings
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def _select_stdin(timeout: float) -> bool:
    """Check if stdin has data available."""
    import select
    readable, _, _ = select.select([sys.stdin], [], [], timeout)
    return bool(readable)


async def run_with_escape_cancel(
    coro: Coroutine[Any, Any, T],
    cancel_message: str = "\n[dim][Cancelled by Escape][/dim]",
) -> tuple[T | None, bool]:
    """Run a coroutine with Escape key cancellation support.

    Args:
        coro: The coroutine to run
        cancel_message: Message to display on cancellation (ignored, caller handles)

    Returns:
        Tuple of (result, was_cancelled):
        - result: The coroutine result, or None if cancelled
        - was_cancelled: True if cancelled via Escape

    Example:
        result, cancelled = await run_with_escape_cancel(agent.run(goal))
        if cancelled:
            print("Operation cancelled")
        else:
            print(f"Result: {result}")
    """
    # Check if stdin is a tty (interactive terminal)
    if not sys.stdin.isatty():
        # Non-interactive mode, just run the coroutine
        result = await coro
        return result, False

    stop_event = asyncio.Event()

    # Create tasks
    main_task = asyncio.create_task(coro)
    escape_task = asyncio.create_task(_check_escape(stop_event))

    try:
        # Wait for either the main task to complete or Escape to be pressed
        done, pending = await asyncio.wait(
            [main_task, escape_task],
            return_when=asyncio.FIRST_COMPLETED,
        )

        # Check what finished
        if main_task in done:
            # Main task completed normally
            stop_event.set()  # Signal escape checker to stop
            escape_task.cancel()
            try:
                await escape_task
            except asyncio.CancelledError:
                pass
            return main_task.result(), False
        else:
            # Escape was pressed
            main_task.cancel()
            try:
                await main_task
            except asyncio.CancelledError:
                pass
            return None, True

    except Exception:
        # Clean up on any error
        stop_event.set()
        main_task.cancel()
        escape_task.cancel()
        raise
