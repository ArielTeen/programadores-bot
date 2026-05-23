import pytest, os, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["DISCORD_TOKEN"] = "test"
os.environ["CLIENT_ID"] = "123"
os.environ["CLIENT_SECRET"] = "test"
os.environ["DASHBOARD_SECRET"] = "abcdefghijklmnopqrstuvwxyz123456"
os.environ["OWNER_ID"] = "123"

from dashboard.app import app

@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

def test_home_redirect(client):
    resp = client.get("/")
    assert resp.status_code in (200, 302)  # 200=login page, 302=redirect if logged in

def test_home_with_session(client):
    with client.session_transaction() as sess:
        sess["user"] = {"id": "123", "username": "Test"}
        sess["access_token"] = "test_token"
    resp = client.get("/")
    assert resp.status_code == 302
    assert "/dashboard" in resp.location

def test_login_redirect(client):
    resp = client.get("/login")
    assert resp.status_code == 302
    assert "discord.com" in resp.location

def test_logout(client):
    with client.session_transaction() as sess:
        sess["user"] = {"id": "123", "username": "Test"}
    resp = client.get("/logout")
    assert resp.status_code == 302

def test_dashboard_no_auth(client):
    resp = client.get("/dashboard")
    assert resp.status_code == 302
    assert "/login" in resp.location

def test_api_config_no_auth(client):
    resp = client.get("/api/guild/123/config")
    assert resp.status_code == 302

def test_api_stats_no_auth(client):
    resp = client.get("/api/guild/123/stats")
    assert resp.status_code == 302

def test_404_handler(client):
    resp = client.get("/nonexistent")
    assert resp.status_code == 404

def test_home_error_param(client):
    resp = client.get("/?error=Test+Error")
    assert resp.status_code == 200
