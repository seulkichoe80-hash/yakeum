from pathlib import Path
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from backend.api.demo_deployment import validate_external_demo_settings
from backend.api.web_runtime import configure_web


def settings():
    return dict(YAKEUM_EXTERNAL_DEMO='1',YAKEUM_APP_MODE='development',
                YAKEUM_SERVE_FRONTEND='1',YAKEUM_DEV_ACCOUNT_ENABLED='1',
                YAKEUM_DEV_COOKIE_SECURE='1',YAKEUM_GEMINI_LIVE_ENABLED='0',
                YAKEUM_DEV_ORIGIN='https://demo.example.invalid',
                YAKEUM_DEV_DB_PATH='/data/yakeum.sqlite3',
                YAKEUM_DEMO_GATE_USERNAME='synthetic-gate',
                YAKEUM_DEMO_GATE_PASSWORD='SYNTHETIC-only-gate-pass-123')


def test_valid_external_synthetic_settings_and_local_default():
    validate_external_demo_settings(settings())
    validate_external_demo_settings({})


@pytest.mark.parametrize('name,value',[
    ('YAKEUM_DEMO_GATE_PASSWORD','short'),('YAKEUM_DEMO_GATE_USERNAME',''),
    ('YAKEUM_GEMINI_LIVE_ENABLED','1'),('YAKEUM_DEV_COOKIE_SECURE','0'),
    ('YAKEUM_APP_MODE','production'),('YAKEUM_DEV_ACCOUNT_ENABLED','0'),
    ('YAKEUM_SERVE_FRONTEND','0'),('YAKEUM_DEV_ORIGIN','http://demo.example.invalid'),
    ('YAKEUM_DEV_ORIGIN','https://demo.example.invalid/path'),
    ('YAKEUM_DEV_ORIGIN','https://demo.example.invalid?token=not-real'),
    ('YAKEUM_DEV_ORIGIN','https://user:synthetic@example.invalid'),
    ('YAKEUM_DEV_ORIGIN','https://*.example.invalid'),
    ('YAKEUM_DEV_DB_PATH','relative.sqlite3'),
    ('YAKEUM_DEV_DB_PATH',str(Path(__file__).resolve().parents[2]/'unsafe.sqlite3')),
])
def test_invalid_external_settings_refuse_startup_without_echoing_values(name,value):
    values=settings();values[name]=value
    with pytest.raises(RuntimeError) as e:validate_external_demo_settings(values)
    assert not value or value not in str(e.value) or value in ('0','1','production')
    assert 'not-real' not in str(e.value) and 'synthetic@' not in str(e.value)


def test_private_api_errors_and_success_are_not_cacheable(monkeypatch):
    monkeypatch.delenv('YAKEUM_EXTERNAL_DEMO',raising=False)
    monkeypatch.delenv('YAKEUM_SERVE_FRONTEND',raising=False)
    app=FastAPI();configure_web(app);client=TestClient(app)
    for path in ['/api/health','/api/no-such-data']:
        response=client.get(path)
        assert response.headers['cache-control']=='no-store'
        assert response.headers['x-content-type-options']=='nosniff'
        assert response.headers['referrer-policy']=='no-referrer'


def test_external_entrance_blocks_ui_api_and_docs_but_allows_minimal_liveness(monkeypatch,tmp_path):
    values=settings()
    for key,value in values.items():monkeypatch.setenv(key,value)
    (tmp_path/'index.html').write_text('synthetic-screen')
    monkeypatch.setenv('YAKEUM_FRONTEND_DIST',str(tmp_path))
    app=FastAPI();configure_web(app);client=TestClient(app)
    for path in ['/', '/docs', '/openapi.json', '/api/dev-account/families', '/assets/test.js']:
        response=client.get(path)
        assert response.status_code==401
        assert response.headers['cache-control']=='no-store'
        assert response.headers['www-authenticate'].startswith('Basic')
    assert client.get('/api/health').status_code==200
    assert client.get('/',auth=('synthetic-gate','wrong')).status_code==401
    assert client.get('/',headers={'Authorization':'Basic not-valid!'}).status_code==401
    correct=('synthetic-gate',values['YAKEUM_DEMO_GATE_PASSWORD'])
    assert client.get('/',auth=correct).text=='synthetic-screen'
    # The entrance grants no app identity or family permission.
    assert client.get('/api/dev-account/families',auth=correct).status_code==404
    assert values['YAKEUM_DEMO_GATE_PASSWORD'] not in client.get('/').text


def test_https_gate_keeps_cookie_csrf_and_family_ownership_separate(monkeypatch,tmp_path):
    from backend.api.dev_account import router
    values=settings()
    for key,value in values.items():monkeypatch.setenv(key,value)
    (tmp_path/'index.html').write_text('synthetic-screen')
    monkeypatch.setenv('YAKEUM_FRONTEND_DIST',str(tmp_path))
    app=FastAPI();app.include_router(router);configure_web(app)
    # HTTPS TestClient checks cookie semantics, not a real certificate/TLS handshake.
    monkeypatch.setenv('YAKEUM_DEV_ACCOUNT_ENABLED','1')
    monkeypatch.setenv('YAKEUM_APP_MODE','development')
    monkeypatch.setenv('YAKEUM_DEV_COOKIE_SECURE','1')
    monkeypatch.setenv('YAKEUM_DEV_ORIGIN','https://demo.example.invalid')
    monkeypatch.setenv('YAKEUM_DEV_DB_PATH',str(tmp_path/'synthetic.sqlite3'))
    c=TestClient(app,base_url='https://demo.example.invalid')
    c.auth=('synthetic-gate',values['YAKEUM_DEMO_GATE_PASSWORD'])
    c.headers['Origin']='https://demo.example.invalid'
    password='SYNTHETIC-account-only-pass-123'
    assert c.post('/api/dev-account/register',json={'username':'synthetic_gate_user','password':password}).status_code==201
    login=c.post('/api/dev-account/login',json={'username':'synthetic_gate_user','password':password})
    cookie=login.headers['set-cookie']
    assert 'Secure' in cookie and 'HttpOnly' in cookie and 'SameSite=strict' in cookie
    assert c.get('/api/dev-account/me').status_code==200
    assert c.post('/api/dev-account/families',json={'name':'가상 가족'}).status_code==403
    c.headers['X-CSRF-Token']=login.json()['csrf_token']
    assert c.post('/api/dev-account/families',json={'name':'가상 가족'}).status_code==201
