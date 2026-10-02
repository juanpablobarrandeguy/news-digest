"""Single entry point to whatever LLM is configured.

Both digest/summarize.py and digest/tweets.py go through `call()`. Adding a
provider means adding one function here and one line to PROVIDERS — nothing
downstream changes.
"""

import logging
import re
import time

import requests

from . import config, health

log = logging.getLogger(__name__)

GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"
GEMINI_FALLBACK_MODEL = "gemini-flash-latest"  # Google's own alias, used if listing fails
GEMINI_MAX_MODELS = 3  # how many models to try before giving up for the run
_RETRY_STATUS = {429, 500, 502, 503, 504}
_STABLE_FLASH_RE = re.compile(r"^models/gemini-(\d+(?:\.\d+)*)-flash$")
_STABLE_LITE_RE = re.compile(r"^models/gemini-(\d+(?:\.\d+)*)-flash-lite$")

# Resolved once per run: candidate models, best first, and which one is in use.
# The newest Flash is often overloaded on the free tier (HTTP 503); when that
# happens the run moves to the next candidate and stays there.
_gemini_models: list[str] | None = None
_gemini_idx = 0


class LLMUnavailable(RuntimeError):
    """No provider configured, no usable key, or every model failed this run."""


def _post(url: str, **kwargs) -> requests.Response:
    """POST with retries on rate limits and server errors.

    The free tiers rate-limit per minute; a few calls in a row can trip that.
    Honors Retry-After when the server sends it, otherwise backs off 5s, 10s, 20s.
    """
    retries = max(config.LLM_RETRIES, 0)
    for attempt in range(retries + 1):
        try:
            resp = requests.post(url, timeout=config.LLM_TIMEOUT, **kwargs)
        except (requests.ConnectionError, requests.Timeout) as exc:
            if attempt == retries:
                raise
            wait = 5 * 2 ** attempt
            log.warning("llm: %s, retrying in %ss", type(exc).__name__, wait)
            time.sleep(wait)
            continue
        if resp.status_code in _RETRY_STATUS and attempt < retries:
            try:
                wait = min(int(resp.headers.get("Retry-After", "")), 60)
            except ValueError:
                wait = 5 * 2 ** attempt
            log.warning("llm: HTTP %d, retrying in %ss", resp.status_code, wait)
            time.sleep(wait)
            continue
        return resp
    return resp  # unreachable, keeps type checkers quiet


def _version_key(version: str) -> tuple[int, ...]:
    return tuple(int(p) for p in version.split("."))


def _discover_gemini_models() -> list[str]:
    """The two newest stable 'gemini-X.Y-flash' models this key can call, then the
    newest stable flash-lite (separate capacity, usually free when Flash is busy). Previews and dated variants are
    skipped on purpose: they come and go faster."""
    try:
        resp = requests.get(
            f"{GEMINI_BASE}/models",
            headers={"x-goog-api-key": config.LLM_API_KEY},
            params={"pageSize": 1000},
            timeout=30,
        )
        resp.raise_for_status()
        flash: list[tuple[tuple[int, ...], str]] = []
        lite: list[tuple[tuple[int, ...], str]] = []
        for model in resp.json().get("models", []):
            name = model.get("name", "")
            if "generateContent" not in model.get("supportedGenerationMethods", []):
                continue
            for regex, bucket in ((_STABLE_FLASH_RE, flash), (_STABLE_LITE_RE, lite)):
                match = regex.match(name)
                if match:
                    bucket.append((_version_key(match.group(1)), name.removeprefix("models/")))
        flash.sort(reverse=True)
        lite.sort(reverse=True)
        found = [n for _, n in flash[:2]] + [n for _, n in lite[:1]]
        if found:
            return found
        log.warning("llm: no stable gemini-*-flash in the model list")
    except Exception as exc:  # noqa: BLE001
        log.warning("llm: could not list Gemini models (%s)", exc)
    return [GEMINI_FALLBACK_MODEL]


def _gemini_candidates() -> list[str]:
    global _gemini_models
    if _gemini_models is None:
        found = _discover_gemini_models()
        models = ([config.LLM_MODEL] if config.LLM_MODEL else []) + [m for m in found if m != config.LLM_MODEL]
        _gemini_models = models[:GEMINI_MAX_MODELS]
        log.info("llm: Gemini candidates %s", ", ".join(_gemini_models))
    return _gemini_models


def _gemini_model_name() -> str:
    models = _gemini_candidates()
    return models[min(_gemini_idx, len(models) - 1)]


def _call_gemini(system: str, user: str) -> str:
    global _gemini_idx
    payload = {
        "system_instruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": {"temperature": 0.3, "responseMimeType": "application/json"},
    }
    headers = {"x-goog-api-key": config.LLM_API_KEY, "Content-Type": "application/json"}
    models = _gemini_candidates()

    while _gemini_idx < len(models):
        model = models[_gemini_idx]
        problem = ""
        try:
            resp = _post(f"{GEMINI_BASE}/models/{model}:generateContent", headers=headers, json=payload)
        except (requests.ConnectionError, requests.Timeout) as exc:
            problem = type(exc).__name__
        else:
            if resp.status_code == 404:
                problem = "ya no existe"
                if model == config.LLM_MODEL:
                    health.warn(f"El modelo {model} ya no existe: borrá o actualizá la variable LLM_MODEL.")
            elif resp.status_code in _RETRY_STATUS:
                problem = f"HTTP {resp.status_code}"
            else:
                resp.raise_for_status()
                parts = resp.json()["candidates"][0]["content"]["parts"]
                return "".join(p.get("text", "") for p in parts)

        _gemini_idx += 1
        if _gemini_idx < len(models):
            log.warning("llm: %s failed (%s), switching to %s", model, problem, models[_gemini_idx])
            health.warn(f"Gemini {model} no respondió ({problem}); se usó {models[_gemini_idx]}.")
        else:
            health.warn(f"Ningún modelo de Gemini respondió ({', '.join(models)}); "
                        "el mail salió sin selección ni resúmenes con IA.")

    raise LLMUnavailable("every Gemini candidate failed this run")


def _call_groq(system: str, user: str) -> str:
    resp = _post(
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
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def _call_anthropic(system: str, user: str) -> str:
    resp = _post(
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
    if config.LLM_PROVIDER == "gemini":
        return _gemini_model_name()
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
