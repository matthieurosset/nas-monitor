from datetime import datetime, timezone
from app import db


class Metric(db.Model):
    __tablename__ = 'metrics'

    id = db.Column(db.Integer, primary_key=True)
    container_id = db.Column(db.String(64), nullable=False, index=True)
    container_name = db.Column(db.String(255), nullable=False, index=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
    cpu_percent = db.Column(db.Float, default=0.0)
    memory_bytes = db.Column(db.BigInteger, default=0)
    memory_percent = db.Column(db.Float, default=0.0)
    network_rx = db.Column(db.BigInteger, default=0)
    network_tx = db.Column(db.BigInteger, default=0)


class Insight(db.Model):
    __tablename__ = 'insights'

    id = db.Column(db.Integer, primary_key=True)
    container_name = db.Column(db.String(255), nullable=False, index=True)
    insight_type = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=False)
    detected_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    data = db.Column(db.JSON)


class ContainerConfig(db.Model):
    __tablename__ = 'container_config'

    container_name = db.Column(db.String(255), primary_key=True)
    priority = db.Column(db.String(20), default='normal')
    plex_action = db.Column(db.String(20), default='none')
    auto_restart = db.Column(db.Boolean, default=True)


class Setting(db.Model):
    __tablename__ = 'settings'

    key = db.Column(db.String(255), primary_key=True)
    value = db.Column(db.Text)
