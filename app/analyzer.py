import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from app import db
from app.models import Insight, Metric

logger = logging.getLogger(__name__)


def run_analysis(app):
    """Run pattern detection and correlation analysis."""
    with app.app_context():
        _detect_recurring_peaks(app)
        _detect_correlations(app)
        _generate_recommendations(app)


def _detect_recurring_peaks(app):
    """Find containers with recurring CPU/RAM peaks at the same hour."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    metrics = Metric.query.filter(Metric.timestamp >= cutoff).all()

    # Group by container → hour_of_day → list of cpu values
    container_hours = defaultdict(lambda: defaultdict(list))
    for m in metrics:
        hour = m.timestamp.hour
        container_hours[m.container_name][hour].append(m.cpu_percent)

    for container_name, hours in container_hours.items():
        for hour, values in hours.items():
            if len(values) < 3:
                continue
            avg = sum(values) / len(values)
            high_count = sum(1 for v in values if v > 70)

            if high_count >= 3 and avg > 50:
                description = (
                    f"{container_name} averages {avg:.0f}% CPU around "
                    f"{hour:02d}:00 UTC ({high_count} peaks >70% in 7 days)"
                )
                _upsert_insight(
                    container_name, 'recurring_peak', description,
                    {'hour': hour, 'avg_cpu': round(avg, 1), 'peak_count': high_count}
                )


def _detect_correlations(app):
    """Find containers whose high CPU correlates with others."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    metrics = Metric.query.filter(Metric.timestamp >= cutoff).order_by(Metric.timestamp).all()

    # Build time-bucketed data (5-minute buckets)
    buckets = defaultdict(dict)
    for m in metrics:
        bucket = m.timestamp.replace(second=0, microsecond=0)
        bucket = bucket.replace(minute=(bucket.minute // 5) * 5)
        buckets[bucket][m.container_name] = m.cpu_percent

    container_names = list({m.container_name for m in metrics})
    if len(container_names) < 2:
        return

    # Simple correlation: when A is high, is B also high?
    for i, name_a in enumerate(container_names):
        for name_b in container_names[i + 1:]:
            both_high = 0
            a_high = 0
            total = 0

            for bucket_data in buckets.values():
                cpu_a = bucket_data.get(name_a)
                cpu_b = bucket_data.get(name_b)
                if cpu_a is None or cpu_b is None:
                    continue
                total += 1
                if cpu_a > 60:
                    a_high += 1
                    if cpu_b > 60:
                        both_high += 1

            if a_high >= 5 and total > 0:
                correlation = both_high / a_high if a_high else 0
                if correlation > 0.6:
                    description = (
                        f"When {name_a} CPU is high, {name_b} is also high "
                        f"{correlation:.0%} of the time"
                    )
                    _upsert_insight(
                        name_a, 'correlation', description,
                        {'correlated_with': name_b, 'correlation': round(correlation, 2)}
                    )


def _generate_recommendations(app):
    """Generate actionable recommendations based on detected patterns."""
    from app.models import Setting
    plex_name = db.session.get(Setting, 'plex_container')
    plex_name = plex_name.value if plex_name else 'plex'

    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    metrics = Metric.query.filter(Metric.timestamp >= cutoff).all()

    # Find containers that are heavy when Plex is active
    plex_active_times = set()
    container_at_time = defaultdict(dict)

    for m in metrics:
        bucket = m.timestamp.replace(second=0, microsecond=0)
        bucket = bucket.replace(minute=(bucket.minute // 5) * 5)
        container_at_time[bucket][m.container_name] = m.cpu_percent
        if m.container_name == plex_name and m.cpu_percent > 15:
            plex_active_times.add(bucket)

    if not plex_active_times:
        return

    container_during_plex = defaultdict(list)
    for t in plex_active_times:
        for name, cpu in container_at_time.get(t, {}).items():
            if name != plex_name:
                container_during_plex[name].append(cpu)

    for name, cpus in container_during_plex.items():
        if len(cpus) < 3:
            continue
        avg = sum(cpus) / len(cpus)
        if avg > 30:
            description = (
                f"Consider pausing {name} during Plex sessions "
                f"(avg {avg:.0f}% CPU when Plex is active)"
            )
            _upsert_insight(
                name, 'recommendation', description,
                {'avg_cpu_during_plex': round(avg, 1), 'sample_count': len(cpus)}
            )


def get_insights():
    """Get all current insights."""
    return Insight.query.order_by(Insight.detected_at.desc()).all()


def _upsert_insight(container_name, insight_type, description, data):
    """Insert or update an insight."""
    existing = Insight.query.filter_by(
        container_name=container_name,
        insight_type=insight_type,
    ).first()

    if existing:
        existing.description = description
        existing.data = data
        existing.detected_at = datetime.now(timezone.utc)
    else:
        insight = Insight(
            container_name=container_name,
            insight_type=insight_type,
            description=description,
            data=data,
        )
        db.session.add(insight)

    db.session.commit()
