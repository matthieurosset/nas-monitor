from flask import Blueprint, jsonify

from app.collector import get_latest_stats, get_container_list
from app.scheduler import is_plex_active, get_paused_containers
from app.analyzer import get_insights

api_bp = Blueprint('api', __name__)


@api_bp.route('/stats')
def stats():
    """JSON endpoint for current container stats."""
    return jsonify(get_latest_stats())


@api_bp.route('/containers')
def containers():
    """JSON endpoint for container list."""
    return jsonify(get_container_list())


@api_bp.route('/status')
def status():
    """JSON endpoint for overall system status."""
    return jsonify({
        'plex_active': is_plex_active(),
        'paused_containers': list(get_paused_containers()),
    })


@api_bp.route('/insights')
def insights():
    """JSON endpoint for insights."""
    result = []
    for i in get_insights():
        result.append({
            'id': i.id,
            'container_name': i.container_name,
            'type': i.insight_type,
            'description': i.description,
            'detected_at': i.detected_at.isoformat(),
            'data': i.data,
        })
    return jsonify(result)
