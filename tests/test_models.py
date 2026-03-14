from datetime import datetime, timezone

from app.models import Metric, Insight, ContainerConfig, Setting


def test_create_metric(db):
    m = Metric(
        container_id='abc123',
        container_name='test-container',
        timestamp=datetime.now(timezone.utc),
        cpu_percent=45.5,
        memory_bytes=1024 * 1024 * 100,
        memory_percent=25.0,
        network_rx=5000,
        network_tx=3000,
    )
    db.session.add(m)
    db.session.commit()

    result = Metric.query.first()
    assert result.container_name == 'test-container'
    assert result.cpu_percent == 45.5


def test_create_insight(db):
    i = Insight(
        container_name='sonarr',
        insight_type='recurring_peak',
        description='Sonarr peaks at 21:00',
        data={'hour': 21, 'avg_cpu': 75.3},
    )
    db.session.add(i)
    db.session.commit()

    result = Insight.query.first()
    assert result.insight_type == 'recurring_peak'
    assert result.data['hour'] == 21


def test_container_config(db):
    c = ContainerConfig(
        container_name='qbittorrent',
        priority='low',
        plex_action='pause',
        auto_restart=True,
    )
    db.session.add(c)
    db.session.commit()

    result = db.session.get(ContainerConfig, 'qbittorrent')
    assert result.plex_action == 'pause'


def test_default_settings(db):
    s = db.session.get(Setting, 'polling_interval')
    assert s is not None
    assert s.value == '30'
