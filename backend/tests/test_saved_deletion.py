"""Synthetic saved-result deletion, ownership and transaction consistency."""
import sqlite3
from uuid import uuid4
import pytest
from backend.tests.test_dev_account import environment, account, family, processed, save as save_photo
from backend.tests.test_account_hira import process as hira_process, saved as save_hira
from backend.storage.local_db import database


def seed(c,f,kind,held=False):
    if kind=='photo':
        r,_=processed(c,f);assert save_photo(c,f,r['run_id']).status_code==200
        base=f'/api/dev-account/families/{f}/runs';result=r['result']
    else:
        if held:
            from backend.tests.test_b_d_c_api import _row
            r=hira_process(c,f,current=[_row(1,'invalid',None,None)]).json()
        else:r=hira_process(c,f).json()
        save_hira(c,f,r['run_id']);base=f'/api/dev-account/families/{f}/hira-runs';result=r['result']
    if result['current_intake_states']:
        record=result['current_intake_states'][0]['medication_record_id']
        assert c.patch(base+'/'+r['run_id']+'/intake',json={'record_id':record,'choice':'TAKING'}).status_code==200
    return base,r['run_id']


@pytest.mark.parametrize('kind',['photo','hira'])
def test_delete_removes_saved_snapshot_intake_and_prevents_reappearance(kind):
    c=account();f=family(c);base,run=seed(c,f,kind)
    assert c.delete(base+'/'+run).status_code==200
    assert c.get(base).json()['runs']==[]
    assert c.get(base+'/'+run).status_code==404
    assert c.post(base+'/'+run+'/save',json={}).status_code==404
    assert c.patch(base+'/'+run+'/intake',json={'record_id':str(uuid4()),'choice':'TAKING'}).status_code==404
    assert c.delete(base+'/'+run).status_code==404
    with database() as db:
        table,child=('runs','intake') if kind=='photo' else ('hira_runs','hira_intake')
        assert db.execute(f'SELECT count(*) FROM {table} WHERE id=?',(run,)).fetchone()[0]==0
        assert db.execute(f'SELECT count(*) FROM {child} WHERE run_id=?',(run,)).fetchone()[0]==0
        assert db.execute('PRAGMA foreign_key_check').fetchall()==[]
        assert db.execute('SELECT count(*) FROM users').fetchone()[0]==1
        assert db.execute('SELECT count(*) FROM families').fetchone()[0]==1


@pytest.mark.parametrize('kind',['photo','hira'])
def test_delete_requires_owner_family_login_csrf_and_origin(kind):
    a=account();b=account('synthetic_b');fa=family(a);fa2=family(a,'가상 다른 가족');fb=family(b)
    base,run=seed(a,fa,kind);suffix='runs' if kind=='photo' else 'hira-runs'
    for c,f in [(b,fa),(b,fb),(a,fa2)]:
        assert c.delete(f'/api/dev-account/families/{f}/{suffix}/{run}').status_code==404
    csrf=a.headers.pop('X-CSRF-Token');assert a.delete(base+'/'+run).status_code==403
    a.headers['X-CSRF-Token']=csrf
    a.headers['Origin']='https://untrusted.invalid';assert a.delete(base+'/'+run).status_code==403
    a.headers['Origin']='http://testserver';assert a.get(base+'/'+run).status_code==200
    assert a.post('/api/dev-account/logout').status_code==200
    assert a.delete(base+'/'+run).status_code==401


def test_photo_and_hira_deletions_do_not_cross_sources_or_other_results():
    c=account();f=family(c)
    photo,p=seed(c,f,'photo');photo2,p2=seed(c,f,'photo');hira,h=seed(c,f,'hira');hira2,h2=seed(c,f,'hira',held=True)
    assert c.delete(photo+'/'+h).status_code==404
    assert c.delete(hira+'/'+p).status_code==404
    assert c.delete(photo+'/'+p).status_code==200
    assert c.get(photo2+'/'+p2).status_code==200
    assert c.get(hira+'/'+h).status_code==200
    assert c.delete(hira2+'/'+h2).status_code==200
    assert c.get(hira+'/'+h).status_code==200
    assert c.get(photo2+'/'+p2).status_code==200


def test_shared_photo_documents_preserved_until_last_referencing_run_deleted():
    c=account();f=family(c);first,body=processed(c,f)
    second=c.post(f'/api/dev-account/families/{f}/photos/process',json=body).json()
    for r in [first,second]:assert save_photo(c,f,r['run_id']).status_code==200
    root=f'/api/dev-account/families/{f}/runs/'
    assert c.delete(root+first['run_id']).status_code==200
    with database() as db:assert db.execute('SELECT count(*) FROM documents').fetchone()[0]==2
    assert c.get(root+second['run_id']).status_code==200
    assert c.delete(root+second['run_id']).status_code==200
    with database() as db:assert db.execute('SELECT count(*) FROM documents').fetchone()[0]==0


@pytest.mark.parametrize('kind',['photo','hira'])
def test_delete_transaction_rolls_back_children_when_parent_delete_fails(kind):
    c=account();f=family(c);base,run=seed(c,f,kind)
    parent,child=('runs','intake') if kind=='photo' else ('hira_runs','hira_intake')
    with database() as db:
        db.execute(f"CREATE TRIGGER fail_delete BEFORE DELETE ON {parent} BEGIN SELECT RAISE(ABORT,'synthetic rollback'); END")
    # TestClient raises the SQLite exception; verify atomic rollback, not success.
    with pytest.raises(sqlite3.IntegrityError):c.delete(base+'/'+run)
    with database() as db:
        assert db.execute(f'SELECT count(*) FROM {child} WHERE run_id=?',(run,)).fetchone()[0]==1
    assert c.get(base+'/'+run).status_code==200
