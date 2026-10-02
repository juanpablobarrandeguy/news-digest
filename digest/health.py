"""Problems worth telling the reader about, collected during a run.

Failures degrade instead of killing the run (a dead feed is skipped, a failed
LLM call falls back to RSS snippets). That keeps the email coming, but it also
hides breakage for weeks. Anything that degraded gets a line here, and the
email prints them in a small footer, so a quiet failure is still visible.
"""

_notices: list[str] = []


def warn(message: str) -> None:
    if message not in _notices:
        _notices.append(message)


def notices() -> list[str]:
    return list(_notices)


def reset() -> None:
    _notices.clear()
