import logging
import time
from datetime import datetime, timezone

from app import db
from app.models import ContainerConfig, Metric, Setting

logger = logging.getLogger(__name__)

# Track state across invocations
_plex_active = False
_plex_inactive_since = None
_paused_containers = set()


def check_plex_and_schedule(app):
    """Check if Plex is streaming and manage container scheduling."""
    global _plex_active, _plex_inactive_since, _paused_containers

    with app.app_context():
        plex_name_setting = db.session.get(Setting, 'plex_container')
        plex_name = plex_name_setting.value if plex_name_setting else 'plex'

        cpu_threshold_setting = db.session.get(Setting, 'plex_cpu_threshold')
        cpu_threshold = float(cpu_threshold_setting.value) if cpu_threshold_setting else 20.0

        net_threshold_setting = db.session.get(Setting, 'plex_net_threshold')
        net_threshold = int(net_threshold_setting.value) if net_threshold_setting else 50_000_000

        action_delay_setting = db.session.get(Setting, 'plex_action_delay')
        action_delay = int(action_delay_setting.value) if action_delay_setting else 60

        restart_delay_setting = db.session.get(Setting, 'plex_restart_delay')
        restart_delay = int(restart_delay_setting.value) if restart_delay_setting else 300

        # Get latest Plex metrics
        latest_plex = Metric.query.filter_by(
            container_name=plex_name
        ).order_by(Metric.timestamp.desc()).first()

        if not latest_plex:
            return

        is_streaming = (
            latest_plex.cpu_percent > cpu_threshold
            or latest_plex.network_rx > net_threshold
        )

        now = time.time()

        if is_streaming and not _plex_active:
            # Plex just became active - wait for action_delay to avoid false positives
            if not hasattr(check_plex_and_schedule, '_stream_start'):
                check_plex_and_schedule._stream_start = now
                return

            elapsed = now - check_plex_and_schedule._stream_start
            if elapsed < action_delay:
                return

            _plex_active = True
            _plex_inactive_since = None
            check_plex_and_schedule._stream_start = None
            logger.info("Plex streaming detected, applying scheduling rules")
            _apply_plex_rules(app)

        elif is_streaming and _plex_active:
            # Still streaming, reset inactive timer
            _plex_inactive_since = None
            check_plex_and_schedule._stream_start = None

        elif not is_streaming and _plex_active:
            # Plex stopped streaming
            if _plex_inactive_since is None:
                _plex_inactive_since = now

            elapsed = now - _plex_inactive_since
            if elapsed >= restart_delay:
                _plex_active = False
                _plex_inactive_since = None
                logger.info("Plex inactive for %ds, restarting paused containers", restart_delay)
                _restart_paused_containers(app)

        else:
            # Not streaming, not previously active
            check_plex_and_schedule._stream_start = None


def _apply_plex_rules(app):
    """Pause/stop containers based on their plex_action config."""
    global _paused_containers
    from app.collector import container_action
    from app.notifier import send_notification

    configs = ContainerConfig.query.filter(
        ContainerConfig.plex_action.in_(['pause', 'stop'])
    ).all()

    for config in configs:
        action = config.plex_action
        success, msg = container_action(config.container_name, action)
        if success:
            _paused_containers.add(config.container_name)
            logger.info("Plex active: %s container %s", action, config.container_name)
            send_notification(
                app,
                f"Plex streaming detected: {action}d {config.container_name}"
            )
        else:
            logger.warning("Failed to %s %s: %s", action, config.container_name, msg)


def _restart_paused_containers(app):
    """Restart containers that were paused/stopped for Plex."""
    global _paused_containers
    from app.collector import container_action
    from app.notifier import send_notification

    configs = ContainerConfig.query.filter(
        ContainerConfig.auto_restart.is_(True),
        ContainerConfig.container_name.in_(_paused_containers),
    ).all()

    restarted = []
    for config in configs:
        # Try unpause first, then start
        success, msg = container_action(config.container_name, 'unpause')
        if not success:
            success, msg = container_action(config.container_name, 'start')
        if success:
            restarted.append(config.container_name)
            logger.info("Restarted container %s after Plex session", config.container_name)

    _paused_containers.clear()

    if restarted:
        send_notification(
            app,
            f"Plex session ended: restarted {', '.join(restarted)}"
        )


def is_plex_active():
    """Return current Plex streaming state."""
    return _plex_active


def get_paused_containers():
    """Return set of containers currently paused for Plex."""
    return _paused_containers.copy()
