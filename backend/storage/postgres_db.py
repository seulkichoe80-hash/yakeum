"""Synthetic demo PostgreSQL adapter. No implicit SQLite fallback or live I/O at import."""
from contextlib import contextmanager, suppress
from pathlib import Path
import os
import sqlite3
from urllib.parse import urlsplit
from fastapi import HTTPException
from backend.storage.db_diagnostics import classify_db_error, report_db_failure


def connection_settings(values=None):
    values=os.environ if values is None else values
    raw=values.get('YAKEUM_DATABASE_URL','')
    try:
        url=urlsplit(raw)
        if url.scheme not in ('postgres','postgresql') or not url.hostname or not url.username or not url.password or not url.path.strip('/'):
            raise ValueError()
        local=(values.get('YAKEUM_PG_LOCAL_TEST')=='1' and url.hostname in ('127.0.0.1','localhost')
               and values.get('YAKEUM_EXTERNAL_DEMO')!='1')
        if values.get('YAKEUM_PG_LOCAL_TEST')=='1' and not local:raise ValueError()
        options={'connect_timeout':10,'prepare_threshold':None}
        options.update(sslmode='disable' if local else 'verify-full')
        if not local:
            options['sslrootcert']=values.get('YAKEUM_PG_SSLROOTCERT','/etc/ssl/certs/ca-certificates.crt')
        return raw,options
    except (ValueError,TypeError):
        report_db_failure('CONFIGURATION','CONFIG')
        raise HTTPException(503,'PostgreSQL 비밀 연결 설정이 필요합니다. 주소나 비밀번호를 화면에 입력하지 마세요.') from None


class Row(dict):
    def __getitem__(self,key):
        return list(self.values())[key] if isinstance(key,int) else super().__getitem__(key)


class Cursor:
    def __init__(self,cursor):self.cursor=cursor
    def fetchone(self):
        row=self.cursor.fetchone();return Row(row) if row is not None else None
    def fetchall(self):return [Row(row) for row in self.cursor.fetchall()]
    def __iter__(self):return iter(self.fetchall())


class Connection:
    def __init__(self,connection):self.connection=connection
    def execute(self,sql,params=()):
        # Only repository-owned SQL statements pass here; never interpolate user values.
        sql=sql.replace('?', '%s').replace('ORDER BY rowid','ORDER BY _created_order')
        if sql.startswith('INSERT OR IGNORE INTO '):
            sql=sql.replace('INSERT OR IGNORE INTO ','INSERT INTO ',1)+' ON CONFLICT DO NOTHING'
        sql=sql.replace('SET count=count+1','SET count=attempts.count+1')
        return Cursor(self.connection.execute(sql,params))


@contextmanager
def postgres_database():
    import psycopg
    from psycopg.rows import dict_row
    from backend.storage.local_db import SCHEMA,HIRA_SCHEMA
    raw,options=connection_settings()
    connection=None
    phase='CONNECT'
    def rollback():
        if connection:
            with suppress(psycopg.Error):connection.rollback()
    try:
        connection=psycopg.connect(raw,row_factory=dict_row,**options)
        phase='INITIALIZE'
        connection.execute("SET LOCAL statement_timeout='10s'")
        # Like BEGIN IMMEDIATE locally: serialize short demo transactions and schema creation.
        connection.execute('SELECT pg_advisory_xact_lock(1948031027)')
        connection.execute('CREATE SCHEMA IF NOT EXISTS yakeum_demo')
        connection.execute('REVOKE ALL ON SCHEMA yakeum_demo FROM PUBLIC')
        connection.execute('SET LOCAL search_path TO yakeum_demo')
        connection.execute('CREATE TABLE IF NOT EXISTS schema_version(version INTEGER NOT NULL)')
        rows=connection.execute('SELECT version FROM schema_version').fetchall()
        if rows and (len(rows)!=1 or rows[0]['version']!=2):
            report_db_failure('SCHEMA_VERSION','INITIALIZE')
            raise HTTPException(503,'지원하지 않는 시연 DB 버전입니다. 기존 자료를 보존하고 설정을 확인해 주세요.')
        if not rows:
            schema=(SCHEMA+HIRA_SCHEMA).replace('REAL','DOUBLE PRECISION')
            schema=schema.replace('name TEXT NOT NULL);','name TEXT NOT NULL, _created_order BIGSERIAL);')
            for statement in schema.split(';'):
                if statement.strip():connection.execute(statement)
            connection.execute('INSERT INTO schema_version VALUES(2)')
        phase='QUERY'
        yield Connection(connection)
        phase='COMMIT'
        connection.commit()
    except psycopg.IntegrityError:
        report_db_failure('CONSTRAINT',phase)
        rollback()
        raise sqlite3.IntegrityError('Synthetic storage constraint conflict') from None
    except psycopg.Error as error:
        report_db_failure(classify_db_error(error,phase),phase)
        rollback()
        raise HTTPException(503,'시연 데이터베이스에 연결하거나 처리하지 못했습니다. 잠시 후 다시 시도해 주세요.') from None
    except BaseException:
        rollback()
        raise
    finally:
        if connection:
            with suppress(psycopg.Error):connection.close()
