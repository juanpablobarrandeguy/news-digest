"""Single entry point to whatever LLM is configured.

Both digest/summarize.py and digest/tweets.py go through `call()`. Adding a
provider means adding one function here and one line to PROVIDERS — nothing
downstream changes.
"""

import logging

import requests

from . import config

log = logging.getLogger(__name__)


class LLMUnavailable(RuntimeError):
    """No provider configured, or no usable key."""


def _call_gemini(system: str, user: str) -> str:
    model = model_name()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    resp = requests.post(
        url,
        headers={"x-goog-api-key": config.LLM_API_KEY, "Content-Type": "application/json"},
        json={
            "system_instruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {"temperature": 0.3, "responseMimeType": "application/json"},
        },
        timeout=config.LLM_TIMEOUT,
    )
    resp.raise_for_status()
    parts = resp.json()["candidates"][0]["content"]["parts"]
    return "".join(p.get("text", "") for p in parts)


def _call_groq(system: str, user: str) -> str:
    resp = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {config.LLM_API_KEY}"},
        json={
            "model": model_name(),
            "temperature": 0.3,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        },
        timeout=config.LLM_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def _call_anthropic(system: str, user: str) -> str:
    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": config.LLM_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": model_name(),
            "max_tokens": 4000,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        },
        timeout=config.LLM_TIMEOUT,
    )
    resp.raise_for_status()
    blocks = resp.json()["content"]
    return "".join(b.get("text", "") for b in blocks if b.get("type") == "text")


PROVIDERS = {
    "gemini": _call_gemini,
    "groq": _call_groq,
    "anthropic": _call_anthropic,
}


def model_name() -> str:
    return config.LLM_MODEL or config.PROVIDER_DEFAULT_MODEL.get(config.LLM_PROVIDER, "")


def is_enabled() -> bool:
    return (
        config.LLM_PROVIDER in PROVIDERS
        and bool(config.LLM_API_KEY)
        and config.LLM_PROVIDER != "none"
    )


def call(system: str, user: str) -> str:
    """Raise LLMUnavailable if unconfigured; let real API errors propagate."""
    if not is_enabled():
        raise LLMUnavailable(f"provider={config.LLM_PROVIDER!r}, key={'set' if config.LLM_API_KEY else 'missing'}")
    return PROVIDERS[config.LLM_PROVIDER](system, user)
