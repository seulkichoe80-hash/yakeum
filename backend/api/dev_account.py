"""Development-only accounts and owned snapshots. Synthetic medical data only."""
from datetime import date, datetime, timezone
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
from time import time
from typing import Annotated, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, Response, UploadFile
from pydantic import Field, StrictBool
from backend.storage.local_db import config, database
from backend.api import photo_demo, photo_upload
from backend.services.extraction import ExtractionContext, adapt_provider_call
from backend.services.reconciliation.current_intake import apply_user_verification

COOKIE='yakeum_dev_session'
SESSION_SECONDS=8*60*60
VERSION='DEV_ACCOUNT_V1'


def guard(request: Request):
    config()
    if request.method not in ('GET','HEAD','OPTIONS'):
        origin=os.environ.get('YAKEUM_DEV_ORIGIN','http://127.0.0.1:4192')
        if request.headers.get('origin') != origin:
            raise HTTPException(403, '허용된 개발 화면에서 다시 요청해 주세요.')


router=APIRouter(prefix='/api/dev-account',tags=['Development accounts only'],dependencies=[Depends(guard)])


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def password_hash(password, salt=None):
    salt=salt or secrets.token_hex(16)
    value=hashlib.scrypt(password.encode(),salt=bytes.fromhex(salt),n=16384,r=8,p=1,maxmem=64*1024*1024).hex()
    return f'scrypt${salt}${value}'


DUMMY_HASH=password_hash('synthetic-dummy-password',salt='00'*16)


def principal(request: Request):
    token=request.cookies.get(COOKIE,'')
    with database() as db:
        db.execute('DELETE FROM sessions WHERE expires<=?',(time(),))
        row=db.execute('SELECT s.*,u.username FROM sessions s JOIN users u ON u.id=s.user_id WHERE token_hash=?',(digest(token),)).fetchone()
        if not row:
            raise HTTPException(401,'로그인이 필요하거나 세션이 만료되었습니다.')
        value=dict(row)
    if request.method not in ('GET','HEAD','OPTIONS') and not hmac.compare_digest(request.headers.get('x-csrf-token',''),value['csrf']):
        raise HTTPException(403,'로그인 확인값이 다릅니다. 다시 로그인해 주세요.')
    return value


User=Annotated[dict,Depends(principal)]


def owned_family(db, family, user):
    row=db.execute('SELECT * FROM families WHERE id=? AND owner_id=?',(str(family),user['user_id'])).fetchone()
    if not row: raise HTTPException(404,'현재 계정의 가족 자료를 찾을 수 없습니다.')
    return row


def owned_run(db, family, run_id, user, saved=False):
    owned_family(db,family,user)
    row=db.execute('SELECT * FROM runs WHERE id=? AND family_id=?',(str(run_id),str(family))).fetchone()
    if not row or (saved and not row['saved']): raise HTTPException(404,'저장 자료를 찾을 수 없습니다.')
    return row


class Credentials(photo_demo.LocalModel):
    username: str=Field(pattern=r'^[a-z0-9_-]{3,40}$')
    password: str=Field(min_length=12,max_length=128)


def rate_limit(request, username):
    key=digest((request.client.host if request.client else '')+'|'+username)
    limited=False
    with database() as db:
        db.execute('DELETE FROM attempts WHERE expires<=?',(time(),))
        row=db.execute('SELECT count FROM attempts WHERE key=?',(key,)).fetchone()
        if row and row['count']>=10: limited=True
        else: db.execute('INSERT INTO attempts VALUES(?,1,?) ON CONFLICT(key) DO UPDATE SET count=count+1',(key,time()+600))
    if limited: raise HTTPException(429,'로그인 시도가 많습니다. 10분 후 다시 시도해 주세요.')


