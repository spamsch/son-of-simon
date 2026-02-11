"""Tests for Telegram sleep/wake reconnection logic."""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from macbot.telegram.bot import TelegramBot, _make_bot


class TestTelegramBotTimeouts:
    """Verify that the Bot is created with explicit HTTP timeouts."""

    def test_make_bot_sets_timeouts(self) -> None:
        """_make_bot should configure an HTTPXRequest with our timeouts."""
        with patch("macbot.telegram.bot.HTTPXRequest") as mock_req_cls, \
             patch("macbot.telegram.bot.Bot") as mock_bot_cls:
            mock_req = MagicMock()
            mock_req_cls.return_value = mock_req

            _make_bot("123:abc")

            mock_req_cls.assert_called_once_with(
                connect_timeout=10.0,
                read_timeout=10.0,
                write_timeout=10.0,
                pool_timeout=5.0,
            )
            mock_bot_cls.assert_called_once_with(token="123:abc", request=mock_req)

    def test_init_uses_make_bot(self) -> None:
        """TelegramBot.__init__ should use _make_bot."""
        with patch("macbot.telegram.bot._make_bot") as mock_make:
            mock_make.return_value = MagicMock()
            bot = TelegramBot("123:abc")
            mock_make.assert_called_once_with("123:abc")
            assert bot._bot is mock_make.return_value


class TestTelegramBotRefresh:
    """Verify the connection refresh mechanism."""

    @pytest.mark.asyncio
    async def test_refresh_shuts_down_and_recreates(self) -> None:
        """refresh() should shutdown the old bot and create a new one."""
        with patch("macbot.telegram.bot._make_bot") as mock_make:
            old_bot = AsyncMock()
            new_bot = MagicMock()
            mock_make.side_effect = [old_bot, new_bot]

            bot = TelegramBot("123:abc")
            assert bot._bot is old_bot

            await bot.refresh()

            old_bot.shutdown.assert_awaited_once()
            assert bot._bot is new_bot

    @pytest.mark.asyncio
    async def test_refresh_tolerates_shutdown_error(self) -> None:
        """refresh() should still create a new bot even if shutdown raises."""
        with patch("macbot.telegram.bot._make_bot") as mock_make:
            old_bot = AsyncMock()
            old_bot.shutdown.side_effect = Exception("connection dead")
            new_bot = MagicMock()
            mock_make.side_effect = [old_bot, new_bot]

            bot = TelegramBot("123:abc")
            await bot.refresh()

            assert bot._bot is new_bot


