from flask import Blueprint, render_template, request, jsonify

from app.collector import get_latest_stats, container_action, get_container_list
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
    # Sort by combined CPU + RAM usage descending
    stats.sort(key=lambda s: s['cpu_percent'] + s['memory_percent'], reverse=True)
    # Compute global totals
    total_cpu = sum(s['cpu_percent'] for s in stats)
    total_ram_mb = sum(s['memory_bytes'] for s in stats) / (1024 * 1024)
    # Use the first container's memory to estimate total system RAM
    # (memory_percent = usage/limit, so limit = usage/percent*100)
    total_ram_percent = 0
    if stats:
        total_bytes = sum(s['memory_bytes'] for s in stats)
        # All containers share the same host memory limit
        first_with_ram = next((s for s in stats if s['memory_percent'] > 0), None)
        if first_with_ram:
            host_ram = first_with_ram['memory_bytes'] / first_with_ram['memory_percent'] * 100
            total_ram_percent = (total_bytes / host_ram) * 100
    return render_template(
        'partials/container_stats.html',
        stats=stats,
        total_cpu=round(total_cpu, 1),
        total_ram_mb=round(total_ram_mb, 1),
        total_ram_percent=round(total_ram_percent, 1),
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
