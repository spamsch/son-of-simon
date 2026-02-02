"""Followup queue for handling messages arriving while agent is busy.

This module provides a queue system for buffering incoming messages when
the agent is processing a request. Messages can be collected, debounced,
and processed in various modes.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable

logger = logging.getLogger(__name__)


class QueueMode(str, Enum):
    """Mode for processing queued messages.

    Attributes:
        COLLECT: Batch same-channel messages together for processing.
        FOLLOWUP: Process messages one at a time in order.
        INTERRUPT: Allow new messages to interrupt current processing.
    """

    COLLECT = "collect"
    FOLLOWUP = "followup"
    INTERRUPT = "interrupt"


class DropPolicy(str, Enum):
    """Policy for handling queue overflow.

    Attributes:
        OLD: Drop oldest messages when queue is full.
        NEW: Reject new messages when queue is full.
        SUMMARIZE: Summarize older messages to make room.
    """

    OLD = "old"
    NEW = "new"
    SUMMARIZE = "summarize"


@dataclass
class FollowupItem:
    """An item in the followup queue.

    Attributes:
        prompt: The message content to process.
        message_id: Optional identifier for the original message.
        enqueued_at: Timestamp when the item was queued.
        channel: Optional channel identifier for routing.
        metadata: Optional additional data associated with the item.
    """

    prompt: str
    message_id: str | None = None
    enqueued_at: float = field(default_factory=time.time)
    channel: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def age_ms(self) -> float:
        """Get the age of this item in milliseconds."""
        return (time.time() - self.enqueued_at) * 1000


@dataclass
class ChannelQueue:
    """Queue state for a single channel.

    Attributes:
        items: List of queued items.
        last_activity: Timestamp of last activity.
    """

    items: list[FollowupItem] = field(default_factory=list)
    last_activity: float = field(default_factory=time.time)


# Type alias for the processor callback
ProcessorCallback = Callable[[list[FollowupItem]], Awaitable[None]]


class FollowupQueue:
    """Queue for handling followup messages.

    The followup queue buffers incoming messages while the agent is busy,
    allowing them to be processed in various modes (collected, sequential,
    or interruptible).

    Example:
        queue = FollowupQueue(
            mode=QueueMode.COLLECT,
            cap=100,
            debounce_ms=500,
        )

        # Enqueue incoming messages
        await queue.enqueue(FollowupItem(prompt="Hello"))
        await queue.enqueue(FollowupItem(prompt="World"))

        # Drain and process
        async def processor(items):
            for item in items:
                print(item.prompt)

        await queue.drain(processor)
    """

    def __init__(
        self,
        mode: QueueMode = QueueMode.COLLECT,
        cap: int = 100,
        debounce_ms: int = 500,
        drop_policy: DropPolicy = DropPolicy.OLD,
    ) -> None:
        """Initialize the followup queue.

        Args:
            mode: Processing mode for queued messages.
            cap: Maximum number of items in the queue.
            debounce_ms: Milliseconds to wait for additional messages.
            drop_policy: Policy for handling queue overflow.
        """
        self._mode = mode
        self._cap = cap
        self._debounce_ms = debounce_ms
        self._drop_policy = drop_policy

        self._channels: dict[str, ChannelQueue] = {}
        self._default_channel = ChannelQueue()
        self._lock = asyncio.Lock()
        self._new_item_event = asyncio.Event()
        self._draining = False

    @property
    def mode(self) -> QueueMode:
        """Get the current queue mode."""
        return self._mode

    @mode.setter
    def mode(self, value: QueueMode) -> None:
        """Set the queue mode."""
        self._mode = value

    def _get_channel_queue(self, channel: str | None) -> ChannelQueue:
        """Get the queue for a channel.

        Args:
            channel: Channel identifier or None for default.

        Returns:
            The ChannelQueue for the specified channel.
        """
        if channel is None:
            return self._default_channel
        if channel not in self._channels:
            self._channels[channel] = ChannelQueue()
        return self._channels[channel]

    def _total_count(self) -> int:
        """Get the total number of items across all channels."""
        count = len(self._default_channel.items)
        for cq in self._channels.values():
            count += len(cq.items)
        return count

    def _apply_drop_policy(self, channel_queue: ChannelQueue) -> FollowupItem | None:
        """Apply drop policy when queue is at capacity.

        Args:
            channel_queue: The channel queue to apply policy to.

        Returns:
            The dropped item, if any.
        """
        if self._total_count() < self._cap:
            return None

        if self._drop_policy == DropPolicy.OLD:
            # Drop oldest from this channel, or from any channel if empty
            if channel_queue.items:
                dropped = channel_queue.items.pop(0)
                logger.warning(f"Dropped oldest message: {dropped.message_id}")
                return dropped

            # Find oldest across all channels
            oldest_queue = None
            oldest_time = float("inf")
            for cq in [self._default_channel] + list(self._channels.values()):
                if cq.items and cq.items[0].enqueued_at < oldest_time:
                    oldest_time = cq.items[0].enqueued_at
                    oldest_queue = cq
            if oldest_queue:
                dropped = oldest_queue.items.pop(0)
                logger.warning(f"Dropped oldest message: {dropped.message_id}")
                return dropped

        elif self._drop_policy == DropPolicy.SUMMARIZE:
            # Summarize older messages in this channel
            if len(channel_queue.items) > 2:
                # Keep first and last, summarize middle
                old_items = channel_queue.items[:-1]
                last_item = channel_queue.items[-1]
                summary = self._summarize_items(old_items)
                channel_queue.items = [summary, last_item]
                logger.info(f"Summarized {len(old_items)} messages into 1")

        return None

    def _summarize_items(self, items: list[FollowupItem]) -> FollowupItem:
        """Create a summary item from multiple items.

        Args:
            items: Items to summarize.

        Returns:
            A single FollowupItem containing the summary.
        """
        prompts = [item.prompt for item in items]
        summary_prompt = f"[Summary of {len(items)} messages]:\n" + "\n---\n".join(prompts)
        return FollowupItem(
            prompt=summary_prompt,
            message_id=f"summary_{items[0].message_id}",
            enqueued_at=items[0].enqueued_at,
            channel=items[0].channel,
            metadata={"summarized_count": len(items)},
        )

    async def enqueue(self, item: FollowupItem) -> bool:
        """Enqueue a followup item.

        Args:
            item: The item to enqueue.

        Returns:
            True if the item was enqueued, False if rejected.
        """
        async with self._lock:
            if self._draining:
                logger.debug("Queue is draining, rejecting new item")
                return False

            channel_queue = self._get_channel_queue(item.channel)

            # Check capacity
            if self._total_count() >= self._cap:
                if self._drop_policy == DropPolicy.NEW:
                    logger.warning(f"Queue at capacity, rejecting: {item.message_id}")
                    return False
                self._apply_drop_policy(channel_queue)

            channel_queue.items.append(item)
            channel_queue.last_activity = time.time()
            self._new_item_event.set()

            logger.debug(
                f"Enqueued item for channel '{item.channel}', "
                f"queue size: {self._total_count()}"
            )
            return True

    async def drain(
        self,
        processor: ProcessorCallback,
        channel: str | None = None,
    ) -> int:
        """Drain the queue, processing all items.

        In COLLECT mode, items from the same channel are batched.
        In FOLLOWUP mode, items are processed one at a time.

        Args:
            processor: Async callback to process items.
            channel: Specific channel to drain, or None for all.

        Returns:
            Number of items processed.
        """
        self._draining = True
        processed = 0

        try:
            # Wait for debounce period
            await self._wait_for_debounce()

            if channel is not None:
                processed = await self._drain_channel(processor, channel)
            else:
                processed = await self._drain_all_channels(processor)

        finally:
            self._draining = False
            self._new_item_event.clear()

        return processed

    async def _wait_for_debounce(self) -> None:
        """Wait for the debounce period to allow message collection."""
        if self._debounce_ms <= 0:
            return

        deadline = time.time() + (self._debounce_ms / 1000)
        while time.time() < deadline:
            remaining = deadline - time.time()
            if remaining <= 0:
                break

            self._new_item_event.clear()
            try:
                await asyncio.wait_for(
                    self._new_item_event.wait(),
                    timeout=remaining,
                )
                # New item arrived, extend deadline
                deadline = time.time() + (self._debounce_ms / 1000)
            except asyncio.TimeoutError:
                break

    async def _drain_channel(
        self, processor: ProcessorCallback, channel: str | None
    ) -> int:
        """Drain a specific channel.

        Args:
            processor: Callback to process items.
            channel: Channel to drain.

        Returns:
            Number of items processed.
        """
        async with self._lock:
            channel_queue = self._get_channel_queue(channel)
            items = channel_queue.items.copy()
            channel_queue.items.clear()

        if not items:
            return 0

        if self._mode == QueueMode.COLLECT:
            await processor(items)
        else:
            for item in items:
                await processor([item])

        return len(items)

    async def _drain_all_channels(self, processor: ProcessorCallback) -> int:
        """Drain all channels.

        Args:
            processor: Callback to process items.

        Returns:
            Total items processed.
        """
        total = 0

        # Process default channel
        total += await self._drain_channel(processor, None)

        # Process named channels
        async with self._lock:
            channel_names = list(self._channels.keys())

        for channel_name in channel_names:
            total += await self._drain_channel(processor, channel_name)

        return total

    def peek(self, channel: str | None = None) -> list[FollowupItem]:
        """Peek at items in the queue without removing them.

        Args:
            channel: Specific channel to peek, or None for all.

        Returns:
            List of items in the queue.
        """
        if channel is not None:
            return self._get_channel_queue(channel).items.copy()

        items = self._default_channel.items.copy()
        for cq in self._channels.values():
            items.extend(cq.items)
        return sorted(items, key=lambda x: x.enqueued_at)

    def clear(self, channel: str | None = None) -> int:
        """Clear items from the queue.

        Args:
            channel: Specific channel to clear, or None for all.

        Returns:
            Number of items cleared.
        """
        if channel is not None:
            cq = self._get_channel_queue(channel)
            count = len(cq.items)
            cq.items.clear()
            return count

        count = len(self._default_channel.items)
        self._default_channel.items.clear()
        for cq in self._channels.values():
            count += len(cq.items)
            cq.items.clear()
        return count

    def size(self, channel: str | None = None) -> int:
        """Get the number of items in the queue.

        Args:
            channel: Specific channel to count, or None for all.

        Returns:
            Number of items.
        """
        if channel is not None:
            return len(self._get_channel_queue(channel).items)
        return self._total_count()

    def is_empty(self) -> bool:
        """Check if the queue is empty."""
        return self._total_count() == 0

    def get_stats(self) -> dict[str, Any]:
        """Get queue statistics.

        Returns:
            Dictionary with queue statistics.
        """
        channel_stats = {}
        for name, cq in self._channels.items():
            channel_stats[name] = {
                "count": len(cq.items),
                "last_activity": cq.last_activity,
            }

        return {
            "mode": self._mode.value,
            "total_items": self._total_count(),
            "cap": self._cap,
            "debounce_ms": self._debounce_ms,
            "drop_policy": self._drop_policy.value,
            "draining": self._draining,
            "default_channel_count": len(self._default_channel.items),
            "channels": channel_stats,
        }
