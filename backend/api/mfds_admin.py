"""Opt-in administrator-only, durable one-shot MFDS diagnostic. Not live matching."""
from datetime import datetime, timezone
import hmac
import json
import os
from pathlib import Path
import re
import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, ConfigDict, StrictBool

from backend.api.dev_account import User, guard
from backend.storage.local_db import database
from backend.services.mfds import probe

SLOT = 'mfds-render-v1'  # Fixed forever for this feature; never rotate/reset on deployment.
SCHEMA = '''CREATE TABLE IF NOT EXISTS mfds_probe_attempts(
    slot TEXT PRIMARY KEY,
    started TEXT NOT NULL,
    result TEXT
)'''


def administrator(user: User):
    if os.environ.get('YAKEUM_MFDS_PROBE_ENABLED') != '1':
        raise HTTPException(404, '검증 기능이 꺼져 있습니다.')
    name = os.environ.get('YAKEUM_MFDS_PROBE_ADMIN_USERNAME', '')
    if not re.fullmatch(r'[a-z0-9_-]{3,40}', name) or not hmac.compare_digest(user['username'], name):
        raise HTTPException(403, '서버에서 지정한 관리자만 사용할 수 있습니다.')
    if os.environ.get('YAKEUM_EXTERNAL_DEMO') == '1' and os.environ.get('YAKEUM_STORAGE_BACKEND') != 'postgres':
        raise HTTPException(503, '외부 시연 검증은 기존 PostgreSQL 영속 저장 설정이 필요합니다.')
    return user


Admin = Annotated[dict, Depends(administrator)]
router = APIRouter(prefix='/api/dev-account/admin/mfds-probe',
                   tags=['Temporary administrator diagnostics'], dependencies=[Depends(guard)])


def snapshot(row):
    return {'response_version': 'ADMIN_MFDS_PROBE_V1',
            'state': 'UNUSED' if row is None else 'FINISHED' if row['result'] is not None else 'STARTED_OR_UNCERTAIN',
            'consumed': row is not None,
            'started_at': row['started'] if row else None,
            'result': json.loads(row['result']) if row and row['result'] is not None else None}


@router.get('/status')
def status(user: Admin):
    with database() as db:
        db.execute(SCHEMA)
        row = db.execute('SELECT * FROM mfds_probe_attempts WHERE slot=?', (SLOT,)).fetchone()
    return snapshot(row)


class ExecuteInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    confirm: StrictBool


@router.post('/execute')
def execute(body: ExecuteInput, user: Admin):
    if not body.confirm:
        raise HTTPException(422, '최대 1회 실제 조회에 명시적으로 동의해 주세요.')
    key = os.environ.get('MFDS_API_KEY', '').strip()
    if not key:
        raise HTTPException(503, 'Render 서버의 MFDS_API_KEY 비공개 설정이 필요합니다.')
    if re.search(r'%[0-9a-fA-F]{2}', key):
        raise HTTPException(503, 'Decoding 인증키 설정을 확인해 주세요. 키를 화면에 입력하지 마세요.')
    # database() serializes SQLite/PG transactions. COMMIT must finish before I/O.
    # If commit outcome is unclear, this function never starts an HTTP request.
    with database() as db:
        db.execute(SCHEMA)
        row = db.execute('SELECT * FROM mfds_probe_attempts WHERE slot=?', (SLOT,)).fetchone()
        if row is not None:
            return snapshot(row)  # Read-only replay, including indeterminate attempts.
        started = datetime.now(timezone.utc).isoformat()
        db.execute('INSERT INTO mfds_probe_attempts(slot,started,result) VALUES(?,?,NULL)', (SLOT, started))
    # No DB lock/transaction is held during network I/O. A process crash leaves
    # NULL result permanently consumed. There is deliberately no retry/reset API.
    result = probe.live_result(key)
    with database() as db:
        db.execute('UPDATE mfds_probe_attempts SET result=? WHERE slot=? AND result IS NULL',
                   (json.dumps(result, ensure_ascii=False), SLOT))
        row = db.execute('SELECT * FROM mfds_probe_attempts WHERE slot=?', (SLOT,)).fetchone()
    return snapshot(row)


@router.get('/view', response_class=HTMLResponse)
def view(user: Admin):
    nonce = secrets.token_urlsafe(24)
    html = Path(__file__).with_name('mfds_admin.html').read_text().replace('__NONCE__', nonce)
    return HTMLResponse(html, headers={
        'Cache-Control': 'no-store', 'X-Frame-Options': 'DENY',
        'Content-Security-Policy': "default-src 'none'; script-src 'nonce-" + nonce + "'; style-src 'nonce-" + nonce + "'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"})
