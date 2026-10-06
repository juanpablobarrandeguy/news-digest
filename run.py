#!/usr/bin/env python3
"""Build and send the daily news digest.

    python run.py              # fetch, pick, summarize, send
    DRY_RUN=1 python run.py    # print to stdout, don't send, don't touch state
"""

import logging
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

from digest import config, editor, fetch, health, llm, render, send, state, summarize, tweets


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-7s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    log = logging.getLogger("digest")

    try:
        now = datetime.now(ZoneInfo(config.TIMEZONE))
    except Exception:  # noqa: BLE001
        log.warning("unknown timezone %r — falling back to UTC", config.TIMEZONE)
        now = datetime.now()

    today = now.date().isoformat()
    if not config.DRY_RUN and not config.FORCE and state.last_sent() == today:
        log.info("digest for %s already sent — nothing to do", today)
        return 0

    if not llm.is_enabled() and config.LLM_PROVIDER != "none":
        health.warn("Sin clave de IA (LLM_API_KEY): notas elegidas por fecha y fuente, "
                    "con el texto de cada feed en lugar de un resumen.")

    seen = state.prune(state.load())
    log.info("%d urls in the seen store", len(seen))

    use_editor = config.EDITOR_ENABLED and llm.is_enabled()
    buckets = fetch.build_candidates(set(seen), config.EDITOR_POOL if use_editor else None)
    if sum(len(v) for v in buckets.values()) == 0:
        log.warning("nothing new to report — skipping send")
        return 0

    if use_editor:
        buckets = editor.pick(buckets, llm.call)
    total = sum(len(v) for v in buckets.values())

    buckets = summarize.summarize(buckets)

    tweet_html = tweet_text = ""
    if config.TWEETS_ENABLED and llm.is_enabled():
        flat = [a for key in config.SECTION_ORDER for a in buckets.get(key, [])]
        angles = tweets.generate(flat, llm.call)
        log.info("trending angles: %d above threshold", len(angles))
        tweet_html = tweets.render_html(angles)
        tweet_text = tweets.render_text(angles)

    notices = health.notices()
    html_body = render.render_html(buckets, now, tweet_html, notices)
    text_body = render.render_text(buckets, now, tweet_text, notices)
    subject = render.subject(buckets, now)

    send.send(subject, text_body, html_body)

    if not config.DRY_RUN:
        keys = [k for items in buckets.values() for a in items for k in a.state_keys]
        state.save(state.record(seen, keys))
        state.mark_sent(today)

    log.info("done: %d stories", total)
    return 0


if __name__ == "__main__":
    sys.exit(main())
