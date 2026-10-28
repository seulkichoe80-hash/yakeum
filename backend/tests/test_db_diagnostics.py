"""Classified synthetic failures only; no network, real DB or credential reads."""
import logging
from unittest.mock import patch
import psycopg
import pytest
from fastapi import HTTPException
from backend.storage.db_diagnostics import classify_db_error,report_db_failure
from backend.storage.postgres_db import postgres_database

PRIVATE='SYNTHETIC-PRIVATE-URL-PASSWORD-COOKIE-HEALTH'


@pytest.mark.parametrize('message,expected',[
 ('could not translate host name','DNS'),
 ('failed to resolve host','DNS'),
 ('temporary failure in name resolution','DNS'),
 ('connection refused','NETWORK_UNREACHABLE'),
 ('network is unreachable','NETWORK_UNREACHABLE'),
 ('connection reset by peer','NETWORK_UNREACHABLE'),
 ('timeout expired','NETWORK_TIMEOUT'),
 ('password authentication failed','AUTHENTICATION'),
 ('Tenant or user not found','AUTHENTICATION'),
 ('certificate verify failed','SSL_CERTIFICATE'),
 ('root certificate file does not exist','SSL_CERTIFICATE'),
 ('server certificate does not match host name','SSL_CERTIFICATE'),
 ('server does not support SSL','SSL_NEGOTIATION'),
 ('invalid connection option','CONFIGURATION'),
 ('opaque failure','CONNECTION_UNKNOWN'),
])
def test_connect_text_only_selects_fixed_category_without_logging_private_text(message,expected,caplog):
    error=psycopg.OperationalError(message+' '+PRIVATE)
    category=classify_db_error(error,'CONNECT')
    assert category==expected
    with caplog.at_level(logging.WARNING):report_db_failure(category,'CONNECT')
    assert PRIVATE not in caplog.text
    for record in caplog.records:
        assert PRIVATE not in repr(record.args)
        assert record.exc_info is None and record.stack_info is None


@pytest.mark.parametrize('error,phase,expected',[
 (psycopg.errors.InvalidPassword,'CONNECT','AUTHENTICATION'),
 (psycopg.errors.InsufficientPrivilege,'INITIALIZE','SCHEMA_PERMISSION'),
 (psycopg.errors.InsufficientPrivilege,'QUERY','PERMISSION'),
 (psycopg.errors.InvalidCatalogName,'CONNECT','DATABASE_SELECTION'),
 (psycopg.errors.TooManyConnections,'CONNECT','CONNECTION_LIMIT'),
 (psycopg.errors.QueryCanceled,'QUERY','DATABASE_TIMEOUT'),
 (psycopg.errors.UndefinedTable,'INITIALIZE','SCHEMA_INITIALIZATION'),
 (psycopg.errors.UniqueViolation,'QUERY','CONSTRAINT'),
])
def test_sqlstate_classification(error,phase,expected):
    assert classify_db_error(error(PRIVATE),phase)==expected


def test_no_arbitrary_log_fields(caplog):
    with pytest.raises(ValueError):report_db_failure(PRIVATE,'CONNECT')
    with pytest.raises(ValueError):report_db_failure('DNS',PRIVATE)
    assert not caplog.records


@pytest.fixture
def fake_config(monkeypatch):
    monkeypatch.setenv('YAKEUM_DATABASE_URL','postgresql://synthetic:synthetic-pass@db.example.invalid/demo')
    monkeypatch.delenv('YAKEUM_PG_LOCAL_TEST',raising=False)


@pytest.mark.parametrize('phase,category',[('CONNECT','DNS'),('INITIALIZE','SCHEMA_PERMISSION'),
 ('QUERY','QUERY_FAILED'),('COMMIT','COMMIT_FAILED')])
def test_storage_emits_stage_and_category_only_and_preserves_503(fake_config,phase,category,caplog):
    class Cursor:
        def fetchall(self):return [{'version':2}]
    class Fake:
        def execute(self,*args,**kwargs):
            if phase=='INITIALIZE':raise psycopg.errors.InsufficientPrivilege(PRIVATE)
            return Cursor()
        def commit(self):
            if phase=='COMMIT':raise psycopg.OperationalError(PRIVATE)
        def rollback(self):pass
        def close(self):pass
    def connect(*args,**kwargs):
        assert kwargs['sslmode']=='verify-full'
        if phase=='CONNECT':raise psycopg.OperationalError('failed to resolve host '+PRIVATE)
        return Fake()
    with patch.object(psycopg,'connect',side_effect=connect),caplog.at_level(logging.WARNING):
        with pytest.raises(HTTPException) as e:
            with postgres_database():
                if phase=='QUERY':raise psycopg.OperationalError(PRIVATE)
    assert e.value.status_code==503 and PRIVATE not in e.value.detail
    assert f'category={category} phase={phase}' in caplog.text
    assert PRIVATE not in caplog.text
    assert all(r.exc_info is None for r in caplog.records)


def test_schema_version_logs_enum_without_resetting_existing_tables(fake_config,caplog):
    statements=[]
    class Cursor:
        def fetchall(self):return [{'version':999}]
    class Fake:
        def execute(self,sql,*a,**kw):statements.append(sql);return Cursor()
        def rollback(self):pass
        def close(self):pass
    with patch.object(psycopg,'connect',return_value=Fake()),caplog.at_level(logging.WARNING):
        with pytest.raises(HTTPException):
            with postgres_database():pass
    assert 'category=SCHEMA_VERSION phase=INITIALIZE' in caplog.text
    assert not any('DROP ' in s or 'TRUNCATE ' in s or 'DELETE ' in s for s in statements)
