from __future__ import annotations

import json
import logging
import urllib.request
from datetime import date

from shared.config import Settings
from shared.models import ComedyBrief

logger = logging.getLogger(__name__)


def _post_slack(webhook_url: str, message: str) -> None:
    """Send a message to Slack via webhook."""
    payload = json.dumps({"text": message}).encode("utf-8")
    req = urllib.request.Request(
        webhook_url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status != 200:
                logger.warning("Slack webhook returned status %d", resp.status)
    except Exception:
        logger.exception("Failed to send Slack alert")


def alert_success(brief: ComedyBrief, deliveries: list[str], settings: Settings) -> None:
    """Send success notification with brief summary."""
    if not settings.slack_webhook_url:
        return

    top_titles = [s.item.title for s in brief.items[:3]]
    top_list = "\n".join(f"  • {t}" for t in top_titles)

    message = (
        f":newspaper: *Comedy Brief — {brief.date.isoformat()}*\n"
        f"Top picks:\n{top_list}\n\n"
        f"Delivered to: {', '.join(deliveries)}"
    )
    _post_slack(settings.slack_webhook_url, message)


def alert_failure(error: Exception, settings: Settings) -> None:
    """Send failure notification."""
    if not settings.slack_webhook_url:
        return

    message = (
        f":rotating_light: *Agent Researcher Failed — {date.today().isoformat()}*\n"
        f"Error: {type(error).__name__}: {error}"
    )
    _post_slack(settings.slack_webhook_url, message)
