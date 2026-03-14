# nas-monitor

## Project Overview
Docker container monitoring tool for Synology NAS with intelligent pattern analysis and event-based scheduling.

## Stack
- **Backend**: Flask + SQLAlchemy + SQLite + HTMX
- **Frontend**: Pure CSS dark mode, Chart.js for graphs
- **Deployment**: GitHub Actions → GHCR → Portainer

## Conventions
- Python 3.11+
- Flask app factory pattern in `app/__init__.py`
- SQLAlchemy for ORM, SQLite for storage
- HTMX for real-time updates (no heavy JS framework)
- Dark mode only, monitoring-style UI
- All times in UTC

## Project Structure
```
app/              # Flask application
  routes/         # Blueprint routes
  templates/      # Jinja2 templates
  static/         # CSS + JS
tests/            # pytest tests
```

## Commands
```bash
# Development
pip install -r requirements.txt
python run.py

# Tests
pytest tests/ -v

# Docker
docker compose up --build
```

## Infrastructure
- **GitHub**: matthieurosset/nas-monitor
- **Image**: ghcr.io/matthieurosset/nas-monitor:latest
- **Port**: 5200 (host) → 5000 (container)
- **Data**: /volume3/docker/nas-monitor/data → Y:\nas-monitor\data
- **NAS**: PUID=1038, PGID=65536, UMASK=022
- **Docker socket**: mounted read-only for metrics collection