class TestPollingLoopReconnect:
    """Verify that the polling loop detects sleep gaps and reconnects."""

    @pytest.mark.asyncio
    async def test_sleep_gap_triggers_refresh_on_success(self) -> None:
        """If get_updates succeeds but took too long, refresh the connection."""
        from macbot.telegram.service import TelegramService

        service = TelegramService(bot_token="123:abc")
        service.bot = AsyncMock(spec=TelegramBot)
        service.bot.get_updates = AsyncMock(return_value=[])
        service.bot.get_me = AsyncMock(return_value={"username": "test_bot"})
        service.bot.refresh = AsyncMock()
        service.bot.close = AsyncMock()

        call_count = 0

        async def fake_get_updates(offset=None, timeout=30):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # Simulate sleep/wake by advancing monotonic time
                # We can't actually sleep, so we patch time.monotonic
                return []
            # Stop after second call
            service._running = False
            return []

        service.bot.get_updates = AsyncMock(side_effect=fake_get_updates)

        # Patch time.monotonic to simulate a 120 s gap on the first poll
        real_monotonic = time.monotonic
        call_times = iter([
            100.0,   # poll_start for call 1
            220.0,   # elapsed check after call 1 (120 s gap -> triggers refresh)
            220.0,   # poll_start for call 2
            250.0,   # elapsed check after call 2 (normal)
        ])

        with patch("macbot.telegram.service.time") as mock_time:
            mock_time.monotonic = lambda: next(call_times)
            await service.start()

        service.bot.refresh.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_sleep_gap_triggers_refresh_on_error(self) -> None:
        """If get_updates fails after a sleep gap, refresh and retry immediately."""
        from telegram.error import TelegramError

        from macbot.telegram.service import TelegramService

        service = TelegramService(bot_token="123:abc")
        service.bot = AsyncMock(spec=TelegramBot)
        service.bot.get_me = AsyncMock(return_value={"username": "test_bot"})
        service.bot.refresh = AsyncMock()
        service.bot.close = AsyncMock()

        call_count = 0

        async def fake_get_updates(offset=None, timeout=30):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise TelegramError("Connection reset")
            service._running = False
            return []

        service.bot.get_updates = AsyncMock(side_effect=fake_get_updates)

        # First call: start=100, error caught at elapsed=200 (100 s gap)
        # Second call: start=200, success at elapsed=230 (normal)
        call_times = iter([
            100.0,   # poll_start for call 1
            200.0,   # elapsed in except block (100 s gap -> refresh)
            200.0,   # poll_start for call 2
            230.0,   # elapsed after call 2
        ])

        with patch("macbot.telegram.service.time") as mock_time:
            mock_time.monotonic = lambda: next(call_times)
            await service.start()

        service.bot.refresh.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_normal_error_uses_exponential_backoff(self) -> None:
        """Normal errors (not sleep gaps) should use exponential backoff."""
        from telegram.error import TelegramError

        from macbot.telegram.service import TelegramService

        service = TelegramService(bot_token="123:abc")
        service.bot = AsyncMock(spec=TelegramBot)
        service.bot.get_me = AsyncMock(return_value={"username": "test_bot"})
        service.bot.refresh = AsyncMock()
        service.bot.close = AsyncMock()

        call_count = 0

        async def fake_get_updates(offset=None, timeout=30):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise TelegramError("Server error")
            service._running = False
            return []

        service.bot.get_updates = AsyncMock(side_effect=fake_get_updates)

        # All calls have normal timing (no sleep gap)
        monotonic_value = [100.0]

        def advancing_monotonic():
            monotonic_value[0] += 1.0
            return monotonic_value[0]

        sleep_durations = []
        original_sleep = asyncio.sleep

        async def tracking_sleep(duration):
            sleep_durations.append(duration)

        with patch("macbot.telegram.service.time") as mock_time, \
             patch("macbot.telegram.service.asyncio.sleep", side_effect=tracking_sleep):
            mock_time.monotonic = advancing_monotonic
            await service.start()

        # Should NOT have refreshed (no sleep gap)
        service.bot.refresh.assert_not_awaited()

        # Should have backed off exponentially: 2^1=2, 2^2=4
        assert sleep_durations == [2, 4]

    @pytest.mark.asyncio
    async def test_no_refresh_on_normal_poll(self) -> None:
        """Normal polls that complete within threshold should not refresh."""
        from macbot.telegram.service import TelegramService

        service = TelegramService(bot_token="123:abc")
        service.bot = AsyncMock(spec=TelegramBot)
        service.bot.get_updates = AsyncMock(return_value=[])
        service.bot.get_me = AsyncMock(return_value={"username": "test_bot"})
        service.bot.refresh = AsyncMock()
        service.bot.close = AsyncMock()

        call_count = 0

        async def fake_get_updates(offset=None, timeout=30):
            nonlocal call_count
            call_count += 1
            if call_count >= 3:
                service._running = False
            return []

        service.bot.get_updates = AsyncMock(side_effect=fake_get_updates)

        # All polls take ~30 s (normal long-poll timeout)
        monotonic_value = [100.0]

        def advancing_monotonic():
            monotonic_value[0] += 15.0  # 15 s per half-call = 30 s per cycle
            return monotonic_value[0]

        with patch("macbot.telegram.service.time") as mock_time:
            mock_time.monotonic = advancing_monotonic
            await service.start()

        service.bot.refresh.assert_not_awaited()
