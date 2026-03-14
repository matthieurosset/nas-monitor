import logging

import requests

from app import db
from app.models import Setting

logger = logging.getLogger(__name__)


def send_notification(app, message):
    """Send notification to all configured channels."""
    with app.app_context():
        _send_discord(message)
        _send_telegram(message)


def _send_discord(message):
    """Send a message to Discord via webhook."""
    setting = db.session.get(Setting, 'discord_webhook')
    webhook_url = setting.value if setting else ''
    if not webhook_url:
        return

    try:
        resp = requests.post(
            webhook_url,
            json={'content': f'**nas-monitor** {message}'},
            timeout=10,
        )
        if resp.status_code not in (200, 204):
            logger.warning("Discord webhook returned %d", resp.status_code)
    except Exception as e:
        logger.error("Discord notification failed: %s", e)


def _send_telegram(message):
    """Send a message to Telegram via bot API."""
    token_setting = db.session.get(Setting, 'telegram_bot_token')
    chat_setting = db.session.get(Setting, 'telegram_chat_id')
    token = token_setting.value if token_setting else ''
    chat_id = chat_setting.value if chat_setting else ''

    if not token or not chat_id:
        return

    try:
        resp = requests.post(
            f'https://api.telegram.org/bot{token}/sendMessage',
            json={'chat_id': chat_id, 'text': f'nas-monitor: {message}'},
            timeout=10,
        )
        if resp.status_code != 200:
            logger.warning("Telegram API returned %d", resp.status_code)
    except Exception as e:
        logger.error("Telegram notification failed: %s", e)


def test_notification(app, channel):
    """Send a test notification to verify configuration."""
    with app.app_context():
        if channel == 'discord':
            _send_discord("Test notification - nas-monitor is connected!")
            return True
        elif channel == 'telegram':
            _send_telegram("Test notification - nas-monitor is connected!")
            return True
    return False
