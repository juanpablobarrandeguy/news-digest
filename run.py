#!/usr/bin/env python3
"""Build and send the daily news digest.

    python run.py              # fetch, summarize, send
    DRY_RUN=1 python run.py    # print to stdout, don't send, don't touch state
"""

import logging
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

from digest import config, fetch, llm, render, send, state, summarize, tweets


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

    seen = state.prune(state.load())
    log.info("%d urls in the seen store", len(seen))

    buckets = fetch.build_candidates(set(seen))
    total = sum(len(v) for v in buckets.values())
    if total == 0:
        log.warning("nothing new to report — skipping send")
        return 0

    buckets = summarize.summarize(buckets)

    tweet_html = tweet_text = ""
    if config.TWEETS_ENABLED and llm.is_enabled():
        flat = [a for key in config.SECTION_ORDER for a in buckets.get(key, [])]
        angles = tweets.generate(flat, llm.call)
        log.info("tweet angles: %d above threshold", len(angles))
        tweet_html = tweets.render_html(angles)
        tweet_text = tweets.render_text(angles)

    html_body = render.render_html(buckets, now, tweet_html)
    text_body = render.render_text(buckets, now, tweet_text)
    subject = render.subject(buckets, now)

    send.send(subject, text_body, html_body)

    if not config.DRY_RUN:
        keys = [k for items in buckets.values() for a in items for k in a.state_keys]
        state.save(state.record(seen, keys))

    log.info("done: %d stories", total)
    return 0


if __name__ == "__main__":
    sys.exit(main())
