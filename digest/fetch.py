"""Fetch RSS feeds, normalize entries, deduplicate, and rank."""

import calendar
import html
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

import feedparser

from . import config, health

log = logging.getLogger(__name__)

TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "utm_id", "fbclid", "gclid", "mc_cid", "mc_eid", "ref", "at_medium",
    "at_campaign", "smid", "partner",
}

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


@dataclass
class Article:
    title: str
    url: str
    source: str
    category: str
    published: datetime
    snippet: str = ""
    weight: float = 1.0
    score: float = 0.0
    paragraph: str = field(default="")

    @property
    def key(self) -> str:
        """Identity for within-run deduplication."""
        return canonical_url(self.url)

    @property
    def state_keys(self) -> list[str]:
        """Everything to remember so this story never comes back.

        Both the URL and the normalized headline: a story collapsed as a
        near-duplicate has a different URL, and would otherwise reappear
        tomorrow once the winning URL is marked as seen.
        """
        keys = [f"u:{self.key}"]
        title_key = _normalize_title(self.title)
        if title_key:
            keys.append(f"t:{title_key}")
        return keys


def canonical_url(url: str) -> str:
    """Strip tracking params and trailing slashes so the same story dedupes."""
    try:
        parts = urlparse(url.strip())
    except ValueError:
        return url.strip()
    query = [(k, v) for k, v in parse_qsl(parts.query) if k.lower() not in TRACKING_PARAMS]
    path = parts.path.rstrip("/") or "/"
    netloc = parts.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    return urlunparse((parts.scheme or "https", netloc, path, "", urlencode(query), ""))


def clean_text(raw: str, limit: int = 600) -> str:
    """RSS descriptions are HTML soup. Flatten to a plain snippet."""
    if not raw:
        return ""
    text = _TAG_RE.sub(" ", raw)
    text = html.unescape(text)
    text = _WS_RE.sub(" ", text).strip()
    if len(text) > limit:
        text = text[:limit].rsplit(" ", 1)[0] + "…"
    return text


def _entry_datetime(entry) -> datetime | None:
    for attr in ("published_parsed", "updated_parsed"):
        parsed = getattr(entry, attr, None)
        if parsed:
            try:
                # feedparser ya normaliza published_parsed a UTC. calendar.timegm
                # lo lee como UTC; time.mktime lo leeria como hora local y correria
                # cada fecha por el offset de la maquina (+3h en Argentina).
                return datetime.fromtimestamp(calendar.timegm(parsed), tz=timezone.utc)
            except (ValueError, OverflowError):
                continue
    return None


def _normalize_title(title: str) -> str:
    return _WS_RE.sub(" ", re.sub(r"[^\w\s]", "", title.lower())).strip()


def _looks_like_ai(article: Article) -> bool:
    blob = f" {article.title.lower()} {article.snippet.lower()} "
    return any(kw in blob for kw in config.AI_KEYWORDS)


def _keyword_regex(keywords: list[str]) -> re.Pattern:
    """Whole-word alternation; a trailing '*' allows any word ending."""
    parts = []
    for kw in keywords:
        if kw.endswith("*"):
            parts.append(re.escape(kw[:-1].lower()) + r"\w*")
        else:
            parts.append(re.escape(kw.lower()) + r"\b")
    return re.compile(r"\b(?:" + "|".join(parts) + ")", re.IGNORECASE)


_CABA_RE = _keyword_regex(config.CABA_KEYWORDS)


def _looks_like_caba(article: Article) -> bool:
    return bool(_CABA_RE.search(f"{article.title} {article.snippet}"))


