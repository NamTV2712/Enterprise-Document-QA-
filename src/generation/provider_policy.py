"""Shared provider-key policy helpers.

The evaluation and serving paths must agree about which credentials are
eligible for a provider call.  This module keeps that decision in one place
and deliberately never logs or serializes the secret itself.
"""

from __future__ import annotations

from typing import Any

GROQ_KEY_POLICIES = frozenset({"pool", "key5_only"})


def normalize_groq_key_policy(policy: str | None) -> str:
    value = (policy or "pool").strip().lower()
    if value not in GROQ_KEY_POLICIES:
        allowed = ", ".join(sorted(GROQ_KEY_POLICIES))
        raise ValueError(f"GROQ_KEY_POLICY must be one of: {allowed}")
    return value


def configured_groq_keys(settings: Any, *, policy: str | None = None) -> list[str]:
    """Return eligible Groq keys in deterministic order for a settings object."""
    effective = normalize_groq_key_policy(
        policy if policy is not None else getattr(settings, "groq_key_policy", "pool")
    )
    if effective == "key5_only":
        key = getattr(settings, "groq_api_key5", "")
        if not key:
            raise ValueError("GROQ_KEY_POLICY=key5_only requires GROQ_API_KEY5")
        return [key]

    return list(
        dict.fromkeys(
            key
            for key in (
                getattr(settings, "groq_api_key", ""),
                getattr(settings, "groq_api_key2", ""),
                getattr(settings, "groq_api_key3", ""),
                getattr(settings, "groq_api_key4", ""),
                getattr(settings, "groq_api_key5", ""),
            )
            if key
        )
    )


def validate_explicit_keys(
    requested_keys: list[str],
    *,
    settings: Any,
    policy: str,
) -> list[str]:
    """Validate caller-supplied keys without exposing their values.

    Under ``key5_only`` a caller may pass the already-resolved single key5
    value.  Passing a pool is rejected so a future call cannot silently rotate
    to another credential.
    """
    selected = list(dict.fromkeys(key for key in requested_keys if key))
    if policy != "key5_only":
        return selected
    if len(selected) > 1:
        raise ValueError("GROQ_KEY_POLICY=key5_only forbids a multi-key client pool")
    configured_key5 = getattr(settings, "groq_api_key5", "")
    if configured_key5 and selected and selected[0] != configured_key5:
        raise ValueError("GROQ_KEY_POLICY=key5_only permits only GROQ_API_KEY5")
    if not selected:
        if not configured_key5:
            raise ValueError("GROQ_KEY_POLICY=key5_only requires GROQ_API_KEY5")
        selected = [configured_key5]
    return selected


def key_alias(index: int, *, policy: str, pool_size: int) -> str:
    """Return safe metadata for a provider key without leaking credentials."""
    if policy == "key5_only":
        return "key5"
    return f"key-{index + 1}" if pool_size else "key-unknown"
