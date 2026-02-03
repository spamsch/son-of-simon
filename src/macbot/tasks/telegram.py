"""Tasks: Telegram Integration

Provides tasks for the agent to send messages via Telegram.
"""

from typing import Any

from macbot.config import settings
from macbot.tasks.base import Task


class TelegramSendTask(Task):
    """Send a message via Telegram."""

    @property
    def name(self) -> str:
        return "telegram_send"

    @property
    def description(self) -> str:
        return (
            "Send a message to the user via Telegram. Use this to proactively "
            "notify the user about important information, task completion, or alerts. "
            "Only works when Telegram is configured."
        )

    async def execute(self, message: str, chat_id: str | None = None) -> dict[str, Any]:
        """Send a message via Telegram.

        Args:
            message: The message text to send
            chat_id: Optional chat ID (uses default if not provided)

        Returns:
            Dictionary with result status
        """
        from macbot.telegram import TelegramBot

        token = settings.telegram_bot_token
        if not token:
            return {
                "success": False,
                "error": "Telegram not configured (MACBOT_TELEGRAM_BOT_TOKEN not set)",
            }

        target_chat = chat_id or settings.telegram_chat_id
        if not target_chat:
            return {
                "success": False,
                "error": "No chat_id provided and MACBOT_TELEGRAM_CHAT_ID not set",
            }

        try:
            bot = TelegramBot(token)
            await bot.send_message(target_chat, message)
            await bot.close()
            return {
                "success": True,
                "message": "Message sent successfully",
                "chat_id": target_chat,
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to send message: {e}",
            }


def register_telegram_tasks(registry) -> None:
    """Register Telegram tasks with a registry.

    Args:
        registry: TaskRegistry to register tasks with.
    """
    registry.register(TelegramSendTask())
