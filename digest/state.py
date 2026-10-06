"""Tracks which stories have already been sent, so nothing repeats.

A plain JSON file, committed back to the repo by the workflow. No database,
no cloud storage, and it keeps the repo active so GitHub doesn't disable the
scheduled workflow for inactivity.
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import config

log = logging.getLogger(__name__)


def load(path: str | None = None) -> dict[str, str]:
    target = Path(path or config.STATE_PATH)
    if not target.exists():
        return {}
    try:
        with target.open(encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, dict):
            return data
        log.warning("state file is not an object — starting fresh")
    except (json.JSONDecodeError, OSError) as exc:
        log.warning("could not read state (%s) — starting fresh", exc)
    return {}


def prune(seen: dict[str, str], days: int | None = None) -> dict[str, str]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days or config.STATE_RETENTION_DAYS)
    kept: dict[str, str] = {}
    for key, stamp in seen.items():
        try:
            when = datetime.fromisoformat(stamp)
        except (TypeError, ValueError):
            continue
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
        if when >= cutoff:
            kept[key] = stamp
    return kept


def record(seen: dict[str, str], keys: list[str]) -> dict[str, str]:
    stamp = datetime.now(timezone.utc).isoformat()
    for key in keys:
        seen[key] = stamp
    return seen


def save(seen: dict[str, str], path: str | None = None) -> None:
    target = Path(path or config.STATE_PATH)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(seen, fh, indent=1, sort_keys=True)
        fh.write("\n")
    tmp.replace(target)
    log.info("state saved: %d urls tracked", len(seen))


def last_sent(path: str | None = None) -> str:
    target = Path(path or config.LAST_SENT_PATH)
    try:
        return target.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def mark_sent(day: str, path: str | None = None) -> None:
    target = Path(path or config.LAST_SENT_PATH)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(day + "\n", encoding="utf-8")
    log.info("marked %s as sent", day)
