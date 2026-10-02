"""Pick the stories worth posting about and suggest entry points.

Shown in the email as "Noticias viralizables / trending": candidates for a
LinkedIn post, the brand's Instagram or X. This does NOT write the posts. It surfaces which of today's stories have traction
potential for your lane and what the possible angles are — you write the actual
post. On political items it gives the factual hook and names where the
disagreement sits, without taking a side.

Fails soft: any error returns [] and the digest email goes out without this
section.
"""

import json
import logging
import re
from dataclasses import dataclass, field

from . import config

log = logging.getLogger(__name__)


@dataclass
class Angle:
    title: str
    url: str
    source: str
    category: str
    score: int
    why: str
    angles: list[str] = field(default_factory=list)
    format_hint: str = ""
    ttl_hours: int = 24


_SYSTEM = (
    "You help a technical professional decide what to post about on LinkedIn, on "
    "his brand's Instagram account, or on X. You do NOT write the posts — you "
    "surface which stories have traction potential and what the possible entry "
    "points are. He has his own opinions and supplies the take himself.\n\n"
    "For each story you select, give:\n"
    "- score (0-100): likelihood this gets engagement in his lane. Be harsh. "
    "Most stories score below 50. Reserve 80+ for something genuinely live.\n"
    "- why: one sentence on what makes it timely right now, not why it's important "
    "in general.\n"
    "- angles: 2-3 distinct entry points. An angle is a framing or a question, not "
    "a finished sentence and not a hot take. Prefer angles that draw on hands-on "
    "infrastructure and cloud experience, since that is his credibility.\n"
    "- format: the best fit, one of 'post LinkedIn', 'carrusel Instagram', "
    "'reel', 'post X', 'hilo X'.\n"
    "- ttl_hours: how long this stays worth posting about.\n\n"
    "On political or contested stories: describe what happened and name what "
    "people actually disagree about. Do not supply a position, do not imply which "
    "side is correct, and do not phrase angles as advocacy. Neutral framing only — "
    "he supplies the opinion.\n\n"
    "Skip anything that is pure product marketing, a funding round with no "
    "technical substance, or so widely covered that there is nothing left to add.\n\n"
    "Write in Spanish (rioplatense, neutral register).\n\n"
    "Respond with ONLY a JSON object, no prose and no markdown fences:\n"
    '{{"picks": [{{"id": <int>, "score": <int>, "why": "...", '
    '"angles": ["...", "..."], "format": "...", "ttl_hours": <int>}}]}}'
)

_USER_TMPL = (
    "Lane: {lane}\n\n"
    "Select at most {max_angles} stories scoring {min_score} or above. "
    "If none clear the bar, return an empty picks array — that is a valid answer.\n\n"
    "Stories:\n\n{articles}"
)


def _get(obj, name: str, default=""):
    """Articles may be dataclasses here and plain dicts elsewhere."""
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _format_articles(articles: list) -> str:
    lines = []
    for idx, art in enumerate(articles):
        lines.append(f"[{idx}] ({_get(art, 'category')}) {_get(art, 'title')}")
        body = _get(art, "paragraph") or _get(art, "snippet")
        if body:
            lines.append(f"     {body[:400]}")
        lines.append("")
    return "\n".join(lines)


def _parse(raw: str) -> list[dict]:
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip()).strip()
    try:
        return json.loads(text).get("picks", [])
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0)).get("picks", [])
        except json.JSONDecodeError:
            pass
    log.warning("tweets: could not parse the LLM response, skipping section")
    return []


