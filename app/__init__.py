import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def create_app():
    app = Flask(__name__)

    db_path = os.environ.get('DATABASE_PATH', 'data/nas-monitor.db')
    os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else '.', exist_ok=True)

    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'nas-monitor-dev-key')

    db.init_app(app)

    from app.routes.dashboard import dashboard_bp
    from app.routes.history import history_bp
    from app.routes.insights import insights_bp
    from app.routes.settings import settings_bp
    from app.routes.api import api_bp

    app.register_blueprint(dashboard_bp)
    app.register_blueprint(history_bp, url_prefix='/history')
    app.register_blueprint(insights_bp, url_prefix='/insights')
    app.register_blueprint(settings_bp, url_prefix='/settings')
    app.register_blueprint(api_bp, url_prefix='/api')

    with app.app_context():
        from app import models  # noqa: F401
        db.create_all()
        _init_default_settings()

    _start_background_jobs(app)

    logging.basicConfig(level=logging.INFO)

    @app.route('/health')
    def health():
        return {'status': 'ok'}

    return app


def _init_default_settings():
    from app.models import Setting
    defaults = {
        'polling_interval': '30',
        'retention_days': '7',
        'plex_container': 'plex',
        'plex_cpu_threshold': '20',
        'plex_net_threshold': '50000000',
        'plex_action_delay': '60',
        'plex_restart_delay': '300',
        'discord_webhook': '',
        'telegram_bot_token': '',
        'telegram_chat_id': '',
        'alert_cpu_threshold': '80',
        'alert_ram_threshold': '80',
    }
    for key, value in defaults.items():
        existing = db.session.get(Setting, key)
        if not existing:
            db.session.add(Setting(key=key, value=value))
    db.session.commit()


def _start_background_jobs(app):
    from apscheduler.schedulers.background import BackgroundScheduler
    from app.collector import collect_metrics, cleanup_old_metrics
    from app.scheduler import check_plex_and_schedule
    from app.analyzer import run_analysis

    scheduler = BackgroundScheduler()

    scheduler.add_job(
        collect_metrics, 'interval', seconds=30,
        args=[app], id='collect_metrics', replace_existing=True
    )
    scheduler.add_job(
        cleanup_old_metrics, 'interval', hours=1,
        args=[app], id='cleanup_metrics', replace_existing=True
    )
    scheduler.add_job(
        check_plex_and_schedule, 'interval', seconds=30,
        args=[app], id='plex_scheduler', replace_existing=True
    )
    scheduler.add_job(
        run_analysis, 'interval', hours=1,
        args=[app], id='run_analysis', replace_existing=True
    )

    scheduler.start()
    app._scheduler = scheduler