@router.post('/register',status_code=201)
def register(body: Credentials, request: Request):
    rate_limit(request,'register')
    value=password_hash(body.password)
    try:
        with database() as db:
            db.execute('INSERT INTO users VALUES(?,?,?)',(str(uuid4()),body.username,value))
    except sqlite3.IntegrityError:
        raise HTTPException(409,'이 아이디로 가입할 수 없습니다. 다른 가상 아이디를 사용해 주세요.') from None
    return {'created':True,'development_only':True}


@router.post('/login')
def login(body: Credentials, request: Request, response: Response):
    rate_limit(request,'login')  # per-client bound also covers unknown usernames
    with database() as db:
        row=db.execute('SELECT * FROM users WHERE username=?',(body.username,)).fetchone()
    stored=row['password_hash'] if row else DUMMY_HASH
    salt=stored.split('$')[1]
    valid=hmac.compare_digest(stored,password_hash(body.password,salt))
    if not row or not valid: raise HTTPException(401,'아이디 또는 비밀번호를 확인해 주세요.')
    token=secrets.token_urlsafe(32);csrf=secrets.token_urlsafe(32)
    with database() as db:
        old=request.cookies.get(COOKIE)
        if old: db.execute('DELETE FROM sessions WHERE token_hash=?',(digest(old),))
        db.execute('DELETE FROM sessions WHERE expires<=?',(time(),))
        db.execute('INSERT INTO sessions VALUES(?,?,?,?)',(digest(token),row['id'],csrf,time()+SESSION_SECONDS))
    response.set_cookie(COOKIE,token,httponly=True,samesite='strict',secure=os.environ.get('YAKEUM_DEV_COOKIE_SECURE')=='1',max_age=SESSION_SECONDS,path='/api/dev-account')
    return {'username':row['username'],'csrf_token':csrf,'development_only':True,'response_version':VERSION}


@router.get('/me')
def me(user: User):
    return {'username':user['username'],'csrf_token':user['csrf'],'development_only':True,'response_version':VERSION}


@router.post('/logout')
def logout(user: User,response: Response):
    with database() as db: db.execute('DELETE FROM sessions WHERE token_hash=?',(user['token_hash'],))
    response.delete_cookie(COOKIE,path='/api/dev-account',httponly=True,samesite='strict',secure=os.environ.get('YAKEUM_DEV_COOKIE_SECURE')=='1')
    return {'logged_out':True}


class FamilyInput(photo_demo.LocalModel):
    name: str=Field(min_length=1,max_length=60)


@router.get('/families')
def families(user: User):
    with database() as db:
        return {'families':[dict(r) for r in db.execute('SELECT id,name FROM families WHERE owner_id=? ORDER BY rowid',(user['user_id'],))]}


@router.post('/families',status_code=201)
def create_family(body: FamilyInput,user: User):
    name=body.name.strip()
    if not name: raise HTTPException(422,'가족 표시 이름을 입력해 주세요.')
    family=str(uuid4())
    with database() as db:
        if db.execute('SELECT count(*) FROM families WHERE owner_id=?',(user['user_id'],)).fetchone()[0]>=20:
            raise HTTPException(422,'개발 계정당 가족은 최대 20명입니다.')
        db.execute('INSERT INTO families VALUES(?,?,?)',(family,user['user_id'],name))
    return {'id':family,'name':name}