def generate(articles: list, llm_call, *, lane: str = "", max_angles: int = 0,
             min_score: int = 0) -> list[Angle]:
    """articles: the flat deduplicated list. llm_call: callable(system, user) -> str.

    Returns [] on any failure. Never raises — the email goes out regardless.
    """
    lane = lane or config.TWEET_LANE
    max_angles = max_angles or config.TWEET_MAX_ANGLES
    min_score = min_score or config.TWEET_MIN_SCORE

    if not articles:
        return []

    try:
        raw = llm_call(
            _SYSTEM.format(),  # the template doubles its braces
            _USER_TMPL.format(
                lane=lane.strip(),
                articles=_format_articles(articles),
                max_angles=max_angles,
                min_score=min_score,
            ),
        )
    except Exception as exc:  # noqa: BLE001 — degrade, don't cascade
        log.warning("tweets: LLM call failed (%s), skipping section", exc)
        return []

    out: list[Angle] = []
    for pick in _parse(raw):
        try:
            idx = int(pick["id"])
            art = articles[idx]  # the real link is attached HERE, never by the model
        except (KeyError, TypeError, ValueError, IndexError):
            log.debug("tweets: discarding pick with invalid id: %r", pick)
            continue

        try:
            score = int(pick.get("score", 0))
        except (TypeError, ValueError):
            continue
        if score < min_score:
            continue

        try:
            ttl = int(pick.get("ttl_hours", 24))
        except (TypeError, ValueError):
            ttl = 24

        out.append(Angle(
            title=_get(art, "title", ""),
            url=_get(art, "url", "") or _get(art, "link", ""),
            source=_get(art, "source", ""),
            category=_get(art, "category", ""),
            score=score,
            why=str(pick.get("why", "")).strip(),
            angles=[str(a).strip() for a in pick.get("angles", []) if str(a).strip()],
            format_hint=str(pick.get("format", "")).strip(),
            ttl_hours=ttl,
        ))

    out.sort(key=lambda a: a.score, reverse=True)
    return out[:max_angles]


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------

_RULES = "Temas y enfoques para LinkedIn, Instagram de la marca o X. El texto lo escribís vos."

_INK, _MUTED, _RULE, _ACCENT = "#16181d", "#6b7280", "#e6e8ec", "#1f5eff"
_FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"


def _esc(text: str) -> str:
    import html
    return html.escape(text or "", quote=True)


def render_html(angles: list[Angle]) -> str:
    """Section appended to the end of the digest email."""
    if not angles:
        return ""

    cards = []
    for angle in angles:
        bullets = "".join(
            f'<li style="margin-bottom:5px;">{_esc(a)}</li>' for a in angle.angles
        )
        cards.append(f"""
        <tr><td style="padding:16px 0;border-bottom:1px solid {_RULE};">
          <div style="font-family:{_FONT};font-size:11px;color:{_MUTED};
                      text-transform:uppercase;letter-spacing:.06em;padding-bottom:5px;">
            {angle.score}/100 &nbsp;·&nbsp; {_esc(angle.format_hint)}
            &nbsp;·&nbsp; vence en {angle.ttl_hours}h
          </div>
          <div style="font-family:{_FONT};font-size:15px;font-weight:600;
                      color:{_INK};padding-bottom:5px;">{_esc(angle.title)}</div>
          <div style="font-family:{_FONT};font-size:14px;color:{_MUTED};
                      padding-bottom:8px;">{_esc(angle.why)}</div>
          <ul style="font-family:{_FONT};font-size:14px;color:{_INK};
                     line-height:1.5;margin:0;padding-left:18px;">{bullets}</ul>
          <div style="padding-top:8px;">
            <a href="{_esc(angle.url)}" style="font-family:{_FONT};font-size:13px;
               color:{_ACCENT};text-decoration:none;">Fuente &rarr;</a>
          </div>
        </td></tr>""")

    return f"""
        <tr><td style="padding:34px 0 4px 0;">
          <div style="font-family:{_FONT};font-size:13px;font-weight:700;
                      letter-spacing:.12em;text-transform:uppercase;color:{_ACCENT};">
            {_esc(config.TRENDING_TITLE)}
          </div>
          <div style="font-family:{_FONT};font-size:12px;color:{_MUTED};padding-top:4px;">
            {_RULES}
          </div>
        </td></tr>
        <tr><td><table role="presentation" width="100%" cellpadding="0"
                       cellspacing="0" border="0">{"".join(cards)}</table></td></tr>"""


def render_text(angles: list[Angle]) -> str:
    if not angles:
        return ""
    title = config.TRENDING_TITLE.upper()
    lines = ["", title, "=" * len(title), _RULES, ""]
    for angle in angles:
        lines.append(f"[{angle.score}/100 · {angle.format_hint} · vence en {angle.ttl_hours}h]")
        lines.append(angle.title)
        lines.append(f"  {angle.why}")
        lines.extend(f"  - {a}" for a in angle.angles)
        lines.append(f"  {angle.url}")
        lines.append("")
    return "\n".join(lines)
