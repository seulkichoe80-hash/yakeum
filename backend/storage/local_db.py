"""Explicitly enabled development SQLite storage; no operational deployment defaults."""
from contextlib import contextmanager
import os
from pathlib import Path
import sqlite3
from fastapi import HTTPException

SCHEMA = '''
CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS sessions(token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id), csrf TEXT NOT NULL, expires REAL NOT NULL);
CREATE TABLE IF NOT EXISTS families(id TEXT PRIMARY KEY, owner_id TEXT NOT NULL REFERENCES users(id), name TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS documents(id TEXT PRIMARY KEY, family_id TEXT NOT NULL REFERENCES families(id), metadata TEXT NOT NULL, originals TEXT NOT NULL, expires REAL NOT NULL);
CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY, family_id TEXT NOT NULL REFERENCES families(id), reviews TEXT NOT NULL, result TEXT NOT NULL, saved INTEGER NOT NULL DEFAULT 0, created TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS intake(run_id TEXT NOT NULL REFERENCES runs(id), record_id TEXT NOT NULL, state TEXT NOT NULL, PRIMARY KEY(run_id,record_id));
CREATE TABLE IF NOT EXISTS attempts(key TEXT PRIMARY KEY, count INTEGER NOT NULL, expires REAL NOT NULL);
'''


def config():
    if os.environ.get('YAKEUM_DEV_ACCOUNT_ENABLED') != '1' or os.environ.get('YAKEUM_APP_MODE', 'development') != 'development':
        raise HTTPException(503, '개발용 로그인·저장이 꺼져 있습니다. 운영 인증 기능은 아직 제공하지 않습니다.')
    location = os.environ.get('YAKEUM_DEV_DB_PATH', '')
    if not location or not Path(location).is_absolute():
        raise HTTPException(503, '개발용 DB의 절대 경로 설정이 필요합니다.')
    path = Path(location).resolve()
    if path.is_relative_to(Path(__file__).resolve().parents[2]):
        raise HTTPException(503, '개발 DB는 소스 저장소 밖의 절대 경로에 보관해 주세요.')
    return path


@contextmanager
def database():
    path = config()
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    # SQLite creates no credential-bearing config file. Keep DB outside Git.
    connection = sqlite3.connect(path, timeout=10)
    path.chmod(0o600)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute('PRAGMA foreign_keys=ON')
        version = connection.execute('PRAGMA user_version').fetchone()[0]
        if version not in (0, 1):
            raise HTTPException(503, '지원하지 않는 개발 DB 버전입니다. 이전 파일을 보존하고 설정을 확인해 주세요.')
        connection.executescript(SCHEMA)
        connection.execute('PRAGMA user_version=1')
        connection.execute('BEGIN IMMEDIATE')
        yield connection
        connection.commit()
    except BaseException:
        connection.rollback()
        raise
    finally:
        connection.close()
