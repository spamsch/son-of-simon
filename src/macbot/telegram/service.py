"""Telegram service for macbot.

Provides a high-level service that polls for messages, processes them
through the agent, and sends back responses.
"""

import asyncio
import logging
import signal
import tempfile
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

    async def _transcribe_voice(self, voice_file_id: str) -> str | None:
        """Download and transcribe a voice message using OpenAI Whisper.

        Args:
            voice_file_id: Telegram file ID for the voice message

        Returns:
            Transcribed text or None if transcription failed
        """
        try:
            from openai import AsyncOpenAI
            from macbot.config import settings

            if not settings.openai_api_key:
                logger.error("OpenAI API key not configured for voice transcription")
                return None

            # Download the voice file from Telegram
            file = await self.bot._bot.get_file(voice_file_id)

            with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
                tmp_path = Path(tmp.name)
                await file.download_to_drive(tmp_path)

            try:
                # Transcribe using OpenAI Whisper
                client = AsyncOpenAI(api_key=settings.openai_api_key)
                with open(tmp_path, "rb") as audio_file:
                    transcript = await client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file,
                    )
                return transcript.text
            finally:
                # Clean up temp file
                tmp_path.unlink(missing_ok=True)

        except Exception as e:
            logger.exception(f"Error transcribing voice message: {e}")
            return None

    async def _summarize_for_voice(self, text: str) -> str:
        """Summarize a response into 1-2 sentences for TTS.

        Args:
            text: Full agent response text

        Returns:
            Short conversational summary
        """
        from macbot.config import settings
        from macbot.providers.base import Message
        from macbot.providers.litellm_provider import LiteLLMProvider

        model = settings.get_model()
        api_key = settings.get_api_key_for_model(model)
        provider = LiteLLMProvider(model=model, api_key=api_key)

        response = await provider.chat(
            messages=[Message(role="user", content=text)],
            system_prompt=(
                "Summarize this assistant response in 1-2 short conversational "
                "sentences, as if speaking to someone. Be concise and natural."
            ),
        )
        return response.content or text[:200]

    async def _text_to_voice(self, text: str) -> bytes:
        """Convert text to OGG Opus audio using OpenAI TTS.

        Args:
            text: Text to synthesize

        Returns:
            OGG Opus audio bytes
        """
        from openai import AsyncOpenAI
        from macbot.config import settings

        client = AsyncOpenAI(api_key=settings.openai_api_key)
        response = await client.audio.speech.create(
            model="tts-1",
            voice="shimmer",
            input=text,
            response_format="opus",
        )
        return response.content

    async def _send_voice_reply(self, response: str, chat_id: str) -> None:
        """Summarize a response and send it as a voice message.

        Failures are logged but never block the text response.

        Args:
            response: Full agent response text
            chat_id: Telegram chat ID to send to
        """
        try:
            summary = await self._summarize_for_voice(response)
            audio = await self._text_to_voice(summary)
            await self.bot.send_voice(chat_id, audio)
        except Exception as e:
            logger.warning(f"Voice reply failed (non-fatal): {e}")

    async def _process_update(self, update: Update) -> None:
        """Process a single update from Telegram.

        Args:
            update: Telegram Update object
        """
        if not update.message:
            return

        message = update.message
        user_id = message.from_user.id if message.from_user else None
        chat_id = str(message.chat_id)

        # Track whether original message was voice/audio
        is_voice = bool(message.voice or message.audio)

        # Handle voice messages (voice notes) and audio files
        if message.voice:
            text = await self._transcribe_voice(message.voice.file_id)
            if not text:
                await self.send_message(
                    "Sorry, I couldn't transcribe your voice message.",
                    chat_id,
                    parse_mode=None,
                )
                return
            logger.info(f"Transcribed voice message: {text[:50]}...")
        elif message.audio:
            text = await self._transcribe_voice(message.audio.file_id)
            if not text:
                await self.send_message(
                    "Sorry, I couldn't transcribe your audio file.",
                    chat_id,
                    parse_mode=None,
                )
                return
            logger.info(f"Transcribed audio file: {text[:50]}...")
        elif message.text:
            text = message.text
        else:
            # Neither text nor voice/audio
            return

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
                return

            # Send voice reply for voice/audio messages
            if is_voice and response:
                from macbot.config import settings
                if settings.openai_api_key:
                    await self._send_voice_reply(response, chat_id)
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
