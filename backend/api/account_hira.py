"""Owned HIRA v2 snapshots, separate from photo runs. Development SQLite only."""
from datetime import datetime, timezone
import json
from typing import Annotated
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from backend.api.dev_account import User, guard, owned_family, SaveInput, Choice
from backend.storage.local_db import database
from backend.services.reconciliation.current_intake import apply_user_verification

VERSION='DEV_ACCOUNT_HIRA_V1'
router=APIRouter(prefix='/api/dev-account/families/{family}',tags=['Development HIRA storage'],dependencies=[Depends(guard)])


def owned_hira(db,family,run_id,user,saved=False):
    owned_family(db,family,user)
    run=db.execute('SELECT * FROM hira_runs WHERE id=? AND family_id=?',(str(run_id),str(family))).fetchone()
    if run is None or (saved and not run['saved']):
        raise HTTPException(404,'현재 가족의 HIRA 저장 자료를 찾을 수 없습니다.')
    return run


@router.post('/hira/process')
async def process(family: UUID,user: User,previous_file: Annotated[UploadFile,File()],current_file: Annotated[UploadFile,File()]):
    try:
        with database() as db: owned_family(db,family,user)
        # Lazy import reuses existing bounded upload/parser/v2 validation, without a cycle.
        from backend.api.main import _reconcile_hira_files
        result=(await _reconcile_hira_files(family,previous_file,current_file,version=2)).model_dump(mode='json')
        run_id=str(uuid4());now=datetime.now(timezone.utc)
        with database() as db:
            owned_family(db,family,user)
            db.execute('DELETE FROM hira_runs WHERE saved=0 AND created<?',
                       (datetime.fromtimestamp(now.timestamp()-86400,timezone.utc).isoformat(),))
            db.execute('INSERT INTO hira_runs VALUES(?,?,?,0,?)',(run_id,str(family),json.dumps(result),now.isoformat()))
        return {'response_version':VERSION,'development_only':True,'source_type':'HIRA',
                'run_id':run_id,'family_member_id':str(family),'saved':False,'result':result,
                'intake_states':result['current_intake_states']}
    finally:
        await previous_file.close()
        await current_file.close()


def write_choices(db,run,user,choices):
    result=json.loads(run['result'])
    initial={state['medication_record_id']:state for state in result['current_intake_states']}
    ids=[str(choice.record_id) for choice in choices]
    if len(ids)!=len(set(ids)) or any(id not in initial for id in ids):
        raise HTTPException(422,'실제로 비교한 이 HIRA 결과의 복용 항목만 확인할 수 있습니다.')
    for state in initial.values():
        db.execute('INSERT OR IGNORE INTO hira_intake VALUES(?,?,?)',(run['id'],state['medication_record_id'],json.dumps(state)))
    for choice in choices:
        state=apply_user_verification(initial[str(choice.record_id)],choice.choice,
                family_member_id=run['family_id'],verified_by=user['user_id'],last_verified_at=datetime.now(timezone.utc).isoformat())
        db.execute('UPDATE hira_intake SET state=? WHERE run_id=? AND record_id=?',
                   (json.dumps(state),run['id'],str(choice.record_id)))


@router.post('/hira-runs/{run_id}/save')
def save(family: UUID,run_id: UUID,body: SaveInput,user: User):
    with database() as db:
        run=owned_hira(db,family,run_id,user)
        write_choices(db,run,user,body.intake_confirmations)
        db.execute('UPDATE hira_runs SET saved=1 WHERE id=?',(str(run_id),))
    return {'saved':True,'source_type':'HIRA','run_id':str(run_id)}


@router.get('/hira-runs')
def listing(family: UUID,user: User):
    with database() as db:
        owned_family(db,family,user)
        return {'source_type':'HIRA','runs':[dict(r) for r in db.execute(
            'SELECT id,created FROM hira_runs WHERE family_id=? AND saved=1 ORDER BY created DESC',(str(family),))]}


@router.get('/hira-runs/{run_id}')
def detail(family: UUID,run_id: UUID,user: User):
    with database() as db:
        run=owned_hira(db,family,run_id,user,saved=True)
        states=[json.loads(r['state']) for r in db.execute('SELECT state FROM hira_intake WHERE run_id=?',(str(run_id),))]
    return {'response_version':VERSION,'development_only':True,'source_type':'HIRA','saved':True,
            'run_id':str(run_id),'family_member_id':str(family),'result':json.loads(run['result']),'intake_states':states}


@router.patch('/hira-runs/{run_id}/intake')
def verify(family: UUID,run_id: UUID,body: Choice,user: User):
    with database() as db:
        run=owned_hira(db,family,run_id,user,saved=True)
        write_choices(db,run,user,[body])
    return {'updated':True}
