"""Send the digest over plain SMTP. Works with Gmail app passwords."""

import logging
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr, formatdate

from . import config

log = logging.getLogger(__name__)


def build_message(subject: str, text_body: str, html_body: str) -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = formataddr(("Daily Digest", config.MAIL_FROM))
    msg["To"] = config.MAIL_TO
    msg["Date"] = formatdate(localtime=True)
    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")
    return msg


def send(subject: str, text_body: str, html_body: str) -> None:
    if config.DRY_RUN:
        print(f"--- DRY RUN ---\nSubject: {subject}\n")
        print(text_body)
        return

    missing = [
        name for name, value in (
            ("SMTP_USER", config.SMTP_USER),
            ("SMTP_PASS", config.SMTP_PASS),
            ("MAIL_TO", config.MAIL_TO),
        ) if not value
    ]
    if missing:
        raise RuntimeError(f"missing required env vars: {', '.join(missing)}")

    msg = build_message(subject, text_body, html_body)
    context = ssl.create_default_context()

    if config.SMTP_PORT == 465:
        with smtplib.SMTP_SSL(config.SMTP_HOST, config.SMTP_PORT, context=context, timeout=45) as server:
            server.login(config.SMTP_USER, config.SMTP_PASS)
            server.send_message(msg)
    else:
        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=45) as server:
            server.ehlo()
            server.starttls(context=context)
            server.login(config.SMTP_USER, config.SMTP_PASS)
            server.send_message(msg)

    log.info("email sent to %s", config.MAIL_TO)
