"""Render the digest as HTML and plaintext.

Styles are inlined because Gmail and Outlook strip or mangle <style> blocks.
Layout is a single column at 640px, which behaves on a phone.
"""

import html
from datetime import datetime

from . import config
from .fetch import Article

INK = "#16181d"
MUTED = "#6b7280"
RULE = "#e6e8ec"
ACCENT = "#1f5eff"
FONT = ("-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif")


def _esc(text: str) -> str:
    return html.escape(text or "", quote=True)


def _story_html(article: Article, is_last: bool) -> str:
    border = "" if is_last else f"border-bottom:1px solid {RULE};"
    stamp = article.published.strftime("%b %d, %H:%M UTC")
    return f"""
        <tr>
          <td style="padding:20px 0;{border}">
            <div style="font-family:{FONT};font-size:11px;letter-spacing:.06em;
                        text-transform:uppercase;color:{MUTED};padding-bottom:6px;">
              {_esc(article.source)} &nbsp;·&nbsp; {stamp}
            </div>
            <div style="font-family:{FONT};font-size:17px;line-height:1.35;
                        font-weight:600;color:{INK};padding-bottom:8px;">
              {_esc(article.title)}
            </div>
            <div style="font-family:{FONT};font-size:15px;line-height:1.6;color:{INK};">
              {_esc(article.paragraph)}
            </div>
            <div style="padding-top:10px;">
              <a href="{_esc(article.url)}"
                 style="font-family:{FONT};font-size:14px;color:{ACCENT};text-decoration:none;">
                Read more &rarr;
              </a>
            </div>
          </td>
        </tr>"""


def _section_html(key: str, articles: list[Article]) -> str:
    if not articles:
        return ""
    label = config.SECTION_TITLES.get(key, key.title())
    rows = "".join(
        _story_html(a, is_last=(i == len(articles) - 1)) for i, a in enumerate(articles)
    )
    return f"""
        <tr>
          <td style="padding:34px 0 4px 0;">
            <div style="font-family:{FONT};font-size:13px;font-weight:700;
                        letter-spacing:.12em;text-transform:uppercase;color:{ACCENT};">
              {_esc(label)}
            </div>
          </td>
        </tr>
        <tr><td><table role="presentation" width="100%" cellpadding="0"
                       cellspacing="0" border="0">{rows}</table></td></tr>"""


def _notices_html(notices: list[str]) -> str:
    if not notices:
        return ""
    items = "".join(f'<li style="margin-bottom:4px;">{_esc(n)}</li>' for n in notices)
    return f"""
        <tr>
          <td style="padding-top:30px;">
            <div style="font-family:{FONT};font-size:12px;font-weight:700;color:{MUTED};
                        text-transform:uppercase;letter-spacing:.06em;padding-bottom:6px;">
              Avisos
            </div>
            <ul style="font-family:{FONT};font-size:12px;color:{MUTED};line-height:1.5;
                       margin:0;padding-left:18px;">{items}</ul>
          </td>
        </tr>"""


def render_html(buckets: dict[str, list[Article]], now: datetime,
                tweet_section: str = "", notices: list[str] | None = None) -> str:
    sections = "".join(
        _section_html(key, buckets.get(key, [])) for key in config.SECTION_ORDER
    )
    total = sum(len(v) for v in buckets.values())
    headline_date = now.strftime("%A, %B %d, %Y")

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Daily Digest</title></head>
<body style="margin:0;padding:0;background:#f4f5f7;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
         style="background:#f4f5f7;padding:24px 12px;">
    <tr><td align="center">
      <table role="presentation" width="640" cellpadding="0" cellspacing="0" border="0"
             style="max-width:640px;width:100%;background:#ffffff;border-radius:10px;
                    padding:32px 30px 36px 30px;">
        <tr>
          <td style="padding-bottom:6px;border-bottom:2px solid {INK};">
            <div style="font-family:{FONT};font-size:24px;font-weight:700;color:{INK};">
              Daily Digest
            </div>
            <div style="font-family:{FONT};font-size:13px;color:{MUTED};padding:6px 0 12px 0;">
              {headline_date} &nbsp;·&nbsp; {total} stories
            </div>
          </td>
        </tr>
        {sections}
        {tweet_section}
        {_notices_html(notices or [])}
        <tr>
          <td style="padding-top:30px;border-top:1px solid {RULE};">
            <div style="font-family:{FONT};font-size:12px;color:{MUTED};line-height:1.5;">
              Assembled automatically from public RSS feeds.
            </div>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body></html>"""


def render_text(buckets: dict[str, list[Article]], now: datetime,
                tweet_section: str = "", notices: list[str] | None = None) -> str:
    lines = [f"DAILY DIGEST — {now.strftime('%A, %B %d, %Y')}", ""]
    for key in config.SECTION_ORDER:
        articles = buckets.get(key, [])
        if not articles:
            continue
        label = config.SECTION_TITLES.get(key, key.title()).upper()
        lines.extend([label, "=" * len(label), ""])
        for article in articles:
            lines.append(article.title)
            lines.append(f"({article.source} · {article.published.strftime('%b %d, %H:%M UTC')})")
            lines.append(article.paragraph)
            lines.append(article.url)
            lines.append("")
    footer = ""
    if notices:
        footer = "\n\nAVISOS\n" + "\n".join(f"- {n}" for n in notices) + "\n"
    return "\n".join(lines) + tweet_section + footer


def subject(buckets: dict[str, list[Article]], now: datetime) -> str:
    total = sum(len(v) for v in buckets.values())
    return f"{config.MAIL_SUBJECT_PREFIX} — {now.strftime('%b %d')} ({total} stories)"
