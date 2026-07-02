# backend/app/services/ai_provider.py

"""
Unified AI provider wrapper. Supports OpenAI and Anthropic.
All chat services use this instead of calling APIs directly.
"""

import logging
from typing import Any, AsyncGenerator, Dict, List, Optional, Type, TypeVar, Union

from pydantic import BaseModel

from ..config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

# A `system` value can be either a plain string (legacy) or a list of Anthropic
# content blocks (used for prompt caching — cache_control on the last block).
SystemValue = Union[str, List[Dict[str, Any]]]

# Lazy-init clients so missing keys don't crash on import
_openai_client = None
_anthropic_client = None

# Model families that require the modern request surface: no sampling params
# (temperature/top_p/top_k → 400), adaptive-only thinking, and output_config.effort.
# Prefix match against the configured Anthropic model id.
_MODERN_ANTHROPIC_PREFIXES = (
    "claude-opus-4-7",
    "claude-opus-4-8",
    "claude-sonnet-5",
    "claude-fable-5",
    "claude-mythos-5",
)


def _is_modern_anthropic(model: str) -> bool:
    """True when the Anthropic model rejects temperature and uses adaptive
    thinking + output_config.effort (Opus 4.7/4.8, Sonnet 5, Fable 5, Mythos 5)."""
    return any(model.startswith(p) for p in _MODERN_ANTHROPIC_PREFIXES)


def _get_openai_client():
    global _openai_client
    if _openai_client is None:
        from openai import AsyncOpenAI
        _openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    return _openai_client


def _get_anthropic_client():
    global _anthropic_client
    if _anthropic_client is None:
        from anthropic import AsyncAnthropic
        _anthropic_client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
    return _anthropic_client


async def chat_completion(
    messages: List[Dict[str, Any]],
    temperature: float = 0.7,
    max_tokens: int = 2000,
    json_mode: bool = False,
    provider: Optional[str] = None,
    thinking: bool = False,
    effort: Optional[str] = None,
    cache_system: bool = False,
) -> str:
    """
    Unified chat completion. Returns the text content of the response.

    Args:
        messages: List of {"role": "system"|"user"|"assistant", "content": "..."}.
            A "system" message's content may be a string, or a list of Anthropic
            content blocks (dicts) to enable fine-grained prompt caching.
        temperature: Sampling temperature. Ignored on modern Anthropic models
            (Opus 4.7/4.8, Sonnet 5, Fable 5, Mythos 5), which reject it.
        max_tokens: Max tokens in response
        json_mode: If True, request JSON output
        provider: Override the default AI_PROVIDER setting
        thinking: If True, enable adaptive thinking (modern Anthropic only)
        effort: output_config effort — "low"|"medium"|"high"|"max" (modern
            Anthropic only). Defaults to the model default when None.
        cache_system: If True, mark the (last) system block with cache_control
            so the shared prefix is cached across calls (Anthropic only).
    """
    provider = provider or settings.AI_PROVIDER

    if provider == "anthropic":
        return await _anthropic_completion(
            messages, temperature, max_tokens, json_mode, thinking, effort, cache_system
        )
    else:
        return await _openai_completion(messages, temperature, max_tokens, json_mode)


