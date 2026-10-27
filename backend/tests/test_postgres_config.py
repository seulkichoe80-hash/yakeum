import pytest
from fastapi import HTTPException
from backend.storage.postgres_db import connection_settings


def test_remote_postgres_requires_certificate_verification_and_no_prepared_statements():
    raw,options=connection_settings({'YAKEUM_DATABASE_URL':'postgresql://synthetic:fake-password@db.example.invalid/demo?sslmode=disable'})
    assert options['sslmode']=='verify-full' and options['prepare_threshold'] is None
    assert options['connect_timeout']==10


@pytest.mark.parametrize('values',[
    {},{'YAKEUM_DATABASE_URL':'not-a-url'},
    {'YAKEUM_DATABASE_URL':'postgresql://synthetic:secret@db.example.invalid/demo','YAKEUM_PG_LOCAL_TEST':'1'},
    {'YAKEUM_DATABASE_URL':'postgresql://synthetic:secret@localhost/demo','YAKEUM_PG_LOCAL_TEST':'1','YAKEUM_EXTERNAL_DEMO':'1'},
])
def test_missing_or_insecure_remote_configuration_is_sanitized(values):
    with pytest.raises(HTTPException) as e:connection_settings(values)
    assert e.value.status_code==503 and 'secret' not in e.value.detail


def test_unavailable_postgres_does_not_fall_back_or_expose_url(monkeypatch):
    import psycopg
    from backend.storage.local_db import database
    monkeypatch.setenv('YAKEUM_DEV_ACCOUNT_ENABLED','1');monkeypatch.setenv('YAKEUM_APP_MODE','development')
    monkeypatch.setenv('YAKEUM_STORAGE_BACKEND','postgres')
    monkeypatch.setenv('YAKEUM_DATABASE_URL','postgresql://synthetic:private-secret@db.example.invalid/demo')
    def fail(*args,**kwargs):raise psycopg.OperationalError('private-secret private-query')
    monkeypatch.setattr(psycopg,'connect',fail)
    with pytest.raises(HTTPException) as e:
        with database():pass
    assert e.value.status_code==503 and 'private' not in e.value.detail


def test_external_postgres_uses_tls_without_requiring_sqlite_path():
    from backend.tests.test_demo_deployment import settings
    from backend.api.demo_deployment import validate_external_demo_settings
    values=settings();values.pop('YAKEUM_DEV_DB_PATH')
    values.update(YAKEUM_STORAGE_BACKEND='postgres',YAKEUM_DATABASE_URL='postgresql://synthetic:fake-password@db.example.invalid/demo')
    validate_external_demo_settings(values)
    values['YAKEUM_PG_LOCAL_TEST']='1'
    with pytest.raises(RuntimeError):validate_external_demo_settings(values)


def test_broken_connection_rollback_cannot_leak_provider_error(monkeypatch):
    import psycopg
    from backend.storage.local_db import database
    monkeypatch.setenv('YAKEUM_DEV_ACCOUNT_ENABLED','1');monkeypatch.setenv('YAKEUM_APP_MODE','development')
    monkeypatch.setenv('YAKEUM_STORAGE_BACKEND','postgres')
    monkeypatch.setenv('YAKEUM_DATABASE_URL','postgresql://synthetic:private-secret@db.example.invalid/demo')
    class Broken:
        def execute(self,*a,**kw):raise psycopg.OperationalError('private-secret')
        def rollback(self):raise psycopg.OperationalError('private-secret')
        def close(self):pass
    monkeypatch.setattr(psycopg,'connect',lambda *a,**kw:Broken())
    with pytest.raises(HTTPException) as e:
        with database():pass
    assert e.value.status_code==503 and 'private' not in e.value.detail
