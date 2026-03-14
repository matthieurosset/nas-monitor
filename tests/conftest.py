import os
import tempfile

import pytest

from app import create_app, db as _db


@pytest.fixture
def app():
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    os.environ['DATABASE_PATH'] = db_path

    app = create_app()
    app.config['TESTING'] = True

    yield app

    # Shut down the APScheduler to release the DB file
    if hasattr(app, '_scheduler'):
        app._scheduler.shutdown(wait=False)

    # Dispose SQLAlchemy engine to release file handles
    with app.app_context():
        _db.engine.dispose()

    os.close(db_fd)
    try:
        os.unlink(db_path)
    except PermissionError:
        pass  # Windows file locking edge case


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def db(app):
    with app.app_context():
        yield _db
