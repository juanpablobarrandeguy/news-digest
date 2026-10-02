"""Turn raw headlines + snippets into one clean paragraph per story.

Providers are pluggable. The model never emits URLs — it returns an id, and we
stitch the real link back on afterwards. That kills hallucinated links dead.

If the LLM fails for any reason we fall back to the RSS snippet, so the email
always goes out.
"""

import json
import logging
import re

from . import config, health, llm
from .fetch import Article

log = logging.getLogger(__name__)

SYSTEM_PROMPT_TEMPLATE = (
    "You are a news editor writing a concise morning briefing for a technical "
    "reader. For each numbered article you receive, write one self-contained "
    "paragraph of 2 to 4 sentences explaining what happened and why it matters. "
    "Be factual and neutral. Do not use hype, marketing language, or filler "
    "openers. Do not include URLs, links, or citations. Do not editorialize. "
    "You may lightly rewrite the headline so it is clear on its own, but keep it "
    "under 90 characters.\n\n"
    "Write both the headline and the paragraph in {language}, regardless of the "
    "language of the source material.\n\n"
    "When outlets disagree on framing, describe what happened rather than "
    "adopting any single outlet's characterization of it.\n\n"
    "Respond with ONLY a JSON array, no prose and no markdown fences. Each "
    'element must be: {{"id": <int>, "title": "<headline>", "paragraph": "<text>"}}. '
    "Include exactly one element per article you were given."
)

_FENCE_RE = re.compile(r"^\s*```(?:json)?|```\s*$", re.MULTILINE)


def _build_user_prompt(batch: list[tuple[int, Article]]) -> str:
    lines = []
    for idx, article in batch:
        lines.append(f"[{idx}] SOURCE: {article.source}")
        lines.append(f"[{idx}] HEADLINE: {article.title}")
        if article.snippet:
            lines.append(f"[{idx}] EXCERPT: {article.snippet}")
        lines.append("")
    return "Articles:\n\n" + "\n".join(lines)


def _strip_fences(text: str) -> str:
    text = _FENCE_RE.sub("", text).strip()
    start, end = text.find("["), text.rfind("]")
    if start != -1 and end != -1 and end > start:
        text = text[start : end + 1]
    return text


def _summarize_batch(batch: list[tuple[int, Article]], language: str) -> dict[int, dict]:
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(language=language)
    raw = llm.call(system_prompt, _build_user_prompt(batch))
    parsed = json.loads(_strip_fences(raw))
    out: dict[int, dict] = {}
    for item in parsed:
        try:
            out[int(item["id"])] = {
                "title": str(item.get("title", "")).strip(),
                "paragraph": str(item.get("paragraph", "")).strip(),
            }
        except (KeyError, TypeError, ValueError):
            continue
    return out


def _fallback(article: Article) -> str:
    """No LLM, or the LLM misbehaved: use the feed's own description."""
    if article.snippet:
        return article.snippet
    return f"Posted by {article.source}. Follow the link for the full story."


def summarize(buckets: dict[str, list[Article]]) -> dict[str, list[Article]]:
    """Fill in .paragraph on every article, mutating in place."""
    flat: list[Article] = [a for items in buckets.values() for a in items]
    if not flat:
        return buckets

    if not llm.is_enabled():
        log.info("no LLM configured (%s) — using feed snippets", config.LLM_PROVIDER)
        for article in flat:
            article.paragraph = _fallback(article)
        return buckets

    indexed = list(enumerate(flat))
    results: dict[int, dict] = {}
    size = max(config.LLM_BATCH_SIZE, 1)

    # One prompt per output language: a batch mixing English tech news with
    # Spanish national news would have to be told two things at once.
    by_language: dict[str, list[tuple[int, Article]]] = {}
    for pair in indexed:
        language = config.SECTION_LANGUAGE.get(pair[1].category, "English")
        by_language.setdefault(language, []).append(pair)

    for language, group in by_language.items():
        for start in range(0, len(group), size):
            batch = group[start : start + size]
            try:
                got = _summarize_batch(batch, language)
                results.update(got)
                log.info("summarized %d/%d items in %s via %s", len(got), len(batch), language, config.LLM_PROVIDER)
                if not got:
                    health.warn("El resumen con IA volvió vacío para algunas notas; van con el texto del feed.")
            except Exception as exc:  # noqa: BLE001
                log.warning("summarization failed (%s, offset %d): %s", language, start, exc)
                health.warn(f"Falló el resumen con IA de algunas notas ({type(exc).__name__}); "
                            "van con el texto del feed.")

    for idx, article in indexed:
        result = results.get(idx)
        if result and result.get("paragraph"):
            article.paragraph = result["paragraph"]
            if result.get("title"):
                article.title = result["title"]
        else:
            article.paragraph = _fallback(article)

    return buckets
