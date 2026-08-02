"""Offline smoke test: synthetic feeds through the full pipeline, no network."""

import logging
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from pathlib import Path

from digest import config, fetch, render, state, summarize

logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(message)s")

FIX = Path("/tmp/fixtures")
FIX.mkdir(exist_ok=True)
now = datetime.now(timezone.utc)


def rss(title, items):
    entries = "".join(
        f"""  <item>
    <title>{t}</title>
    <link>{u}</link>
    <description><![CDATA[{d}]]></description>
    <pubDate>{format_datetime(now - timedelta(hours=h))}</pubDate>
  </item>"""
        for t, u, d, h in items
    )
    return f"""<?xml version="1.0"?><rss version="2.0"><channel>
<title>{title}</title><link>https://example.com</link><description>x</description>
{entries}
</channel></rss>"""


fixtures = {
    "ai.xml": rss("AI Feed", [
        ("Anthropic ships a new model tier", "https://ex.com/a1?utm_source=rss", "<p>The company announced &amp; released a new tier.</p>", 3),
        ("Old news nobody needs", "https://ex.com/old", "Stale item.", 200),
    ]),
    "tech.xml": rss("Tech Feed", [
        ("Chipmaker posts record quarter on AI demand", "https://ex.com/t1", "Revenue climbed sharply.", 6),
        ("New filesystem lands in the kernel", "https://ex.com/t2", "Merged after review.", 9),
        ("Anthropic ships a new model tier", "https://ex.com/a1", "Duplicate URL, different feed.", 4),
        ("Anthropic Ships a New Model Tier!", "https://ex.com/dupe", "Near-duplicate headline.", 5),
    ]),
    "nacional.xml": rss("Nacional Feed", [
        ("El Gobierno anunció cambios en el esquema cambiario", "https://ex.com/n1", "Medidas anunciadas el jueves.", 5),
        ("Paro de transporte afecta el AMBA", "https://ex.com/n2", "Servicios reducidos.", 8),
    ]),
    "world.xml": rss("World Feed", [
        ("Central bank holds rates steady", "https://ex.com/w1", "Policymakers cited inflation.", 7),
        ("Trade talks resume after long pause", "https://ex.com/w2", "Negotiators met in Geneva.", 12),
    ]),
}
for name, body in fixtures.items():
    (FIX / name).write_text(body, encoding="utf-8")

config.FEEDS = [
    {"name": "AI Feed", "url": str(FIX / "ai.xml"), "category": "ai", "weight": 1.2},
    {"name": "Tech Feed", "url": str(FIX / "tech.xml"), "category": "tech", "weight": 1.0},
    {"name": "Nacional Feed", "url": str(FIX / "nacional.xml"), "category": "nacional", "weight": 1.0},
    {"name": "World Feed", "url": str(FIX / "world.xml"), "category": "world", "weight": 1.1},
]
config.LLM_PROVIDER = "none"
config.STATE_PATH = "/tmp/seen.json"
Path(config.STATE_PATH).unlink(missing_ok=True)  # start from a clean slate

print("\n=== run 1: empty state ===")
seen = state.prune(state.load())
buckets = fetch.build_candidates(set(seen))
buckets = summarize.summarize(buckets)

for key in config.SECTION_ORDER:
    for a in buckets.get(key, []):
        print(f"  [{key}] {a.title}  <- {a.source}")

assert not any(a.title == "Old news nobody needs" for v in buckets.values() for a in v), \
    "stale item leaked past the lookback window"
urls = [a.key for v in buckets.values() for a in v]
assert len(urls) == len(set(urls)), "duplicate URLs in output"
keys = [k for v in buckets.values() for a in v for k in a.state_keys]
assert len([a for v in buckets.values() for a in v if "Anthropic" in a.title]) == 1, \
    "near-duplicate headline not collapsed"
ai_titles = [a.title for a in buckets["ai"]]
assert any("Chipmaker" in t for t in ai_titles), "AI keyword promotion failed"
assert fetch.canonical_url("https://www.ex.com/a1?utm_source=rss") == "https://ex.com/a1", "url canonicalization failed"

assert len(buckets["nacional"]) == 2, "nacional section did not populate"
assert not any("Gobierno" in a.title for a in buckets["ai"]), "nacional item leaked into AI"

html_out = render.render_html(buckets, now)
text_out = render.render_text(buckets, now)
assert "Read more" in html_out and "https://ex.com/w1" in text_out
assert "Nacional" in html_out and "https://ex.com/n1" in text_out
Path("/tmp/preview.html").write_text(html_out, encoding="utf-8")
print(f"\n  subject: {render.subject(buckets, now)}")
print(f"  html: {len(html_out)} bytes -> /tmp/preview.html")

state.save(state.record(seen, keys))

print("\n=== run 2: same feeds, state populated ===")
seen2 = state.prune(state.load())
buckets2 = fetch.build_candidates(set(seen2))
total2 = sum(len(v) for v in buckets2.values())
assert total2 == 0, f"expected zero repeats, got {total2}"
print(f"  {len(seen2)} urls remembered, {total2} new stories -> send skipped")

print("\nALL CHECKS PASSED")
