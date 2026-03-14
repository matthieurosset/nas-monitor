def test_health(client):
    resp = client.get('/health')
    assert resp.status_code == 200
    assert resp.json['status'] == 'ok'


def test_dashboard(client):
    resp = client.get('/')
    assert resp.status_code == 200
    assert b'Dashboard' in resp.data


def test_history_page(client):
    resp = client.get('/history/')
    assert resp.status_code == 200
    assert b'History' in resp.data


def test_insights_page(client):
    resp = client.get('/insights/')
    assert resp.status_code == 200
    assert b'Insights' in resp.data


def test_settings_page(client):
    resp = client.get('/settings/')
    assert resp.status_code == 200
    assert b'Settings' in resp.data


def test_api_stats(client):
    resp = client.get('/api/stats')
    assert resp.status_code == 200
    assert isinstance(resp.json, list)


def test_api_status(client):
    resp = client.get('/api/status')
    assert resp.status_code == 200
    assert 'plex_active' in resp.json


def test_history_data(client):
    resp = client.get('/history/data?period=1h')
    assert resp.status_code == 200
    assert isinstance(resp.json, dict)


def test_history_containers(client):
    resp = client.get('/history/containers')
    assert resp.status_code == 200
    assert isinstance(resp.json, list)


def test_update_settings(client):
    resp = client.post('/settings/general', data={
        'polling_interval': '60',
        'retention_days': '14',
        'plex_container': 'plex',
        'plex_cpu_threshold': '25',
        'plex_net_threshold': '100000000',
        'plex_action_delay': '120',
        'plex_restart_delay': '600',
        'alert_cpu_threshold': '90',
        'alert_ram_threshold': '90',
    }, follow_redirects=True)
    assert resp.status_code == 200
