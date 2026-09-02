"""Contract + behaviour tests for the channel-null channel provider.

Contract: personalclaw.sdk.channel:ChannelTransportProvider

These run with no network, no credentials and no gateway. The contract half
asserts the provider SHAPE core depends on; the behaviour half asserts the
teaching points this exemplar exists to demonstrate — the honest lifecycle,
the send success contract, and the inspectable record.
"""

from __future__ import annotations

import asyncio
import json

from personalclaw.sdk.channel import OutboundMessage
from provider import DEFAULT_KEEP_LAST, ChannelNullProvider, create_provider

CONTRACT_METHODS = ("connect", "disconnect", "display_name", "name", "send")


def _msg(text: str = "hello", channel: str = "demo") -> OutboundMessage:
    return OutboundMessage(channel_id=channel, text=text)


# ── Contract shape (scaffold-generated) ──────────────────────────────────


def test_factory_returns_the_provider() -> None:
    assert isinstance(create_provider({}), ChannelNullProvider)


def test_factory_accepts_no_config() -> None:
    assert isinstance(create_provider(None), ChannelNullProvider)


def test_nothing_abstract_is_left() -> None:
    """An unimplemented abstract method makes the provider uninstantiable."""
    assert not getattr(ChannelNullProvider, "__abstractmethods__", frozenset())


def test_registers_under_the_app_name() -> None:
    """Every per-type registry keys a provider by `.name`."""
    assert create_provider({}).name == "channel-null"


def test_declares_its_display_name() -> None:
    assert create_provider({}).display_name == "Null Channel"


def test_every_contract_method_is_declared_on_the_stub() -> None:
    """Inherited-but-unimplemented is the drift this catches."""
    for name in CONTRACT_METHODS:
        assert name in vars(ChannelNullProvider), f"{name} is not implemented"


# ── Behaviour: the teaching points ────────────────────────────────────────


def test_send_before_connect_is_refused() -> None:
    """True from send means 'accepted' — a disconnected transport must not say it."""
    p = create_provider({})
    assert asyncio.run(p.send(_msg())) is False
    assert not p.sent


def test_lifecycle_gates_send() -> None:
    async def scenario() -> None:
        p = create_provider({})
        assert await p.connect() is True
        assert p.connected is True
        assert await p.send(_msg("one")) is True
        await p.disconnect()
        assert p.connected is False
        assert await p.send(_msg("two")) is False

    asyncio.run(scenario())
    # Only the connected-time send was recorded.


def test_accepted_messages_are_recorded_in_order() -> None:
    async def scenario() -> ChannelNullProvider:
        p = create_provider({})
        await p.connect()
        await p.send(_msg("first"))
        await p.send(_msg("second"))
        return p

    p = asyncio.run(scenario())
    assert [m.text for m in p.sent] == ["first", "second"]


def test_keep_last_bounds_the_record() -> None:
    async def scenario() -> ChannelNullProvider:
        p = create_provider({"keep_last": 2})
        await p.connect()
        for i in range(4):
            await p.send(_msg(f"m{i}"))
        return p

    p = asyncio.run(scenario())
    assert [m.text for m in p.sent] == ["m2", "m3"]


def test_default_record_bound() -> None:
    assert create_provider({}).sent.maxlen == DEFAULT_KEEP_LAST


def test_outbox_jsonl_written_when_configured(tmp_path) -> None:
    outbox = tmp_path / "sub" / "outbox.jsonl"

    async def scenario() -> None:
        p = create_provider({"outbox_path": str(outbox)})
        await p.connect()
        await p.send(_msg("logged", channel="c1"))

    asyncio.run(scenario())
    rows = [json.loads(line) for line in outbox.read_text().splitlines()]
    assert len(rows) == 1
    assert rows[0]["channel_id"] == "c1"
    assert rows[0]["text"] == "logged"


def test_unwritable_outbox_never_fails_the_send(tmp_path) -> None:
    """The in-memory record is the accept; the outbox is best-effort."""
    blocker = tmp_path / "not-a-dir"
    blocker.write_text("file, not dir")

    async def scenario() -> bool:
        p = create_provider({"outbox_path": str(blocker / "outbox.jsonl")})
        await p.connect()
        return await p.send(_msg("still ok"))

    assert asyncio.run(scenario()) is True
