"""Telegram service for macbot.

Provides a high-level service that polls for messages, processes them
through the agent, and sends back responses.
"""

import asyncio
import logging
import signal
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from telegram import Update
from telegram.error import TelegramError

from macbot.telegram.bot import TelegramBot

logger = logging.getLogger(__name__)

# PID file location
PID_FILE = Path.home() / ".macbot" / "telegram.pid"


class TelegramService:
    """Telegram integration service for macbot.

    This service:
    - Polls Telegram for new messages
    - Filters messages by allowed users (if configured)
    - Passes messages to a handler function
    - Sends handler responses back to the user
    """

    def __init__(
        self,
        bot_token: str,
        chat_id: str | None = None,
        allowed_users: list[str] | None = None,
    ):
        """Initialize the Telegram service.

        Args:
            bot_token: Telegram bot token from @BotFather
            chat_id: Default chat ID for outgoing messages
            allowed_users: List of allowed user IDs (empty/None = allow all)
        """
        self.bot = TelegramBot(bot_token)
        self.default_chat_id = chat_id
        self.allowed_users = set(allowed_users) if allowed_users else set()
        self._handler: Callable[[str, str], Awaitable[str]] | None = None
        self._running = False
        self._update_offset: int | None = None

    def set_message_handler(
        self,
        handler: Callable[[str, str], Awaitable[str]],
    ) -> None:
        """Set the handler for incoming messages.

        The handler receives (message_text, chat_id) and should return
        a response string to send back to the user.

        Args:
            handler: Async function that processes messages
        """
        self._handler = handler

    async def send_message(
        self,
        text: str,
        chat_id: str | None = None,
        parse_mode: str | None = "Markdown",
    ) -> bool:
        """Send a message to Telegram.

        Args:
            text: Message text to send
            chat_id: Target chat ID (uses default if not provided)
            parse_mode: Message parsing mode

        Returns:
            True if message was sent successfully
        """
        target_chat = chat_id or self.default_chat_id
        if not target_chat:
            logger.error("No chat_id provided and no default configured")
            return False

        try:
            return await self.bot.send_message(target_chat, text, parse_mode)
        except TelegramError as e:
            logger.error(f"Failed to send message: {e}")
            return False

    def _is_user_allowed(self, user_id: int) -> bool:
        """Check if a user is allowed to interact with the bot.

        Args:
            user_id: Telegram user ID

        Returns:
            True if user is allowed (or no restrictions configured)
        """
        if not self.allowed_users:
            return True
        return str(user_id) in self.allowed_users

    async def _process_update(self, update: Update) -> None:
        """Process a single update from Telegram.

        Args:
            update: Telegram Update object
        """
        if not update.message or not update.message.text:
            return

        message = update.message
        user_id = message.from_user.id if message.from_user else None
        chat_id = str(message.chat_id)
        text = message.text

        # Check user permissions
        if user_id and not self._is_user_allowed(user_id):
            logger.warning(f"Ignoring message from unauthorized user: {user_id}")
            return

        logger.info(f"Received message from {user_id} in chat {chat_id}: {text[:50]}...")

        # Process through handler if set
        if self._handler:
            try:
                # Send typing indicator
                await self.bot._bot.send_chat_action(chat_id, "typing")

                response = await self._handler(text, chat_id)
                if response:
                    # Try markdown first, fall back to plain text
                    try:
                        await self.send_message(response, chat_id, parse_mode="Markdown")
                    except TelegramError:
                        # Markdown parsing failed, send as plain text
                        await self.send_message(response, chat_id, parse_mode=None)
            except Exception as e:
                logger.exception(f"Error processing message: {e}")
                await self.send_message(
                    f"Error processing your request: {e}",
                    chat_id,
                    parse_mode=None,
                )
        else:
            logger.warning("No message handler configured")

    async def start(self, write_pid: bool = False) -> None:
        """Start the polling loop.

        Args:
            write_pid: Whether to write PID file (for daemon mode)
        """
        self._running = True

        if write_pid:
            PID_FILE.parent.mkdir(parents=True, exist_ok=True)
            PID_FILE.write_text(str(asyncio.current_task().get_coro().__self__))
            import os
            PID_FILE.write_text(str(os.getpid()))

        # Get bot info
        try:
            info = await self.bot.get_me()
            logger.info(f"Started Telegram service as @{info['username']}")
        except TelegramError as e:
            logger.error(f"Failed to connect to Telegram: {e}")
            raise

        # Main polling loop
        while self._running:
            try:
                updates = await self.bot.get_updates(
                    offset=self._update_offset,
                    timeout=30,
                )

                for update in updates:
                    # Update offset to acknowledge receipt
                    self._update_offset = update.update_id + 1
                    await self._process_update(update)

            except TelegramError as e:
                logger.error(f"Telegram error: {e}")
                await asyncio.sleep(5)  # Back off on error
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"Unexpected error in polling loop: {e}")
                await asyncio.sleep(5)

        # Cleanup
        if write_pid and PID_FILE.exists():
            PID_FILE.unlink()

        await self.bot.close()
        logger.info("Telegram service stopped")

    async def stop(self) -> None:
        """Stop the polling loop gracefully."""
        self._running = False


def get_pid() -> int | None:
    """Get the PID of a running Telegram service.

    Returns:
        PID if service is running, None otherwise
    """
    if not PID_FILE.exists():
        return None

    try:
        pid = int(PID_FILE.read_text().strip())
        # Check if process is running
        import os
        os.kill(pid, 0)
        return pid
    except (ValueError, ProcessLookupError, PermissionError):
        # Invalid PID or process not running
        if PID_FILE.exists():
            PID_FILE.unlink()
        return None


def stop_daemon() -> bool:
    """Stop a running Telegram daemon.

    Returns:
        True if daemon was stopped, False if not running
    """
    pid = get_pid()
    if not pid:
        return False

    import os
    try:
        os.kill(pid, signal.SIGTERM)
        # Wait for process to exit
        for _ in range(10):
            try:
                os.kill(pid, 0)
                asyncio.get_event_loop().run_until_complete(asyncio.sleep(0.5))
            except ProcessLookupError:
                break
        return True
    except ProcessLookupError:
        return False
