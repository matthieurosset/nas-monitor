from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app

from app import db
from app.models import ContainerConfig, Setting
from app.collector import get_container_list
from app.notifier import test_notification

settings_bp = Blueprint('settings', __name__)


@settings_bp.route('/')
def index():
    settings = {s.key: s.value for s in Setting.query.all()}
    containers = get_container_list()
    configs = {c.container_name: c for c in ContainerConfig.query.all()}
    return render_template(
        'settings.html',
        settings=settings,
        containers=containers,
        configs=configs,
    )


@settings_bp.route('/general', methods=['POST'])
def update_general():
    """Update general settings."""
    keys = [
        'polling_interval', 'retention_days', 'plex_container',
        'plex_cpu_threshold', 'plex_net_threshold',
        'plex_action_delay', 'plex_restart_delay',
        'alert_cpu_threshold', 'alert_ram_threshold',
    ]
    for key in keys:
        value = request.form.get(key, '')
        setting = db.session.get(Setting, key)
        if setting:
            setting.value = value
        else:
            db.session.add(Setting(key=key, value=value))
    db.session.commit()
    return redirect(url_for('settings.index'))


@settings_bp.route('/notifications', methods=['POST'])
def update_notifications():
    """Update notification webhook settings."""
    keys = ['discord_webhook', 'telegram_bot_token', 'telegram_chat_id']
    for key in keys:
        value = request.form.get(key, '')
        setting = db.session.get(Setting, key)
        if setting:
            setting.value = value
        else:
            db.session.add(Setting(key=key, value=value))
    db.session.commit()
    return redirect(url_for('settings.index'))


@settings_bp.route('/test-notification', methods=['POST'])
def test_notif():
    """Send a test notification."""
    channel = request.form.get('channel', 'discord')
    test_notification(current_app._get_current_object(), channel)
    return redirect(url_for('settings.index'))


@settings_bp.route('/container', methods=['POST'])
def update_container_config():
    """Update per-container scheduling config."""
    name = request.form.get('container_name')
    if not name:
        return redirect(url_for('settings.index'))

    config = db.session.get(ContainerConfig, name)
    if not config:
        config = ContainerConfig(container_name=name)
        db.session.add(config)

    config.priority = request.form.get('priority', 'normal')
    config.plex_action = request.form.get('plex_action', 'none')
    config.auto_restart = request.form.get('auto_restart') == 'on'
    db.session.commit()

    return redirect(url_for('settings.index'))
