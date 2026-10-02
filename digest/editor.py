"""Pick, per section, the stories that matter to this reader.

Ranking alone (source weight + freshness) only knows what is new, not what is
relevant. This sends each section's candidate headlines to the LLM along with
the reader's interests for that section (config.SECTION_INTERESTS) and keeps
what it chooses. One request for the whole digest.

Like everything else here, it degrades: if the call fails or the answer is
unusable, each section falls back to the top of the ranking and the email
says so in its footer.
"""

import json
import logging
import re

from . import config, health
from .fetch import Article

log = logging.getLogger(__name__)

_SYSTEM = (
    "You are the editor of a personal morning news briefing. The reader gets news "
    "through this email instead of scrolling social media, so it has to surface "
    "what he would not want to miss.\n\n"
    "For each section you receive the reader's interests and a numbered list of "
    "candidate stories. Choose up to the requested number of stories per section, "
    "ordered from most to least important, judged against that section's interests.\n\n"
    "Rules:\n"
    "- Prefer concrete news (something happened, was announced, decided, released) "
    "over opinion columns, explainers, listicles, deals, horoscopes and celebrity items.\n"
    "- Never pick two stories about the same event; keep the most informative one.\n"
    "- Only use ids listed under that section.\n"
    "- The reader wants the full count per section: if fewer stories match his "
    "interests, fill the rest with the most newsworthy remaining ones of that section.\n"
    "- Exception, section \"caba\": pick only stories that are really about the City "
    "of Buenos Aires (city government, transport, services, neighborhoods, city life). "
    "A national story that merely mentions a porteño court or a former city official "
    "does not count. Returning fewer than requested here is correct.\n\n"
    "Respond with ONLY a JSON object mapping each section key to a list of ids, "
    'for example {"ai": [3, 0, 7], "tech": [12, 15]}. No prose, no markdown fences.'
)


def _format(buckets: dict[str, list[Article]]) -> tuple[str, dict[int, tuple[str, Article]]]:
    index: dict[int, tuple[str, Article]] = {}
    blocks: list[str] = []
    next_id = 0
    for key in config.SECTION_ORDER:
        pool = buckets.get(key, [])
        if not pool:
            continue
        limit = config.SECTION_LIMITS.get(key, 5)
        lines = [
            f"## Section \"{key}\" — pick up to {limit}",
            f"Reader's interests: {config.SECTION_INTERESTS.get(key, '')}",
        ]
        for article in pool:
            index[next_id] = (key, article)
            snippet = article.snippet[:160]
            lines.append(f"[{next_id}] {article.source}: {article.title}" + (f" — {snippet}" if snippet else ""))
            next_id += 1
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks), index


def _parse(raw: str) -> dict:
    text = re.sub(r"^\s*```(?:json)?|```\s*$", "", raw.strip(), flags=re.MULTILINE).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("no JSON object in the response")
    data = json.loads(text[start:end + 1])
    if not isinstance(data, dict):
        raise ValueError("response is not an object")
    return data


def truncate(buckets: dict[str, list[Article]]) -> dict[str, list[Article]]:
    """Fallback: top of the ranking, final limits."""
    return {key: items[: config.SECTION_LIMITS.get(key, 5)] for key, items in buckets.items()}


def pick(buckets: dict[str, list[Article]], llm_call) -> dict[str, list[Article]]:
    """buckets: candidates per section, already ranked. Returns final sections."""
    if not any(buckets.values()):
        return buckets
    prompt, index = _format(buckets)
    try:
        choice = _parse(llm_call(_SYSTEM, "Candidates:\n\n" + prompt))
    except Exception as exc:  # noqa: BLE001 — degrade, don't cascade
        log.warning("editor: failed (%s), falling back to ranking", exc)
        health.warn("El filtro por relevancia falló hoy: las notas se eligieron por fecha y fuente.")
        return truncate(buckets)

    out: dict[str, list[Article]] = {}
    for key, pool in buckets.items():
        limit = config.SECTION_LIMITS.get(key, 5)
        chosen: list[Article] = []
        for raw_id in choice.get(key, []) or []:
            try:
                section, article = index[int(raw_id)]
            except (KeyError, TypeError, ValueError):
                continue
            if section == key and article not in chosen:
                chosen.append(article)
            if len(chosen) == limit:
                break
        # Short answer for a section: top up from the ranking, in order. Not for
        # CABA: its pool comes from a keyword filter, and topping up would bring
        # back exactly the false positives the editor just discarded.
        for article in ([] if key == "caba" else pool):
            if len(chosen) >= limit:
                break
            if article not in chosen:
                chosen.append(article)
        out[key] = chosen
        log.info("editor: section %s -> %d stories", key, len(chosen))
    return out
