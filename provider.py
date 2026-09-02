"""The channel-null channel provider — PersonalClaw's teaching channel.

A **null channel** delivers nowhere. Every ``send`` is accepted, recorded, and
dropped — like ``/dev/null``, but it remembers. That makes it the smallest
honest implementation of ``ChannelTransportProvider`` from
``personalclaw.sdk.channel``, and the one to read before writing a real one:

- the lifecycle is real (``send`` before ``connect`` fails, as yours should),
- the success contract is real (``send`` returns ``True`` only when the
  message was accepted),
- the record is inspectable (an in-memory ring buffer, and optionally a JSONL
  outbox file), so tests and demos can assert what the platform sent.

Imports stay on the SDK surface (``personalclaw.sdk.*``), never a core internal.
"""

from __future__ import annotations

import json
import logging
import time
from collections import deque
from pathlib import Path
from typing import Any

from personalclaw.sdk.channel import ChannelTransportProvider, OutboundMessage

logger = logging.getLogger("channel_null")

#: How many accepted messages the in-memory record keeps (oldest dropped first).
DEFAULT_KEEP_LAST = 100


class ChannelNullProvider(ChannelTransportProvider):
    """Accepts every outbound message while connected; delivers none of them."""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config = dict(config or {})
        self._connected = False
        keep_last = int(self._config.get("keep_last", DEFAULT_KEEP_LAST))
        #: The record every test/demo inspects: newest-last accepted messages.
        self.sent: deque[OutboundMessage] = deque(maxlen=max(1, keep_last))
        # Optional durable outbox — one JSON object per accepted message.
        raw_path = str(self._config.get("outbox_path", "") or "").strip()
        self._outbox_path = Path(raw_path).expanduser() if raw_path else None

    # ── Identity ──────────────────────────────────────────────────────────

    @property
    def name(self) -> str:
        return "channel-null"

    @property
    def display_name(self) -> str:
        return "Null Channel"

    # ── Lifecycle ─────────────────────────────────────────────────────────

    async def connect(self) -> bool:
        """A null transport has nothing to dial, so connecting always succeeds —
        but the state is tracked for real, because the send gate below uses it."""
        self._connected = True
        return True

    async def disconnect(self) -> None:
        self._connected = False

    @property
    def connected(self) -> bool:
        return self._connected

    # ── Outbound ──────────────────────────────────────────────────────────

    async def send(self, message: OutboundMessage) -> bool:
        """Record the message and report success — or refuse when disconnected.

        The refusal is the teaching point: ``True`` from ``send`` means "the
        external system accepted this", so a transport must never return it
        while it has no connection to accept anything with.
        """
        if not self._connected:
            logger.warning("channel-null: send refused — not connected")
            return False
        self.sent.append(message)
        if self._outbox_path is not None:
            self._append_outbox(message)
        logger.info("channel-null: swallowed message to %s", message.channel_id)
        return True

    def _append_outbox(self, message: OutboundMessage) -> None:
        """Best-effort JSONL sink — an unwritable outbox never fails a send
        (the in-memory record above already accepted the message)."""
        row = {
            "ts": time.time(),
            "channel_id": message.channel_id,
            "thread_id": message.thread_id,
            "sender": message.sender,
            "text": message.text,
        }
        try:
            self._outbox_path.parent.mkdir(parents=True, exist_ok=True)
            with self._outbox_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        except OSError as exc:
            logger.warning("channel-null: outbox write failed: %s", exc)


def create_provider(config: dict[str, Any] | None = None) -> ChannelNullProvider:
    """Manifest factory — core calls this with this app's saved settings."""
    return ChannelNullProvider(config)
