"""v8.0 MCP server module.

Exposes the app's capabilities as MCP tools over Streamable HTTP, mounted
in-process on the existing FastAPI app at /mcp, authenticated by the v5.0
sa_<key> API-key gateway.
"""
