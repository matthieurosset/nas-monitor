import logging
from datetime import datetime, timedelta, timezone

import docker

from app import db
from app.models import Metric

logger = logging.getLogger(__name__)

_docker_client = None


def get_docker_client():
    global _docker_client
    if _docker_client is None:
        try:
            _docker_client = docker.from_env()
        except docker.errors.DockerException:
            logger.error("Cannot connect to Docker daemon")
            return None
    return _docker_client


def collect_metrics(app):
    """Collect CPU/RAM/network stats from all running containers."""
    client = get_docker_client()
    if not client:
        return

    with app.app_context():
        try:
            containers = client.containers.list()
        except Exception as e:
            logger.error("Error listing containers: %s", e)
            return

        now = datetime.now(timezone.utc)

        for container in containers:
            try:
                stats = container.stats(stream=False)
                cpu_percent = _calc_cpu_percent(stats)
                mem_usage = stats['memory_stats'].get('usage', 0)
                mem_limit = stats['memory_stats'].get('limit', 1)
                mem_percent = (mem_usage / mem_limit) * 100 if mem_limit else 0

                networks = stats.get('networks', {})
                rx = sum(n.get('rx_bytes', 0) for n in networks.values())
                tx = sum(n.get('tx_bytes', 0) for n in networks.values())

                metric = Metric(
                    container_id=container.short_id,
                    container_name=container.name,
                    timestamp=now,
                    cpu_percent=round(cpu_percent, 2),
                    memory_bytes=mem_usage,
                    memory_percent=round(mem_percent, 2),
                    network_rx=rx,
                    network_tx=tx,
                )
                db.session.add(metric)
            except Exception as e:
                logger.warning("Error collecting stats for %s: %s", container.name, e)

        db.session.commit()


def cleanup_old_metrics(app):
    """Delete metrics older than retention period."""
    with app.app_context():
        from app.models import Setting
        setting = db.session.get(Setting, 'retention_days')
        days = int(setting.value) if setting else 7
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        deleted = Metric.query.filter(Metric.timestamp < cutoff).delete()
        db.session.commit()
        if deleted:
            logger.info("Cleaned up %d old metrics", deleted)


def get_container_list():
    """Get list of all containers with current status."""
    client = get_docker_client()
    if not client:
        return []

    try:
        containers = client.containers.list(all=True)
        return [
            {
                'id': c.short_id,
                'name': c.name,
                'status': c.status,
                'image': c.image.tags[0] if c.image.tags else str(c.image.id)[:20],
            }
            for c in containers
        ]
    except Exception as e:
        logger.error("Error listing containers: %s", e)
        return []


def get_live_stats():
    """Get current stats for all running containers."""
    client = get_docker_client()
    if not client:
        return []

    results = []
    try:
        for container in client.containers.list():
            try:
                stats = container.stats(stream=False)
                cpu_percent = _calc_cpu_percent(stats)
                mem_usage = stats['memory_stats'].get('usage', 0)
                mem_limit = stats['memory_stats'].get('limit', 1)
                mem_percent = (mem_usage / mem_limit) * 100 if mem_limit else 0

                networks = stats.get('networks', {})
                rx = sum(n.get('rx_bytes', 0) for n in networks.values())
                tx = sum(n.get('tx_bytes', 0) for n in networks.values())

                results.append({
                    'id': container.short_id,
                    'name': container.name,
                    'status': container.status,
                    'cpu_percent': round(cpu_percent, 2),
                    'memory_bytes': mem_usage,
                    'memory_mb': round(mem_usage / (1024 * 1024), 1),
                    'memory_percent': round(mem_percent, 2),
                    'network_rx': rx,
                    'network_tx': tx,
                })
            except Exception as e:
                logger.warning("Error getting stats for %s: %s", container.name, e)
    except Exception as e:
        logger.error("Error listing containers: %s", e)

    return results


def container_action(container_name, action):
    """Perform an action on a container (start, stop, pause, unpause)."""
    client = get_docker_client()
    if not client:
        return False, "Cannot connect to Docker"

    try:
        container = client.containers.get(container_name)
        if action == 'start':
            container.start()
        elif action == 'stop':
            container.stop(timeout=10)
        elif action == 'pause':
            container.pause()
        elif action == 'unpause':
            container.unpause()
        elif action == 'restart':
            container.restart(timeout=10)
        else:
            return False, f"Unknown action: {action}"
        return True, f"{action} successful"
    except Exception as e:
        return False, str(e)


def _calc_cpu_percent(stats):
    """Calculate CPU percentage from Docker stats."""
    cpu_stats = stats.get('cpu_stats', {})
    precpu_stats = stats.get('precpu_stats', {})

    cpu_total = cpu_stats.get('cpu_usage', {}).get('total_usage', 0)
    precpu_total = precpu_stats.get('cpu_usage', {}).get('total_usage', 0)
    system_total = cpu_stats.get('system_cpu_usage', 0)
    presystem_total = precpu_stats.get('system_cpu_usage', 0)

    cpu_delta = cpu_total - precpu_total
    system_delta = system_total - presystem_total

    if system_delta > 0 and cpu_delta >= 0:
        num_cpus = cpu_stats.get('online_cpus', 1)
        return (cpu_delta / system_delta) * num_cpus * 100.0

    return 0.0
