from datetime import datetime, timedelta, timezone

from flask import Blueprint, render_template, request, jsonify
from sqlalchemy import func

from app import db
from app.models import Metric

history_bp = Blueprint('history', __name__)

PERIOD_MAP = {
    '1h': timedelta(hours=1),
    '6h': timedelta(hours=6),
    '24h': timedelta(hours=24),
    '7d': timedelta(days=7),
}


@history_bp.route('/')
def index():
    return render_template('history.html')


@history_bp.route('/data')
def history_data():
    """Return aggregated metrics for Chart.js."""
    period = request.args.get('period', '1h')
    container = request.args.get('container')

    delta = PERIOD_MAP.get(period, timedelta(hours=1))
    cutoff = datetime.now(timezone.utc) - delta

    query = Metric.query.filter(Metric.timestamp >= cutoff)
    if container:
        query = query.filter_by(container_name=container)

    query = query.order_by(Metric.timestamp)
    metrics = query.all()

    # Group by container
    containers = {}
    for m in metrics:
        if m.container_name not in containers:
            containers[m.container_name] = {
                'timestamps': [],
                'cpu': [],
                'memory': [],
                'net_rx': [],
                'net_tx': [],
            }
        c = containers[m.container_name]
        c['timestamps'].append(m.timestamp.isoformat())
        c['cpu'].append(m.cpu_percent)
        c['memory'].append(m.memory_percent)
        c['net_rx'].append(m.network_rx)
        c['net_tx'].append(m.network_tx)

    return jsonify(containers)


@history_bp.route('/containers')
def container_names():
    """Return list of container names with metrics."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    names = db.session.query(Metric.container_name).filter(
        Metric.timestamp >= cutoff
    ).distinct().all()
    return jsonify([n[0] for n in names])
