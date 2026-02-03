"""Low-level Telegram bot API wrapper.

Provides a simple async interface for sending and receiving messages
via the Telegram Bot API.
"""

import logging
from typing import Any

from telegram import Bot, Update
from telegram.error import TelegramError

logger = logging.getLogger(__name__)


class TelegramBot:
    """Simple Telegram bot wrapper using python-telegram-bot.

    This class provides low-level access to the Telegram Bot API
    for sending messages and receiving updates via long-polling.
    """

    def __init__(self, token: str):
        """Initialize the bot with a token.

        Args:
            token: Telegram bot token from @BotFather
        """
        self.token = token
        self._bot = Bot(token=token)

    async def get_me(self) -> dict[str, Any]:
        """Get information about the bot.

        Returns:
            Dictionary with bot info including id, username, first_name

        Raises:
            TelegramError: If the API call fails
        """
        user = await self._bot.get_me()
        return {
            "id": user.id,
            "username": user.username,
            "first_name": user.first_name,
            "is_bot": user.is_bot,
        }

    async def send_message(
        self,
        chat_id: str | int,
        text: str,
        parse_mode: str | None = "Markdown",
    ) -> bool:
        """Send a message to a chat.

        Args:
            chat_id: Telegram chat ID to send to
            text: Message text (max 4096 characters)
            parse_mode: Message parsing mode (Markdown, HTML, or None)

        Returns:
            True if message was sent successfully

        Raises:
            TelegramError: If the API call fails
        """
        # Telegram has a 4096 character limit
        if len(text) > 4096:
            # Split into chunks
            chunks = [text[i:i + 4000] for i in range(0, len(text), 4000)]
            for chunk in chunks:
                await self._bot.send_message(
                    chat_id=chat_id,
                    text=chunk,
                    parse_mode=parse_mode,
                )
            return True

        await self._bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=parse_mode,
        )
        return True

    async def get_updates(
        self,
        offset: int | None = None,
        timeout: int = 30,
    ) -> list[Update]:
        """Get new updates via long-polling.

        Args:
            offset: Identifier of the first update to be returned
            timeout: Timeout in seconds for long polling

        Returns:
            List of Update objects
        """
        updates = await self._bot.get_updates(
            offset=offset,
            timeout=timeout,
            allowed_updates=["message"],
        )
        return list(updates)

    async def close(self) -> None:
        """Close the bot connection."""
        await self._bot.shutdown()


async def validate_token(token: str) -> tuple[bool, str]:
    """Validate a Telegram bot token by calling getMe.

    Args:
        token: Telegram bot token to validate

    Returns:
        Tuple of (success, message) where message is either
        the bot username or an error description
    """
    if not token or ":" not in token:
        return False, "Invalid token format (expected 'ID:SECRET')"

    try:
        bot = TelegramBot(token)
        info = await bot.get_me()
        await bot.close()
        return True, f"@{info['username']}"
    except TelegramError as e:
        return False, f"API error: {e.message}"
    except Exception as e:
        return False, f"Connection error: {e}"
