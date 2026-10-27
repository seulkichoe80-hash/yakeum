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
                YAKEUM_DEV_DB_PATH='/data/yakeum.sqlite3')


def test_valid_external_synthetic_settings_and_local_default():
    validate_external_demo_settings(settings())
    validate_external_demo_settings({})


@pytest.mark.parametrize('name,value',[
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
    assert value not in str(e.value) or value in ('0','1','production')
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
