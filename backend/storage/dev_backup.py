"""Explicit synthetic-only SQLite backup/restore. Never overwrite an existing file."""
import argparse
from contextlib import closing
import os
from pathlib import Path
import sqlite3
from fastapi import HTTPException
from backend.storage.local_db import config


class BackupError(ValueError):
    pass


def outside_repository(value):
    path=Path(value)
    if not path.is_absolute(): raise BackupError('절대 경로를 지정해 주세요.')
    path=path.resolve()
    if path.is_relative_to(Path(__file__).resolve().parents[2]):
        raise BackupError('DB와 백업은 소스 저장소 밖에 보관해 주세요.')
    return path


def validate(db):
    if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok' or db.execute('PRAGMA foreign_key_check').fetchone():
        raise BackupError('SQLite 무결성 또는 참조 검사를 통과하지 못했습니다.')
    version=db.execute('PRAGMA user_version').fetchone()[0]
    if version not in (1,2): raise BackupError('지원하지 않는 백업 버전입니다.')
    tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    required={'users','sessions','families','documents','runs','intake','attempts'}
    if version==2: required|={'hira_runs','hira_intake'}
    if not required<=tables: raise BackupError('약이음 개발 DB 구조가 아닙니다.')


def copy_database(source,output,*,synthetic_only=False):
    config()  # Explicit development mode, never an implicit production operation.
    if not synthetic_only: raise BackupError('가상 데이터 전용임을 --synthetic-only로 확인해 주세요.')
    source=outside_repository(source);output=outside_repository(output)
    if source==output or output.exists(): raise BackupError('기존 DB/백업을 덮어쓸 수 없습니다. 새 출력 경로를 선택해 주세요.')
    if not source.is_file(): raise BackupError('원본 DB/백업 파일을 찾을 수 없습니다.')
    output.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    created=False
    try:
        # Exclusive creation also rejects a race with another writer.
        descriptor=os.open(output,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        os.close(descriptor);created=True
        with closing(sqlite3.connect(source.as_uri()+'?mode=ro',uri=True)) as src:
            validate(src)
            with closing(sqlite3.connect(output)) as dst:
                src.backup(dst)
                dst.execute('DELETE FROM sessions');dst.execute('DELETE FROM attempts');dst.commit()
                dst.execute('VACUUM')  # Compact live data; this is not a secure-erasure guarantee.
                validate(dst)
    except BaseException:
        if created: output.unlink(missing_ok=True)
        raise
    return output


def backup(output,*,synthetic_only=False):
    source=config()
    if source is None:raise BackupError('PostgreSQL은 SQLite 백업 명령을 사용할 수 없습니다.')
    return copy_database(source,output,synthetic_only=synthetic_only)


def restore(source,output,*,synthetic_only=False):
    return copy_database(source,output,synthetic_only=synthetic_only)


def main():
    parser=argparse.ArgumentParser(description='가상 데이터 전용 개발 DB 백업/새 파일 복원')
    parser.add_argument('operation',choices=['backup','restore'])
    parser.add_argument('--output',required=True)
    parser.add_argument('--source',help='restore 시 백업 파일 절대 경로')
    parser.add_argument('--synthetic-only',action='store_true')
    args=parser.parse_args()
    try:
        if args.operation=='backup': backup(args.output,synthetic_only=args.synthetic_only)
        elif args.source: restore(args.source,args.output,synthetic_only=args.synthetic_only)
        else: raise BackupError('restore에는 --source가 필요합니다.')
    except (BackupError,sqlite3.Error,OSError,HTTPException):
        parser.exit(1,'처리하지 못했습니다. 가상 데이터 여부·개발 설정·경로·파일 버전을 확인하세요. 기존 파일은 덮어쓰지 않습니다.\n')
    print('가상 데이터용 새 SQLite 파일 생성 및 무결성 검사 완료. 로그인 세션은 포함하지 않습니다.')


if __name__=='__main__': main()
