# MCP Client Setup — Screenwriting Assistant (v8.0)

The MCP server is mounted in-process on the FastAPI app over **Streamable HTTP**.

- **Endpoint (local):** `http://localhost:8001/mcp/` — note the **trailing slash** (a POST to `/mcp` without it 307-redirects, which some clients won't follow).
- **Auth:** an existing v5.0 API key as a **static bearer**. Create one at `/settings/api-keys`, then send it as `Authorization: Bearer sa_<your-key>`. No OAuth.
- A valid, non-expired key grants **all** tools; everything is scoped to that key's owner.

## Backend-verified (automated, no GUI)

The transport + auth foundation is proven by `backend/app/tests/test_mcp_foundation.py`, which drives the mounted `/mcp` with the official `mcp` SDK client over an ASGI transport and asserts:
- `initialize` + `tools/list` round-trip over Streamable HTTP,
- a valid `sa_<key>` static bearer authenticates and `whoami` returns the key's owner,
- a missing bearer is rejected,
- `request_count` on the key increments via the MCP path.

## Claude Code (CLI) — verified path

```bash
claude mcp add --transport http screenwriting http://localhost:8001/mcp/ \
  --header "Authorization: Bearer sa_<your-key>"
```

Then in a Claude Code session, the `ping` and `whoami` tools should be listed; calling `whoami` should return your user.

## Claude Desktop

Add a remote MCP server in Desktop's config pointing at `http://localhost:8001/mcp/` with an `Authorization: Bearer sa_<your-key>` header. (Use the CLI/desktop config form — the claude.ai **web** connector is OAuth-only and is out of scope for v8.0.)

## Hermes

Configure Hermes to connect to `http://localhost:8001/mcp/` with the same static `Authorization: Bearer` header. **Hermes static-header support is unverified** — if Hermes cannot send a static Authorization header, v8.0 still ships for the Claude clients and Hermes support (an OAuth shim or an `mcp-remote` proxy) moves to v8.1. This is not a milestone blocker (MCPF-05).

## Pending USER verification (GUI clients)

The following require a human at the keyboard and are **deferred to the user** (could not be run during autonomous execution):

- [ ] Connect **Claude Code** via the `claude mcp add` command above; confirm `whoami` returns your user.
- [ ] Connect **Claude Desktop**; confirm tools list + a `whoami` call.
- [ ] Connect **Hermes**; confirm whether it accepts the static Authorization header (the go/no-go for native Hermes support vs. deferring to v8.1).

## Notes / configuration

- **DNS-rebinding protection** is OFF by default (internal, key-gated server). To enable host-allowlisting, set `MCP_DNS_REBINDING_PROTECTION=true` and configure allowed hosts.
- In Docker, the backend host port is `8001` (mapped to container `8000`); inside the container network the app is on `8000`.
