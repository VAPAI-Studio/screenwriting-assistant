# backend/app/services/vapai_service.py
"""Outbound client that pushes a completed screenplay into vapai-studio.

Transport: vapai-studio's FastMCP HTTP endpoint (MCP "Streamable HTTP",
JSON-RPC 2.0), authenticated with a shared bearer token (VAPAI_MCP_API_KEY that
matches vapai's own MCP_API_KEY). This avoids needing a per-user Supabase JWT
service-to-service — vapai resolves the owning user from its own DEFAULT_USER_ID
(or the user_id we pass to create_project).

Only screenplay ingestion is done here: create_project -> create_episode ->
create_script. The breakdown (scene/shot extraction) is intentionally NOT
triggered; the user runs it inside vapai-studio.
"""

import json
import logging
from typing import Any, Dict, Optional

import httpx

from ..config import settings
from ..exceptions import VapaiServiceException

logger = logging.getLogger(__name__)

# Pinned MCP protocol version for the initialize handshake. vapai's FastMCP
# negotiates this; keeping it explicit makes the handshake reproducible.
_MCP_PROTOCOL_VERSION = "2025-06-18"


class VapaiService:
    """Async JSON-RPC client to vapai-studio's MCP HTTP server."""

    def _require_config(self) -> None:
        # Only the URL is mandatory. The API key is optional: vapai's MCP enforces
        # a bearer token only when its own MCP_API_KEY is set (e.g. local dev runs
        # without auth). We send the Authorization header only when a key exists.
        if not settings.VAPAI_MCP_URL:
            raise VapaiServiceException(
                "integration not configured (set VAPAI_MCP_URL)",
                status_code=424,
            )

    def _parse_response(self, response: httpx.Response) -> Dict[str, Any]:
        """Parse a Streamable-HTTP MCP response, which may be a plain JSON body or
        an SSE (text/event-stream) frame. Returns the decoded JSON-RPC message and
        raises VapaiServiceException on a JSON-RPC error or unparseable body."""
        if response.status_code >= 400:
            raise VapaiServiceException(
                f"MCP HTTP {response.status_code}: {response.text[:300]}"
            )

        content_type = response.headers.get("content-type", "")
        body = response.text
        message: Optional[Dict[str, Any]] = None

        if "text/event-stream" in content_type:
            # SSE: one or more `data: {...}` lines. Take the last data payload that
            # parses as a JSON-RPC message (the tool result).
            for line in body.splitlines():
                line = line.strip()
                if not line.startswith("data:"):
                    continue
                payload = line[len("data:"):].strip()
                if not payload:
                    continue
                try:
                    message = json.loads(payload)
                except json.JSONDecodeError:
                    continue
        else:
            try:
                message = json.loads(body) if body.strip() else None
            except json.JSONDecodeError as exc:
                raise VapaiServiceException(f"invalid JSON from MCP: {exc}")

        if message is None:
            raise VapaiServiceException("empty response from MCP endpoint")
        if isinstance(message, dict) and message.get("error"):
            raise VapaiServiceException(f"MCP error: {message['error']}")
        return message

    def _extract_tool_result(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Pull the tool's returned object out of a tools/call result. FastMCP puts
        it in result.structuredContent, or as a JSON string in result.content[0].text."""
        result = message.get("result") or {}
        structured = result.get("structuredContent")
        if isinstance(structured, dict):
            # FastMCP sometimes wraps a bare return under {"result": ...}.
            if set(structured.keys()) == {"result"} and isinstance(structured["result"], dict):
                return structured["result"]
            return structured

        content = result.get("content") or []
        if content and isinstance(content, list):
            text = content[0].get("text") if isinstance(content[0], dict) else None
            if text:
                try:
                    parsed = json.loads(text)
                    if isinstance(parsed, dict):
                        return parsed
                except json.JSONDecodeError:
                    pass

        raise VapaiServiceException(f"could not read tool result from: {result}")

    async def _call_tool(
        self,
        client: httpx.AsyncClient,
        session_id: Optional[str],
        request_id: int,
        name: str,
        arguments: Dict[str, Any],
    ) -> Dict[str, Any]:
        headers = {"Mcp-Session-Id": session_id} if session_id else {}
        response = await client.post(
            settings.VAPAI_MCP_URL,
            headers=headers,
            json={
                "jsonrpc": "2.0",
                "id": request_id,
                "method": "tools/call",
                "params": {"name": name, "arguments": arguments},
            },
        )
        message = self._parse_response(response)
        return self._extract_tool_result(message)

    async def _call_tool_list(
        self,
        client: httpx.AsyncClient,
        session_id: Optional[str],
        request_id: int,
        name: str,
        arguments: Dict[str, Any],
    ) -> list:
        """Like _call_tool but for tools that return a LIST (e.g. list_episodes).
        FastMCP puts the array in result.structuredContent.result, or one JSON
        object per result.content[].text."""
        headers = {"Mcp-Session-Id": session_id} if session_id else {}
        response = await client.post(
            settings.VAPAI_MCP_URL,
            headers=headers,
            json={
                "jsonrpc": "2.0",
                "id": request_id,
                "method": "tools/call",
                "params": {"name": name, "arguments": arguments},
            },
        )
        message = self._parse_response(response)
        result = message.get("result") or {}

        structured = result.get("structuredContent")
        if isinstance(structured, dict) and isinstance(structured.get("result"), list):
            return structured["result"]
        if isinstance(structured, list):
            return structured

        items = []
        for entry in result.get("content") or []:
            text = entry.get("text") if isinstance(entry, dict) else None
            if not text:
                continue
            try:
                items.append(json.loads(text))
            except json.JSONDecodeError:
                continue
        return items

    async def send_screenplay(
        self,
        *,
        title: str,
        fountain_text: str,
        existing_project_id: Optional[str] = None,
        existing_episode_id: Optional[str] = None,
        episode_number: int = 1,
    ) -> Dict[str, Any]:
        """Push a screenplay to vapai-studio, creating project/episode/script.

        If existing_project_id and existing_episode_id are provided (a re-send), the
        project and episode are reused and only a new script is created.

        Returns {vapai_project_id, vapai_episode_id, vapai_script_id, deep_link}.
        Raises VapaiServiceException (424 unconfigured, 502 downstream failure).
        """
        self._require_config()

        auth_headers = {
            "Content-Type": "application/json",
            # Streamable HTTP requires the client to accept BOTH content types.
            "Accept": "application/json, text/event-stream",
        }
        # Send the bearer only when a key is configured — vapai's MCP runs without
        # auth locally (no MCP_API_KEY), and an empty "Bearer " would 401.
        if settings.VAPAI_MCP_API_KEY:
            auth_headers["Authorization"] = f"Bearer {settings.VAPAI_MCP_API_KEY}"

        try:
            async with httpx.AsyncClient(
                timeout=settings.VAPAI_TIMEOUT_SECONDS,
                headers=auth_headers,
            ) as client:
                # 1. initialize handshake — capture the session id header.
                init_resp = await client.post(
                    settings.VAPAI_MCP_URL,
                    json={
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "initialize",
                        "params": {
                            "protocolVersion": _MCP_PROTOCOL_VERSION,
                            "capabilities": {},
                            "clientInfo": {
                                "name": "screenwriting-assistant",
                                "version": "1.0.0",
                            },
                        },
                    },
                )
                self._parse_response(init_resp)  # raises on error
                session_id = init_resp.headers.get("mcp-session-id")

                # 2. notifications/initialized (fire-and-forget notification).
                init_notify_headers = (
                    {"Mcp-Session-Id": session_id} if session_id else {}
                )
                await client.post(
                    settings.VAPAI_MCP_URL,
                    headers=init_notify_headers,
                    json={"jsonrpc": "2.0", "method": "notifications/initialized"},
                )

                # 3. Create project + episode (unless re-sending under existing ones).
                if existing_project_id and existing_episode_id:
                    vapai_project_id = existing_project_id
                    vapai_episode_id = existing_episode_id
                else:
                    project_args: Dict[str, Any] = {
                        "name": title,
                        "type": settings.VAPAI_PROJECT_TYPE,
                        "description": "Imported from screenwriting-assistant",
                    }
                    if settings.VAPAI_DEFAULT_USER_ID:
                        project_args["user_id"] = settings.VAPAI_DEFAULT_USER_ID
                    project = await self._call_tool(
                        client, session_id, 2, "create_project", project_args
                    )
                    vapai_project_id = str(project["id"])

                    # vapai auto-creates Episode 1 when a project is created, and
                    # (project_id, number) is unique — so blindly creating an episode
                    # collides. Reuse the existing episode (prefer the one matching
                    # episode_number, else the first); only create if none exist.
                    episodes = await self._call_tool_list(
                        client, session_id, 3, "list_episodes",
                        {"project_id": vapai_project_id},
                    )
                    existing = next(
                        (e for e in episodes if e.get("number") == episode_number),
                        episodes[0] if episodes else None,
                    )
                    if existing:
                        vapai_episode_id = str(existing["id"])
                    else:
                        episode = await self._call_tool(
                            client,
                            session_id,
                            4,
                            "create_episode",
                            {
                                "project_id": vapai_project_id,
                                "number": episode_number,
                                "title": title,
                            },
                        )
                        vapai_episode_id = str(episode["id"])

                # 4. Create the script with the screenplay text (Fountain).
                script = await self._call_tool(
                    client,
                    session_id,
                    4,
                    "create_script",
                    {
                        "project_id": vapai_project_id,
                        "episode_id": vapai_episode_id,
                        "content": fountain_text,
                        "title": title,
                        "source": "manual",
                    },
                )
                vapai_script_id = str(script["id"])

        except VapaiServiceException:
            raise
        except httpx.HTTPError as exc:
            logger.error("vapai-studio push failed (transport): %s", exc)
            raise VapaiServiceException(f"could not reach vapai-studio: {exc}")
        except Exception as exc:  # noqa: BLE001 — surface anything else as 502
            logger.error("vapai-studio push failed: %s", exc)
            raise VapaiServiceException(str(exc))

        deep_link: Optional[str] = None
        if settings.VAPAI_WEB_URL:
            deep_link = f"{settings.VAPAI_WEB_URL.rstrip('/')}/projects/{vapai_project_id}"

        return {
            "vapai_project_id": vapai_project_id,
            "vapai_episode_id": vapai_episode_id,
            "vapai_script_id": vapai_script_id,
            "deep_link": deep_link,
        }


vapai_service = VapaiService()