async def _openai_completion(
    messages: List[Dict[str, Any]],
    temperature: float,
    max_tokens: int,
    json_mode: bool,
) -> str:
    client = _get_openai_client()
    kwargs = {
        "model": settings.OPENAI_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    response = await client.chat.completions.create(**kwargs)
    return response.choices[0].message.content


def _extract_system(messages: List[Dict[str, Any]]):
    """Split Anthropic system content from chat turns.

    Returns (system_value, chat_messages) where system_value is either a string
    (all system contents were strings, concatenated) or a list of content blocks
    (if any system content was already a list of blocks — caching path). Also
    ensures the chat turns start with a user message.
    """
    system_str_parts: List[str] = []
    system_blocks: List[Dict[str, Any]] = []
    any_blocks = False
    chat_messages: List[Dict[str, Any]] = []

    for msg in messages:
        if msg["role"] == "system":
            content = msg["content"]
            if isinstance(content, list):
                any_blocks = True
                system_blocks.extend(content)
            else:
                system_str_parts.append(content)
                system_blocks.append({"type": "text", "text": content})
        else:
            chat_messages.append({"role": msg["role"], "content": msg["content"]})

    if not chat_messages or chat_messages[0]["role"] != "user":
        chat_messages.insert(0, {"role": "user", "content": "Begin."})

    system_value: SystemValue = system_blocks if any_blocks else "".join(system_str_parts)
    return system_value, chat_messages


def _append_system_text(system_value: SystemValue, extra: str) -> SystemValue:
    """Append a plain-text instruction to a system value of either shape."""
    if isinstance(system_value, list):
        return system_value + [{"type": "text", "text": extra}]
    return (system_value or "") + extra


def _apply_system_cache(system_value: SystemValue) -> SystemValue:
    """Mark the last system block with cache_control so the shared prefix is
    cached. Promotes a plain string to a single-block list if needed."""
    if isinstance(system_value, str):
        if not system_value:
            return system_value
        system_value = [{"type": "text", "text": system_value}]
    if system_value:
        # Copy the last block so we don't mutate a caller-owned dict.
        last = dict(system_value[-1])
        last["cache_control"] = {"type": "ephemeral"}
        system_value = system_value[:-1] + [last]
    return system_value


def _log_cache_usage(response, where: str) -> None:
    """Log Anthropic cache read/write token counts when present (best effort)."""
    try:
        usage = getattr(response, "usage", None)
        if usage is None:
            return
        read = getattr(usage, "cache_read_input_tokens", 0) or 0
        created = getattr(usage, "cache_creation_input_tokens", 0) or 0
        if read or created:
            logger.info(f"[{where}] prompt cache: read={read} created={created}")
    except Exception:
        pass


def _first_text_block(response) -> str:
    """Return the text of the first `text` content block in an Anthropic
    response. With adaptive thinking on, response.content[0] may be a thinking
    block, so we can't blindly index [0]."""
    for block in response.content:
        if getattr(block, "type", None) == "text":
            return block.text
    # Fallback: no text block found (e.g. thinking-only / refusal) — return "".
    return ""


async def _anthropic_completion(
    messages: List[Dict[str, Any]],
    temperature: float,
    max_tokens: int,
    json_mode: bool,
    thinking: bool = False,
    effort: Optional[str] = None,
    cache_system: bool = False,
) -> str:
    client = _get_anthropic_client()
    model = settings.ANTHROPIC_MODEL
    modern = _is_modern_anthropic(model)

    system_value, chat_messages = _extract_system(messages)

    # For JSON mode, append instruction to system prompt
    if json_mode:
        system_value = _append_system_text(
            system_value,
            "\n\nIMPORTANT: You MUST return ONLY valid JSON. No markdown, no code fences, no extra text.",
        )

    if cache_system:
        system_value = _apply_system_cache(system_value)

    kwargs: Dict[str, Any] = {
        "model": model,
        "messages": chat_messages,
        "max_tokens": max_tokens,
    }
    # Modern models reject temperature/top_p/top_k with a 400. Only send it on
    # legacy models.
    if not modern:
        kwargs["temperature"] = temperature
    if thinking and modern:
        kwargs["thinking"] = {"type": "adaptive"}
    if effort and modern:
        kwargs["output_config"] = {"effort": effort}
    if system_value:
        kwargs["system"] = system_value

    response = await client.messages.create(**kwargs)
    if cache_system:
        _log_cache_usage(response, where="chat_completion")
    text = _first_text_block(response)

    # Strip markdown code fences if present (LLM sometimes wraps JSON)
    if json_mode and text.startswith("```"):
        lines = text.split("\n")
        # Remove first line (```json) and last line (```)
        if lines[-1].strip() == "```":
            lines = lines[1:-1]
        elif lines[0].startswith("```"):
            lines = lines[1:]
        text = "\n".join(lines)

    return text


async def chat_completion_structured(
    messages: List[Dict[str, str]],
    response_model: Type[T],
    temperature: float = 0.1,
    max_tokens: int = 4000,
    provider: Optional[str] = None,
) -> T:
    """
    Structured output completion. Returns a validated Pydantic model instance.

    Uses provider-native structured output support to guarantee schema-compliant
    JSON responses. Falls back to JSON parsing if structured output methods
    are unavailable.

    Args:
        messages: List of {"role": "system"|"user"|"assistant", "content": "..."}
        response_model: Pydantic model class defining the response schema
        temperature: Sampling temperature (default 0.1 for deterministic extraction)
        max_tokens: Max tokens in response
        provider: Override the default AI_PROVIDER setting
    """
    provider = provider or settings.AI_PROVIDER

    if provider == "anthropic":
        return await _anthropic_structured(messages, response_model, temperature, max_tokens)
    else:
        return await _openai_structured(messages, response_model, temperature, max_tokens)


async def _openai_structured(
    messages: List[Dict[str, str]],
    response_model: Type[T],
    temperature: float,
    max_tokens: int,
) -> T:
    """OpenAI structured output using client.beta.chat.completions.parse()."""
    client = _get_openai_client()
    kwargs = {
        "model": settings.OPENAI_MODEL,
        "messages": messages,
        "response_format": response_model,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    try:
        # Try the stable API first (available in newer SDK versions)
        completion = await client.chat.completions.parse(**kwargs)
        return completion.choices[0].message.parsed
    except AttributeError:
        # Fall back to beta API for older SDK versions
        completion = await client.beta.chat.completions.parse(**kwargs)
        return completion.choices[0].message.parsed


async def _anthropic_structured(
    messages: List[Dict[str, str]],
    response_model: Type[T],
    temperature: float,
    max_tokens: int,
) -> T:
    """Anthropic structured output using JSON schema in response_format."""
    client = _get_anthropic_client()

    # Separate system prompt from messages (same pattern as _anthropic_completion)
    system_prompt = None
    chat_messages = []
    for msg in messages:
        if msg["role"] == "system":
            system_prompt = (system_prompt or "") + msg["content"]
        else:
            chat_messages.append({"role": msg["role"], "content": msg["content"]})

    # Ensure messages start with user role (same pattern)
    if not chat_messages or chat_messages[0]["role"] != "user":
        chat_messages.insert(0, {"role": "user", "content": "Begin."})

    # Append JSON schema instruction to system prompt (Anthropic has no response_format)
    import json
    json_schema = response_model.model_json_schema()
    schema_instruction = (
        f"\n\nYou MUST respond with ONLY valid JSON that matches this schema exactly. "
        f"No markdown, no code fences, no extra text.\n\nSchema:\n{json.dumps(json_schema, indent=2)}"
    )
    full_system = (system_prompt or "") + schema_instruction

    model = settings.ANTHROPIC_MODEL
    kwargs = {
        "model": model,
        "messages": chat_messages,
        "max_tokens": max_tokens,
        "system": full_system,
    }
    # Modern models reject temperature with a 400; only send it on legacy models.
    if not _is_modern_anthropic(model):
        kwargs["temperature"] = temperature

    response = await client.messages.create(**kwargs)
    text = _first_text_block(response)

    # Strip markdown code fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[-1].strip() == "```":
            lines = lines[1:-1]
        elif lines[0].startswith("```"):
            lines = lines[1:]
        text = "\n".join(lines)

    return response_model.model_validate_json(text)


async def chat_completion_stream(
    messages: List[Dict[str, str]],
    temperature: float = 0.7,
    max_tokens: int = 2000,
    provider: Optional[str] = None,
) -> AsyncGenerator[str, None]:
    """Streaming chat completion. Yields text chunks as they arrive."""
    provider = provider or settings.AI_PROVIDER

    if provider == "anthropic":
        async for chunk in _anthropic_stream(messages, temperature, max_tokens):
            yield chunk
    else:
        async for chunk in _openai_stream(messages, temperature, max_tokens):
            yield chunk


async def _openai_stream(
    messages: List[Dict[str, str]],
    temperature: float,
    max_tokens: int,
) -> AsyncGenerator[str, None]:
    client = _get_openai_client()
    kwargs = {
        "model": settings.OPENAI_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": True,
    }
    response = await client.chat.completions.create(**kwargs)
    async for chunk in response:
        if chunk.choices and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content


async def _anthropic_stream(
    messages: List[Dict[str, str]],
    temperature: float,
    max_tokens: int,
) -> AsyncGenerator[str, None]:
    client = _get_anthropic_client()

    system_prompt = None
    chat_messages = []
    for msg in messages:
        if msg["role"] == "system":
            system_prompt = (system_prompt or "") + msg["content"]
        else:
            chat_messages.append({"role": msg["role"], "content": msg["content"]})

    if not chat_messages or chat_messages[0]["role"] != "user":
        chat_messages.insert(0, {"role": "user", "content": "Begin."})

    model = settings.ANTHROPIC_MODEL
    kwargs = {
        "model": model,
        "messages": chat_messages,
        "max_tokens": max_tokens,
    }
    # Modern models reject temperature with a 400; only send it on legacy models.
    if not _is_modern_anthropic(model):
        kwargs["temperature"] = temperature
    if system_prompt:
        kwargs["system"] = system_prompt

    async with client.messages.stream(**kwargs) as stream:
        async for text in stream.text_stream:
            yield text
