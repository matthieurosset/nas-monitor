from flask import Blueprint, render_template, request, jsonify

from app.collector import get_latest_stats, get_host_stats, container_action, get_container_list
from app.scheduler import is_plex_active, get_paused_containers

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
def index():
    containers = get_container_list()
    return render_template(
        'dashboard.html',
        containers=containers,
        plex_active=is_plex_active(),
        paused=get_paused_containers(),
    )


@dashboard_bp.route('/partials/container-stats')
def container_stats_partial():
    """HTMX endpoint: returns updated container stats rows."""
    stats = get_latest_stats()
    stats.sort(key=lambda s: s['cpu_percent'] + s['memory_percent'], reverse=True)

    # Docker totals
    docker_cpu = round(sum(s['cpu_percent'] for s in stats), 1)
    docker_ram_mb = round(sum(s['memory_bytes'] for s in stats) / (1024 * 1024), 1)

    # Host totals (from /proc)
    host = get_host_stats()
    docker_ram_percent = round((docker_ram_mb / host['ram_total_mb']) * 100, 1) if host['ram_total_mb'] else 0

    return render_template(
        'partials/container_stats.html',
        stats=stats,
        docker_cpu=docker_cpu,
        docker_ram_mb=docker_ram_mb,
        docker_ram_percent=docker_ram_percent,
        host_cpu=host['cpu_percent'],
        host_ram_percent=host['ram_percent'],
        host_ram_used_mb=host['ram_used_mb'],
        host_ram_total_mb=host['ram_total_mb'],
        plex_active=is_plex_active(),
        paused=get_paused_containers(),
    )


@dashboard_bp.route('/action', methods=['POST'])
def do_action():
    """Perform a container action (start/stop/pause/unpause)."""
    name = request.form.get('container')
    action = request.form.get('action')
    if not name or not action:
        return jsonify({'error': 'Missing parameters'}), 400

    success, msg = container_action(name, action)
    if success:
        return render_template(
            'partials/action_result.html',
            success=True, message=f'{action.capitalize()} {name}: OK'
        )
    return render_template(
        'partials/action_result.html',
        success=False, message=f'Error: {msg}'
    )
