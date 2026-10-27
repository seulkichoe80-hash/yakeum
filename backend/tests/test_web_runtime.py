from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from backend.api.web_runtime import configure_web
from backend.api.main import app


def test_liveness_contains_no_credentials_or_database_details():
    response=TestClient(app).get('/api/health')
    assert response.status_code==200
    assert response.json()=={'status':'ok','service':'yakeum','scope':'synthetic-demo'}


def test_static_build_shares_origin_without_shadowing_api_or_exposing_source(monkeypatch,tmp_path):
    (tmp_path/'index.html').write_text('<h1>Synthetic app</h1>')
    (tmp_path/'assets').mkdir();(tmp_path/'assets/app.js').write_text('/* synthetic */')
    monkeypatch.setenv('YAKEUM_SERVE_FRONTEND','1');monkeypatch.setenv('YAKEUM_FRONTEND_DIST',str(tmp_path))
    demo=FastAPI()
    @demo.get('/api/example')
    def example():return {'ok':True}
    configure_web(demo);client=TestClient(demo)
    assert client.get('/').status_code==200
    assert client.get('/assets/app.js').status_code==200
    assert client.get('/api/example').json()=={'ok':True}
    for path in ['/api/missing','/.env','/backend/api/main.py','/%2e%2e/private.sqlite3']:
        assert client.get(path).status_code==404


def test_static_mode_fails_if_build_missing(monkeypatch,tmp_path):
    monkeypatch.setenv('YAKEUM_SERVE_FRONTEND','1');monkeypatch.setenv('YAKEUM_FRONTEND_DIST',str(tmp_path/'absent'))
    with pytest.raises(RuntimeError):configure_web(FastAPI())


def test_https_cookie_opt_in_preserves_development_guard(monkeypatch,tmp_path):
    from backend.tests.test_dev_account import account
    monkeypatch.setenv('YAKEUM_DEV_ACCOUNT_ENABLED','1');monkeypatch.setenv('YAKEUM_APP_MODE','development')
    monkeypatch.setenv('YAKEUM_DEV_DB_PATH',str(tmp_path/'synthetic.sqlite3'));monkeypatch.setenv('YAKEUM_DEV_ORIGIN','http://testserver')
    c=account();monkeypatch.setenv('YAKEUM_DEV_COOKIE_SECURE','1')
    from backend.tests.test_dev_account import PASSWORD
    response=c.post('/api/dev-account/login',json={'username':'synthetic_a','password':PASSWORD})
    assert 'Secure' in response.headers['set-cookie'] and 'HttpOnly' in response.headers['set-cookie']
    monkeypatch.setenv('YAKEUM_APP_MODE','production')
    assert c.get('/api/dev-account/me').status_code==503
