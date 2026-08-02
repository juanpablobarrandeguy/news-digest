#!/usr/bin/env python3
"""Check every configured feed actually returns usable items.

Run this before launch and any time a section goes quiet:

    python verify_feeds.py

Feed URLs rot. Argentine outlets in particular rearrange their RSS paths every
so often. Anything marked DEAD should be fixed or removed from FEEDS in
digest/config.py.
"""

import sys
from collections import defaultdict
from datetime import datetime, timezone

import feedparser

from digest import config
from digest.fetch import _entry_datetime

GREEN, RED, YELLOW, RESET = "\033[32m", "\033[31m", "\033[33m", "\033[0m"


def check(feed: dict) -> tuple[str, str]:
    try:
        parsed = feedparser.parse(feed["url"])
    except Exception as exc:  # noqa: BLE001
        return "DEAD", str(exc)[:70]

    status = getattr(parsed, "status", None)
    entries = getattr(parsed, "entries", [])

    if status and status >= 400:
        return "DEAD", f"HTTP {status}"
    if not entries:
        detail = str(getattr(parsed, "bozo_exception", "") or "no entries")
        return "DEAD", detail[:70]

    now = datetime.now(timezone.utc)
    dates = [d for d in (_entry_datetime(e) for e in entries) if d]
    if not dates:
        return "WARN", f"{len(entries)} items, no usable dates"

    age = (now - max(dates)).total_seconds() / 3600
    if age > 72:
        return "WARN", f"{len(entries)} items, newest is {age:.0f}h old"
    return "OK", f"{len(entries)} items, newest {age:.1f}h old"


def main() -> int:
    by_category: dict[str, list] = defaultdict(list)
    for feed in config.FEEDS:
        by_category[feed["category"]].append(feed)

    dead = 0
    for category in config.SECTION_ORDER:
        feeds = by_category.get(category, [])
        if not feeds:
            continue
        print(f"\n{config.SECTION_TITLES.get(category, category).upper()}")
        for feed in feeds:
            verdict, detail = check(feed)
            colour = {"OK": GREEN, "WARN": YELLOW, "DEAD": RED}[verdict]
            print(f"  {colour}{verdict:<5}{RESET} {feed['name']:<18} {detail}")
            print(f"        {feed['url']}")
            if verdict == "DEAD":
                dead += 1

    print()
    if dead:
        print(f"{RED}{dead} feed(s) dead — fix or remove them in digest/config.py{RESET}")
        return 1
    print(f"{GREEN}All feeds responding.{RESET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
