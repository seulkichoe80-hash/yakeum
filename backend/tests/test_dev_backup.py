"""Only synthetic DBs. Never overwrite an existing file or restore live sessions."""
import sqlite3
import pytest
from fastapi import HTTPException
from backend.tests.test_dev_account import environment, account, family
from backend.tests.test_saved_deletion import seed
from backend.storage.local_db import config, database
from backend.storage.dev_backup import backup, restore, BackupError


def test_backup_restore_preserves_both_sources_but_revokes_sessions(monkeypatch,tmp_path):
    c=account();f=family(c);photo,p=seed(c,f,'photo');hira,h=seed(c,f,'hira')
    before={path:c.get(path).json() for path in [photo+'/'+p,hira+'/'+h]}
    source=config();copy=backup(tmp_path/'synthetic-backup.sqlite3',synthetic_only=True)
    assert c.get('/api/dev-account/me').status_code==200  # source session remains valid
    with sqlite3.connect(copy) as db:
        assert db.execute('SELECT count(*) FROM sessions').fetchone()[0]==0
        assert db.execute('SELECT count(*) FROM attempts').fetchone()[0]==0
    restored=restore(copy,tmp_path/'synthetic-restored.sqlite3',synthetic_only=True)
    assert restored.stat().st_mode & 0o777==0o600
    monkeypatch.setenv('YAKEUM_DEV_DB_PATH',str(restored))
    assert c.get('/api/dev-account/me').status_code==401
    from backend.tests.test_dev_account import PASSWORD
    login=c.post('/api/dev-account/login',json={'username':'synthetic_a','password':PASSWORD})
    assert login.status_code==200;c.headers['X-CSRF-Token']=login.json()['csrf_token']
    assert all(c.get(path).json()==value for path,value in before.items())
    assert source.exists() and copy.exists()


def test_post_delete_backup_does_not_restore_deleted_result_but_old_backup_can(tmp_path):
    c=account();f=family(c);root,run=seed(c,f,'hira')
    old=backup(tmp_path/'before.sqlite3',synthetic_only=True)
    assert c.delete(root+'/'+run).status_code==200
    new=backup(tmp_path/'after.sqlite3',synthetic_only=True)
    for source,expected,name in [(old,1,'restore-old.sqlite3'),(new,0,'restore-new.sqlite3')]:
        output=restore(source,tmp_path/name,synthetic_only=True)
        with sqlite3.connect(output) as db:assert db.execute('SELECT count(*) FROM hira_runs').fetchone()[0]==expected
    assert c.get(root+'/'+run).status_code==404  # restore never switches or overwrites active DB


def test_backup_requires_explicit_synthetic_flag_and_new_external_output(tmp_path):
    c=account();family(c)
    with pytest.raises(BackupError):backup(tmp_path/'no-flag.sqlite3')
    with pytest.raises(BackupError):backup(config(),synthetic_only=True)
    output=backup(tmp_path/'existing.sqlite3',synthetic_only=True);before=output.read_bytes()
    with pytest.raises(BackupError):backup(output,synthetic_only=True)
    assert output.read_bytes()==before
    with pytest.raises(BackupError):backup('relative.sqlite3',synthetic_only=True)
    from pathlib import Path
    with pytest.raises(BackupError):backup(Path(__file__).resolve().parents[2]/'unsafe.sqlite3',synthetic_only=True)


def test_bad_backup_rejected_without_creating_or_overwriting_output(tmp_path):
    account();bad=tmp_path/'bad.sqlite3';bad.write_bytes(b'not SQLite')
    output=tmp_path/'output.sqlite3'
    with pytest.raises(sqlite3.Error):restore(bad,output,synthetic_only=True)
    assert not output.exists()
    with sqlite3.connect(tmp_path/'other.sqlite3') as db:db.execute('PRAGMA user_version=999')
    with pytest.raises(BackupError):restore(tmp_path/'other.sqlite3',output,synthetic_only=True)
    assert not output.exists()


def test_production_mode_refuses_backup(monkeypatch,tmp_path):
    account();monkeypatch.setenv('YAKEUM_APP_MODE','production')
    with pytest.raises(HTTPException):backup(tmp_path/'no.sqlite3',synthetic_only=True)
