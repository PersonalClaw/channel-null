# Null Channel

The teaching channel: a PersonalClaw **channel** app that accepts every outbound
message and delivers none of them — `/dev/null`, but it remembers. Read this one
before writing a real channel; fork it to start yours.

It implements `ChannelTransportProvider` from `personalclaw.sdk.channel` in
~100 lines, and every line is there to demonstrate a rule real transports must
follow:

| Teaching point | Where |
| --- | --- |
| `send` returns `True` only when the message was **accepted** — never while disconnected | `send()` gate |
| Lifecycle state is real: `connect` / `disconnect` / `connected` agree with each other | `connect()` / `disconnect()` |
| What was sent is **inspectable**: an in-memory ring buffer (`.sent`) plus an optional JSONL outbox | `sent` deque, `_append_outbox()` |
| A best-effort sink never fails the accept | `_append_outbox()` swallows `OSError` |
| Imports stay on `personalclaw.sdk.*` — never a core internal | top of `provider.py` |

## Settings

| Key | Default | Meaning |
| --- | --- | --- |
| `keep_last` | `100` | How many accepted messages the in-memory record keeps |
| `outbox_path` | *(unset)* | When set, each accepted message is appended to this JSONL file |

## What it's for

- **Demos and tests**: point the platform at a channel that can't leak anything,
  then assert on `.sent` or the outbox file.
- **A fork-and-go starting point**: replace `send()`'s body with your API call,
  make `connect()` dial something real, and you have a channel.
- **The conformance baseline**: the smallest provider that honestly satisfies
  the transport contract.

## Run the tests

```bash
pytest .
```

No network, no credentials, no gateway.

## Install it

From the dashboard: **Store → Add source**, point it at this repo's git URL (or
a local clone), then install and enable it. The gateway resolves the provider
through `app.json` → `provider:create_provider`.

## License

MIT