async def extract_document(family: UUID,user: User,file: Annotated[UploadFile,File()],record_date: Annotated[date,Form()],
                  source_type: Annotated[photo_upload.SourceType,Form()],scenario: Annotated[photo_upload.UploadScenario,Form()]='single', *, gemini=False):
    try:
        with database() as db: owned_family(db,family,user)
        data,mime=await photo_upload.validated_image(file)
        doc=photo_demo.DocumentInput(document_id=uuid4(),record_date=record_date,source_type=source_type,scenario='single')
        context=ExtractionContext(str(family),str(doc.document_id),record_date.isoformat())
        if gemini:
            from starlette.concurrency import run_in_threadpool
            from backend.api.gemini_bridge import extract_approved_image
            results=await run_in_threadpool(extract_approved_image,data,mime,context)
        else:
            results=adapt_provider_call(lambda:photo_upload.fake_response(data,mime,scenario,source_type),context)
        metadata=doc.model_dump(mode='json')
        if gemini: metadata['_extraction_source']='GEMINI'
        with database() as db:
            owned_family(db,family,user)
            db.execute('DELETE FROM documents WHERE expires<=?',(time(),))
            if db.execute('SELECT count(*) FROM documents WHERE family_id=?',(str(family),)).fetchone()[0]>=128:
                raise HTTPException(503,'임시 자료가 많습니다. 15분 후 다시 등록해 주세요.')
            db.execute('INSERT INTO documents VALUES(?,?,?,?,?)',(str(doc.document_id),str(family),json.dumps(metadata),json.dumps(results),time()+900))
        return {'response_version':VERSION,'development_only':True,'document_id':str(doc.document_id),'results':results,
                'extraction_source':'GEMINI' if gemini else 'MOCK','official_data_mode':'LOCAL_MOCK'}
    finally:
        await file.close()


@router.post('/families/{family}/photos/extract')
async def extract(family: UUID,user: User,file: Annotated[UploadFile,File()],record_date: Annotated[date,Form()],
                  source_type: Annotated[photo_upload.SourceType,Form()],scenario: Annotated[photo_upload.UploadScenario,Form()]='single'):
    return await extract_document(family,user,file,record_date,source_type,scenario)


@router.post('/families/{family}/photos/gemini-extract')
async def extract_gemini(family: UUID,user: User,file: Annotated[UploadFile,File()],record_date: Annotated[date,Form()],
                         source_type: Annotated[photo_upload.SourceType,Form()]):
    return await extract_document(family,user,file,record_date,source_type,gemini=True)


class AccountBatch(photo_demo.LocalModel):
    document_id: UUID
    reviews: list[photo_demo.Review]=Field(max_length=32)


class Processing(photo_demo.LocalModel):
    previous: AccountBatch
    current: AccountBatch
    normalization_confirmed: StrictBool=False


@router.post('/families/{family}/photos/process')
def process(family: UUID,body: Processing,user: User):
    sources={};batches={};extraction_sources={}
    with database() as db:
        owned_family(db,family,user)
        for side in ('previous','current'):
            batch=getattr(body,side)
            row=db.execute('SELECT * FROM documents WHERE id=? AND family_id=? AND expires>?',(str(batch.document_id),str(family),time())).fetchone()
            if not row: raise HTTPException(410,'현재 가족의 사진 자료가 없거나 만료되었습니다. 다시 등록해 주세요.')
            sources[side]=json.loads(row['originals'])
            metadata=json.loads(row['metadata'])
            extraction_sources[side]=metadata.pop('_extraction_source','MOCK')
            batches[side]=photo_demo.Batch(**metadata,reviews=batch.reviews)
    result=photo_demo.process_virtual(photo_demo.ProcessInput(family_member_id=family,normalization_confirmed=body.normalization_confirmed,**batches),sources=sources)
    if 'GEMINI' in extraction_sources.values():result['extraction_sources']=extraction_sources
    run_id=str(uuid4());created=datetime.now(timezone.utc).isoformat()
    with database() as db:
        owned_family(db,family,user)
        # Un-saved processing drafts expire; saved snapshots are never removed here.
        db.execute('DELETE FROM runs WHERE saved=0 AND created<?',(datetime.fromtimestamp(time()-86400,timezone.utc).isoformat(),))
        db.execute('INSERT INTO runs VALUES(?,?,?,?,0,?)',(run_id,str(family),body.model_dump_json(),json.dumps(result),created))
    return {'response_version':VERSION,'development_only':True,'run_id':run_id,'result':result}


class Choice(photo_demo.LocalModel):
    record_id: UUID
    choice: Literal['TAKING','NOT_TAKING','UNKNOWN']


