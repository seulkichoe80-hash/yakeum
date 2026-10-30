"""Run only against an explicitly supplied disposable, loopback synthetic database."""
import os
from urllib.parse import urlsplit
import pytest
from backend.tests import test_dev_account as accounts,test_account_hira as hira,test_saved_deletion as deletion

URL=os.environ.get('YAKEUM_TEST_POSTGRES_URL')
pytestmark=pytest.mark.skipif(not URL,reason='Disposable PostgreSQL not configured; SQLite tests still run')


@pytest.fixture(autouse=True)
def disposable_postgres(monkeypatch):
    import psycopg
    url=urlsplit(URL)
    assert url.hostname in ('127.0.0.1','localhost') and url.path=='/yakeum_synthetic'
    # Refuse all real/cloud database selectors. Only this task's disposable DB is reset.
    with psycopg.connect(URL,sslmode='disable',autocommit=True) as c:
        c.execute('DROP SCHEMA IF EXISTS yakeum_demo CASCADE')
    for key,value in dict(YAKEUM_STORAGE_BACKEND='postgres',YAKEUM_DATABASE_URL=URL,
                          YAKEUM_PG_LOCAL_TEST='1',YAKEUM_DEV_ACCOUNT_ENABLED='1',
                          YAKEUM_APP_MODE='development',YAKEUM_DEV_ORIGIN='http://testserver',
                          YAKEUM_GEMINI_LIVE_ENABLED='0').items():monkeypatch.setenv(key,value)
    monkeypatch.delenv('YAKEUM_EXTERNAL_DEMO',raising=False)


ACCOUNT_CASES=[getattr(accounts,n) for n in [
 'test_persist_original_edited_confirmed_normalized_and_comparison_separately',
 'test_intake_selection_is_explicit_separate_and_server_attributed',
 'test_other_user_and_other_family_read_write_and_document_theft_blocked',
 'test_logout_invalidates_cookie_and_protected_endpoints',
 'test_session_expiry_and_csrf_origin_protection',
 'test_invalid_intake_record_and_forged_confirmation_are_rejected',
 'test_password_session_cookie_and_database_do_not_store_plain_password',
 'test_live_services_are_not_used_and_documents_expire',
 'test_login_rotates_session_and_old_session_cannot_be_replayed',
 'test_two_sessions_cannot_use_each_others_csrf',
 'test_fresh_python_process_can_read_saved_sqlite_state']]
HIRA_CASES=[getattr(hira,n) for n in [
 'test_hira_save_relogin_original_normalized_comparison_and_pending_preserved',
 'test_explicit_intake_only_changes_separate_state_and_never_confirms_source',
 'test_two_users_several_families_cannot_read_or_modify_each_others_runs',
 'test_photo_and_hira_storage_have_distinct_tables_lists_and_intake',
 'test_fake_official_lookup_only_and_csrf_enforced']]
DELETE_CASES=[v for n,v in vars(deletion).items() if n.startswith('test_') and callable(v) and v.__code__.co_argcount==0]


@pytest.mark.parametrize('case',ACCOUNT_CASES+HIRA_CASES+DELETE_CASES,ids=lambda f:f.__name__)
def test_existing_owned_storage_contract_on_postgres(case):case()


@pytest.mark.parametrize('problem',['failure','strength','repeat','empty'])
def test_hira_hold_and_executed_zero_on_postgres(problem):hira.test_hold_and_executed_zero_remain_distinct_after_storage(problem)


@pytest.mark.parametrize('confirmed,scenario',[(False,'single'),(True,'mixed'),(True,'unknown'),(True,'repeat'),(True,'failed')])
def test_unconfirmed_photo_cannot_be_saved_on_postgres(confirmed,scenario):accounts.test_unconfirmed_or_held_never_saved_as_confirmed(confirmed,scenario)


def test_duplicate_username_is_conflict_and_next_request_recovers():
    c=accounts.account()
    r=c.post('/api/dev-account/register',json={'username':'synthetic_a','password':accounts.PASSWORD})
    assert r.status_code==409
    assert c.get('/api/dev-account/me').status_code==200


@pytest.mark.parametrize('kind',['photo','hira'])
def test_postgres_delete_removes_matching_children_and_blocks_reappearance(kind):
    from backend.storage.local_db import database
    from uuid import uuid4
    c=accounts.account();f=accounts.family(c);base,run=deletion.seed(c,f,kind)
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
        # PostgreSQL's enforced FK constraints replace SQLite PRAGMA foreign_key_check.
        assert db.execute(f'SELECT count(*) FROM {child} c WHERE NOT EXISTS (SELECT 1 FROM {table} p WHERE p.id=c.run_id)').fetchone()[0]==0
        assert db.execute('SELECT count(*) FROM users').fetchone()[0]==1
        assert db.execute('SELECT count(*) FROM families').fetchone()[0]==1


@pytest.mark.parametrize('kind',['photo','hira'])
def test_postgres_delete_requires_ownership_session_csrf_and_origin(kind):
    deletion.test_delete_requires_owner_family_login_csrf_and_origin(kind)


@pytest.mark.parametrize('kind',['photo','hira'])
def test_postgres_delete_is_atomic_when_parent_delete_fails(kind):
    from backend.storage.local_db import database
    c=accounts.account();f=accounts.family(c);base,run=deletion.seed(c,f,kind)
    table='runs' if kind=='photo' else 'hira_runs'
    with database() as db:
        db.connection.execute("CREATE FUNCTION yakeum_demo.synthetic_reject_delete() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'synthetic rollback'; END $$")
        db.connection.execute(f'CREATE TRIGGER synthetic_reject BEFORE DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION yakeum_demo.synthetic_reject_delete()')
    assert c.delete(base+'/'+run).status_code==503
    value=c.get(base+'/'+run)
    assert value.status_code==200 and value.json()['intake_states']


@pytest.mark.parametrize('case_name',[
    'test_success_fixed_query_persisted_and_replayed_after_new_session',
    'test_simultaneous_requests_only_one_external_attempt',
    'test_process_crash_leaves_consumed_record_and_blocks_restart'])
def test_durable_admin_probe_on_disposable_postgres(monkeypatch,case_name):
    from backend.tests import test_mfds_admin
    from backend.api import mfds_admin
    monkeypatch.setenv('YAKEUM_MFDS_PROBE_ENABLED','1')
    monkeypatch.setenv('YAKEUM_MFDS_PROBE_ADMIN_USERNAME','synthetic_admin')
    monkeypatch.setenv('MFDS_API_KEY','SYNTHETIC-SECRET')
    monkeypatch.setattr(mfds_admin.probe,'fetch_xml',lambda *a:pytest.fail('live forbidden'))
    getattr(test_mfds_admin,case_name)(monkeypatch)


@pytest.mark.parametrize('kind',['photo','hira'])
def test_live_matching_snapshot_provenance_on_disposable_postgres(monkeypatch,kind):
    from backend.tests.test_live_mfds_matching import test_persistence_sources_and_other_owner_access
    monkeypatch.setenv('YAKEUM_MFDS_MATCH_ENABLED','1')
    monkeypatch.setenv('MFDS_API_KEY','SYNTHETIC-SECRET')
    test_persistence_sources_and_other_owner_access(monkeypatch,kind)