def fetch_feed(feed: dict) -> list[Article]:
    """Pull and normalize one feed. Never raises — a dead feed shouldn't kill the run."""
    articles: list[Article] = []
    try:
        parsed = feedparser.parse(feed["url"])
    except Exception as exc:  # noqa: BLE001
        log.warning("feed %s failed to parse: %s", feed["name"], exc)
        return articles

    if getattr(parsed, "bozo", False) and not parsed.entries:
        log.warning("feed %s returned nothing usable (%s)", feed["name"], getattr(parsed, "bozo_exception", ""))
        return articles

    now = datetime.now(timezone.utc)
    for entry in parsed.entries[: config.MAX_PER_FEED]:
        url = (getattr(entry, "link", "") or "").strip()
        title = clean_text(getattr(entry, "title", ""), limit=300)
        if not url or not title:
            continue

        published = _entry_datetime(entry)
        if published is None:
            # No date? Assume it's fresh but penalize it during ranking.
            published = now - timedelta(hours=config.LOOKBACK_HOURS - 1)

        snippet = clean_text(
            getattr(entry, "summary", "") or getattr(entry, "description", "")
        )

        articles.append(
            Article(
                title=title,
                url=url,
                source=feed["name"],
                category=feed["category"],
                published=published,
                snippet=snippet,
                weight=feed.get("weight", 1.0),
            )
        )

    log.info("fetched %d items from %s", len(articles), feed["name"])
    return articles


def fetch_all() -> list[Article]:
    articles: list[Article] = []
    empty: list[str] = []
    for feed in config.FEEDS:
        items = fetch_feed(feed)
        if not items:
            empty.append(feed["name"])
        articles.extend(items)
    if empty:
        health.warn("Feeds que hoy no trajeron nada: " + ", ".join(empty) + ".")
    return articles


def filter_recent(articles: list[Article], hours: int) -> list[Article]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    return [a for a in articles if a.published >= cutoff]


def deduplicate(articles: list[Article]) -> list[Article]:
    """Drop repeat URLs and near-identical headlines across sources."""
    seen_urls: set[str] = set()
    seen_titles: set[str] = set()
    out: list[Article] = []
    for article in sorted(articles, key=lambda a: (-a.weight, -a.published.timestamp())):
        url_key = article.key
        title_key = _normalize_title(article.title)
        if url_key in seen_urls or (title_key and title_key in seen_titles):
            continue
        seen_urls.add(url_key)
        seen_titles.add(title_key)
        out.append(article)
    return out


def classify(articles: list[Article]) -> list[Article]:
    """Promote AI-flavoured tech stories into AI, and city stories into CABA."""
    for article in articles:
        if article.category == "tech" and _looks_like_ai(article):
            article.category = "ai"
        elif article.category == "nacional" and _looks_like_caba(article):
            article.category = "caba"
    return articles


def rank(articles: list[Article]) -> list[Article]:
    """Score by source weight and freshness, newest-heavy."""
    now = datetime.now(timezone.utc)
    for article in articles:
        age_hours = max((now - article.published).total_seconds() / 3600, 0.0)
        recency = max(0.0, 1.0 - (age_hours / max(config.LOOKBACK_HOURS, 1)))
        article.score = article.weight * (0.45 + recency)
    return sorted(articles, key=lambda a: -a.score)


def select(articles: list[Article], per_section: int | None = None) -> dict[str, list[Article]]:
    """Bucket ranked articles into sections.

    per_section=None applies the final SECTION_LIMITS. A number keeps that many
    candidates per section instead, for the editor to choose from.
    """
    buckets: dict[str, list[Article]] = {key: [] for key in config.SECTION_ORDER}
    for article in articles:
        bucket = buckets.get(article.category)
        if bucket is None:
            continue
        limit = per_section if per_section is not None else config.SECTION_LIMITS.get(article.category, 5)
        if len(bucket) < limit:
            bucket.append(article)
    return buckets


def build_candidates(seen_keys: set[str], per_section: int | None = None) -> dict[str, list[Article]]:
    """Full pipeline: fetch -> recency -> unseen -> dedupe -> classify -> rank -> select.

    per_section: candidates to keep per section (see select). None = final limits.
    """
    articles = fetch_all()
    log.info("fetched %d articles total", len(articles))

    articles = filter_recent(articles, config.LOOKBACK_HOURS)
    log.info("%d within the last %dh", len(articles), config.LOOKBACK_HOURS)

    # Dedupe before consulting state, so the same winner is picked every run.
    articles = deduplicate(articles)
    log.info("%d after deduplication", len(articles))

    articles = [a for a in articles if not any(k in seen_keys for k in a.state_keys)]
    log.info("%d not previously sent", len(articles))

    articles = classify(articles)
    articles = rank(articles)

    buckets = select(articles, per_section)
    for name, items in buckets.items():
        log.info("section %s: %d %s", name, len(items),
                 "candidates" if per_section is not None else "stories")
    return buckets
