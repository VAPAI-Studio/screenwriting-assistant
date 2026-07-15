# backend/app/services/vapai_service.py
"""Outbound client that pushes a completed screenplay into vapai-studio.

Transport: vapai-studio's FastMCP HTTP endpoint (MCP "Streamable HTTP",
JSON-RPC 2.0), authenticated with a shared bearer token (VAPAI_MCP_API_KEY that
matches vapai's own MCP_API_KEY). This avoids needing a per-user Supabase JWT
service-to-service — vapai resolves the owning user from its own DEFAULT_USER_ID
(or the user_id we pass to create_project).

Two entry points: send_screenplay (one episode) and send_series (a whole show
as a vapai type="series" project). Only ingestion is done here (project ->
episode -> script, plus the series bible); the breakdown (scene/shot extraction)
is intentionally NOT triggered — the user runs it inside vapai-studio.
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


class _Session:
    """A live MCP session over one httpx client: carries the negotiated session id
    (may be None in stateless mode) and hands out monotonically increasing
    JSON-RPC request ids so a burst of calls never collides on id."""

    def __init__(self, client: httpx.AsyncClient, session_id: Optional[str]):
        self.client = client
        self.session_id = session_id
        self._next_id = 2  # id 1 was the initialize request

    async def post(self, method: str, params: Dict[str, Any]) -> httpx.Response:
        headers = {"Mcp-Session-Id": self.session_id} if self.session_id else {}
        request_id = self._next_id
        self._next_id += 1
        return await self.client.post(
            settings.VAPAI_MCP_URL,
            headers=headers,
            json={
                "jsonrpc": "2.0",
                "id": request_id,
                "method": method,
                "params": params,
            },
        )


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

    async def _open_session(self, client: httpx.AsyncClient) -> "_Session":
        """Run the MCP initialize handshake and return a session object that
        carries the (possibly None) session id and an incrementing request-id
        counter. Shared by send_screenplay and send_series."""
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

        # notifications/initialized (fire-and-forget notification).
        notify_headers = {"Mcp-Session-Id": session_id} if session_id else {}
        await client.post(
            settings.VAPAI_MCP_URL,
            headers=notify_headers,
            json={"jsonrpc": "2.0", "method": "notifications/initialized"},
        )
        return _Session(client=client, session_id=session_id)

    async def _call_tool(
        self,
        session: "_Session",
        name: str,
        arguments: Dict[str, Any],
    ) -> Dict[str, Any]:
        response = await session.post("tools/call", {"name": name, "arguments": arguments})
        message = self._parse_response(response)
        return self._extract_tool_result(message)

    async def _call_tool_list(
        self,
        session: "_Session",
        name: str,
        arguments: Dict[str, Any],
    ) -> list:
        """Like _call_tool but for tools that return a LIST (e.g. list_episodes).
        FastMCP puts the array in result.structuredContent.result, or one JSON
        object per result.content[].text."""
        response = await session.post("tools/call", {"name": name, "arguments": arguments})
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
                session = await self._open_session(client)

                # Create project + episode (unless re-sending under existing ones).
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
                    project = await self._call_tool(session, "create_project", project_args)
                    vapai_project_id = str(project["id"])

                    # vapai auto-creates Episode 1 when a project is created, and
                    # (project_id, number) is unique — so blindly creating an episode
                    # collides. Reuse the existing episode (prefer the one matching
                    # episode_number, else the first); only create if none exist.
                    episodes = await self._call_tool_list(
                        session, "list_episodes", {"project_id": vapai_project_id},
                    )
                    existing = next(
                        (e for e in episodes if e.get("number") == episode_number),
                        episodes[0] if episodes else None,
                    )
                    if existing:
                        vapai_episode_id = str(existing["id"])
                    else:
                        episode = await self._call_tool(
                            session,
                            "create_episode",
                            {
                                "project_id": vapai_project_id,
                                "number": episode_number,
                                "title": title,
                            },
                        )
                        vapai_episode_id = str(episode["id"])

                # Create the script with the screenplay text (Fountain).
                script = await self._call_tool(
                    session,
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

    async def send_episode_within_series(
        self,
        *,
        series_title: str,
        bible_text: str,
        episode_number: int,
        episode_title: str,
        fountain_text: str,
        existing_project_id: Optional[str] = None,
        existing_episode_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Push a SINGLE episode into its series' vapai project (type="series").

        Unlike send_screenplay (which creates a standalone project per episode),
        this reuses/creates the ONE series project for the whole show, so an
        episode sent from the editor lands as episode N of the series — matching
        what "Enviar serie" builds. The series project is reused via
        existing_project_id (show.vapai_project_id); the episode is reused/created
        by number (reusing vapai's auto-created Episode 1). The bible is refreshed
        on the series project when provided.

        Returns {vapai_project_id, vapai_episode_id, vapai_script_id, deep_link}.
        Raises VapaiServiceException (424 unconfigured, 502 downstream failure).
        """
        self._require_config()

        auth_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if settings.VAPAI_MCP_API_KEY:
            auth_headers["Authorization"] = f"Bearer {settings.VAPAI_MCP_API_KEY}"

        try:
            async with httpx.AsyncClient(
                timeout=settings.VAPAI_TIMEOUT_SECONDS,
                headers=auth_headers,
            ) as client:
                session = await self._open_session(client)

                # 1. Series project (reuse on re-send, else create as type="series").
                if existing_project_id:
                    vapai_project_id = existing_project_id
                else:
                    project_args: Dict[str, Any] = {
                        "name": series_title,
                        "type": "series",
                        "description": "Imported from screenwriting-assistant",
                    }
                    if settings.VAPAI_DEFAULT_USER_ID:
                        project_args["user_id"] = settings.VAPAI_DEFAULT_USER_ID
                    project = await self._call_tool(session, "create_project", project_args)
                    vapai_project_id = str(project["id"])

                # 2. Refresh the bible on the series project when we have content.
                if bible_text.strip():
                    await self._call_tool(
                        session,
                        "update_project",
                        {"project_id": vapai_project_id, "bible": bible_text},
                    )

                # 3. Reuse/create THIS episode by number (reusing auto-created Ep 1).
                if existing_episode_id:
                    vapai_episode_id = existing_episode_id
                else:
                    episodes = await self._call_tool_list(
                        session, "list_episodes", {"project_id": vapai_project_id},
                    )
                    match = next(
                        (e for e in episodes if e.get("number") == episode_number), None
                    )
                    if match:
                        vapai_episode_id = str(match["id"])
                    else:
                        created = await self._call_tool(
                            session,
                            "create_episode",
                            {
                                "project_id": vapai_project_id,
                                "number": episode_number,
                                "title": episode_title,
                            },
                        )
                        vapai_episode_id = str(created["id"])

                # 4. Attach the script.
                script = await self._call_tool(
                    session,
                    "create_script",
                    {
                        "project_id": vapai_project_id,
                        "episode_id": vapai_episode_id,
                        "content": fountain_text,
                        "title": episode_title,
                        "source": "manual",
                    },
                )
                vapai_script_id = str(script["id"])

        except VapaiServiceException:
            raise
        except httpx.HTTPError as exc:
            logger.error("vapai-studio episode-in-series push failed (transport): %s", exc)
            raise VapaiServiceException(f"could not reach vapai-studio: {exc}")
        except Exception as exc:  # noqa: BLE001 — surface anything else as 502
            logger.error("vapai-studio episode-in-series push failed: %s", exc)
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

    async def send_series(
        self,
        *,
        series_title: str,
        bible_text: str,
        episodes: list,
        existing_project_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Push a whole series to vapai-studio as one project (type="series").

        episodes: list of dicts with keys:
          - episode_number: int
          - title: str
          - fountain_text: str  (may be empty)
          - vapai_episode_id: str | None  (set on re-send)

        Creates/reuses the series project (+ its bible), then for each episode
        reuses or creates the matching vapai episode (by number, reusing the
        auto-created Episode 1) and attaches a script when the screenplay is
        non-empty. All done over a SINGLE MCP connection.

        Returns {vapai_project_id, deep_link, episodes:[{episode_number,
        vapai_episode_id, vapai_script_id|None, screenplay_empty}]}.
        Raises VapaiServiceException (424 unconfigured, 502 downstream failure).
        """
        self._require_config()

        auth_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if settings.VAPAI_MCP_API_KEY:
            auth_headers["Authorization"] = f"Bearer {settings.VAPAI_MCP_API_KEY}"

        results: list = []
        try:
            async with httpx.AsyncClient(
                timeout=settings.VAPAI_TIMEOUT_SECONDS,
                headers=auth_headers,
            ) as client:
                session = await self._open_session(client)

                # 1. Series project (reuse on re-send, else create as type="series").
                if existing_project_id:
                    vapai_project_id = existing_project_id
                else:
                    project_args: Dict[str, Any] = {
                        "name": series_title,
                        "type": "series",
                        "description": "Imported from screenwriting-assistant",
                    }
                    if settings.VAPAI_DEFAULT_USER_ID:
                        project_args["user_id"] = settings.VAPAI_DEFAULT_USER_ID
                    project = await self._call_tool(session, "create_project", project_args)
                    vapai_project_id = str(project["id"])

                # 2. Bible (series-level metadata) — only when we have content.
                if bible_text.strip():
                    await self._call_tool(
                        session,
                        "update_project",
                        {"project_id": vapai_project_id, "bible": bible_text},
                    )

                # 3. Episodes. List once, then reuse-or-create by number. The vapai
                #    project auto-creates Episode 1, so the first episode reuses it.
                vapai_episodes = await self._call_tool_list(
                    session, "list_episodes", {"project_id": vapai_project_id},
                )
                by_number = {e.get("number"): e for e in vapai_episodes}

                for ep in episodes:
                    number = ep["episode_number"]
                    ep_title = ep["title"]
                    text = ep.get("fountain_text") or ""

                    vapai_episode_id = ep.get("vapai_episode_id")
                    if not vapai_episode_id:
                        match = by_number.get(number)
                        if match:
                            vapai_episode_id = str(match["id"])
                        else:
                            created = await self._call_tool(
                                session,
                                "create_episode",
                                {
                                    "project_id": vapai_project_id,
                                    "number": number,
                                    "title": ep_title,
                                },
                            )
                            vapai_episode_id = str(created["id"])
                            by_number[number] = created

                    vapai_script_id: Optional[str] = None
                    screenplay_empty = not text.strip()
                    if not screenplay_empty:
                        script = await self._call_tool(
                            session,
                            "create_script",
                            {
                                "project_id": vapai_project_id,
                                "episode_id": vapai_episode_id,
                                "content": text,
                                "title": ep_title,
                                "source": "manual",
                            },
                        )
                        vapai_script_id = str(script["id"])

                    results.append({
                        "episode_number": number,
                        "vapai_episode_id": vapai_episode_id,
                        "vapai_script_id": vapai_script_id,
                        "screenplay_empty": screenplay_empty,
                    })

        except VapaiServiceException:
            raise
        except httpx.HTTPError as exc:
            logger.error("vapai-studio series push failed (transport): %s", exc)
            raise VapaiServiceException(f"could not reach vapai-studio: {exc}")
        except Exception as exc:  # noqa: BLE001 — surface anything else as 502
            logger.error("vapai-studio series push failed: %s", exc)
            raise VapaiServiceException(str(exc))

        deep_link: Optional[str] = None
        if settings.VAPAI_WEB_URL:
            deep_link = f"{settings.VAPAI_WEB_URL.rstrip('/')}/projects/{vapai_project_id}"

        return {
            "vapai_project_id": vapai_project_id,
            "deep_link": deep_link,
            "episodes": results,
        }


vapai_service = VapaiService()
