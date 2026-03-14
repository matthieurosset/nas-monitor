from datetime import datetime, timedelta, timezone

from app.models import Metric, Insight
from app.analyzer import _detect_recurring_peaks


def test_detect_recurring_peaks(app, db):
    """Test that recurring CPU peaks are detected."""
    with app.app_context():
        now = datetime.now(timezone.utc)

        # Create metrics with high CPU at hour 21 for multiple days
        for day_offset in range(5):
            ts = now - timedelta(days=day_offset)
            ts = ts.replace(hour=21, minute=0, second=0, microsecond=0)
            db.session.add(Metric(
                container_id='abc',
                container_name='sonarr',
                timestamp=ts,
                cpu_percent=85.0,
                memory_bytes=1024 * 1024 * 200,
                memory_percent=20.0,
                network_rx=1000,
                network_tx=500,
            ))

        db.session.commit()
        _detect_recurring_peaks(app)

        insight = Insight.query.filter_by(
            container_name='sonarr',
            insight_type='recurring_peak',
        ).first()
        assert insight is not None
        assert '21:00' in insight.description