class SaveInput(photo_demo.LocalModel):
    intake_confirmations: list[Choice]=Field(default_factory=list,max_length=64)


def confirm_intake(db,run,user,choices):
    result=json.loads(run['result'])
    initial={s['medication_record_id']:s for s in result['current_intake_states']}
    ids=[str(c.record_id) for c in choices]
    if len(ids)!=len(set(ids)) or any(i not in initial for i in ids):
        raise HTTPException(422,'해당 비교 결과의 복용 항목만 확인할 수 있습니다.')
    for state in initial.values():
        db.execute('INSERT OR IGNORE INTO intake VALUES(?,?,?)',(run['id'],state['medication_record_id'],json.dumps(state)))
    for c in choices:
        state=apply_user_verification(initial[str(c.record_id)],c.choice,family_member_id=run['family_id'],verified_by=user['user_id'],last_verified_at=datetime.now(timezone.utc).isoformat())
        db.execute('UPDATE intake SET state=? WHERE run_id=? AND record_id=?',(json.dumps(state),run['id'],str(c.record_id)))


@router.post('/families/{family}/runs/{run_id}/save')
def save(family: UUID,run_id: UUID,body: SaveInput,user: User):
    with database() as db:
        run=owned_run(db,family,run_id,user)
        if json.loads(run['result'])['stage']!='compared':
            raise HTTPException(409,'후보와 정규화 결과를 확인하고 비교를 마친 뒤 저장해 주세요. 보류 자료는 확인 완료로 저장하지 않습니다.')
        confirm_intake(db,run,user,body.intake_confirmations)
        db.execute('UPDATE runs SET saved=1 WHERE id=?',(str(run_id),))
    return {'saved':True,'run_id':str(run_id)}


@router.get('/families/{family}/runs')
def runs(family: UUID,user: User):
    with database() as db:
        owned_family(db,family,user)
        return {'runs':[dict(r) for r in db.execute('SELECT id,created FROM runs WHERE family_id=? AND saved=1 ORDER BY created DESC',(str(family),))]}


@router.get('/families/{family}/runs/{run_id}')
def detail(family: UUID,run_id: UUID,user: User):
    with database() as db:
        run=owned_run(db,family,run_id,user,saved=True)
        states=[json.loads(r['state']) for r in db.execute('SELECT state FROM intake WHERE run_id=?',(str(run_id),))]
    return {'response_version':VERSION,'development_only':True,'run_id':str(run_id),'family_member_id':str(family),
            'reviews':json.loads(run['reviews']),'result':json.loads(run['result']),'intake_states':states}


@router.patch('/families/{family}/runs/{run_id}/intake')
def verify(family: UUID,run_id: UUID,body: Choice,user: User):
    with database() as db:
        run=owned_run(db,family,run_id,user,saved=True)
        confirm_intake(db,run,user,[body])
    return {'updated':True}


@router.delete('/families/{family}/runs/{run_id}')
def delete_saved_photo(family: UUID,run_id: UUID,user: User):
    with database() as db:
        run=owned_run(db,family,run_id,user,saved=True)
        reviews=json.loads(run['reviews'])
        candidates={reviews[side]['document_id'] for side in ('previous','current')}
        db.execute('DELETE FROM intake WHERE run_id=?',(str(run_id),))
        db.execute('DELETE FROM runs WHERE id=?',(str(run_id),))
        # Documents can be shared by preview/final/other saved runs. Preserve references.
        referenced=set()
        for row in db.execute('SELECT reviews FROM runs WHERE family_id=?',(str(family),)):
            body=json.loads(row['reviews'])
            referenced.update(body[side]['document_id'] for side in ('previous','current'))
        for document in candidates-referenced:
            db.execute('DELETE FROM documents WHERE id=? AND family_id=?',(document,str(family)))
    return {'deleted':True,'source_type':'PHOTO','run_id':str(run_id)}
