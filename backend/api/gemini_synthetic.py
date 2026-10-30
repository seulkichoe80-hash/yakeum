"""Fixed synthetic fixture only; persistent two-slot administrator validation.

No reset, retry, arbitrary image, or general live-mode exemption.
"""
from datetime import datetime, timezone
import hashlib
import hmac
import os
import re
from fastapi import HTTPException
from backend.storage.local_db import database
from backend.services.extraction.config import GeminiSettings, GeminiConfigurationError
from backend.api.extraction_provider import extract_image_candidates

IMAGE_SHA256 = 'c70bba4ae9c8f1ba2e671544dd7b5f76b4ec3d17a81b644ed81263dca7e55060'
SCHEMA = '''CREATE TABLE IF NOT EXISTS gemini_synthetic_attempts(
 slot TEXT PRIMARY KEY, started TEXT NOT NULL, finished TEXT
)'''


def administrator(user):
    if os.environ.get('YAKEUM_GEMINI_SYNTHETIC_ENABLED') != '1':
        raise HTTPException(404, '합성 이미지 검증이 꺼져 있습니다.')
    name = os.environ.get('YAKEUM_GEMINI_SYNTHETIC_ADMIN_USERNAME', '')
    if not re.fullmatch(r'[a-z0-9_-]{3,40}', name) or not hmac.compare_digest(user['username'], name):
        raise HTTPException(403, '서버에서 지정한 관리자만 합성 이미지 검증을 실행할 수 있습니다.')
    if os.environ.get('YAKEUM_EXTERNAL_DEMO') == '1' and os.environ.get('YAKEUM_STORAGE_BACKEND') != 'postgres':
        raise HTTPException(503, '외부 합성 검증은 PostgreSQL 영속 저장이 필요합니다.')


def extract(data, mime, context, user, consent, side):
    administrator(user)
    if not consent or side not in ('previous', 'current'):
        raise HTTPException(422, '승인된 합성 이미지의 이전/현재 각 1회 호출에 명시적으로 동의해 주세요.')
    if mime != 'image/png' or not hmac.compare_digest(hashlib.sha256(data).hexdigest(), IMAGE_SHA256):
        raise HTTPException(422, '배포된 원본 합성 PNG만 허용합니다. 편집·재저장한 이미지나 실제 자료는 사용할 수 없습니다.')
    try:
        GeminiSettings.from_environment()
    except GeminiConfigurationError:
        raise HTTPException(503, 'Gemini 서버 키·모델 설정을 확인하세요.') from None
    slot = 'render-synthetic-bag-v1:' + side  # Fixed globally, never per user/family/release.
    with database() as db:
        db.execute(SCHEMA)
        if db.execute('SELECT slot FROM gemini_synthetic_attempts WHERE slot=?', (slot,)).fetchone():
            raise HTTPException(409, '이미 시작한 합성 검증입니다. 결과가 불명확해도 다시 호출하지 않습니다.')
        db.execute('INSERT INTO gemini_synthetic_attempts(slot,started,finished) VALUES(?,?,NULL)',
                   (slot, datetime.now(timezone.utc).isoformat()))
    # Transaction has committed before external I/O. Crash/timeout consumes slot.
    # Existing SDK enforces one HTTP start and zero automatic retries.
    results = extract_image_candidates(data, mime, context)
    with database() as db:
        db.execute('UPDATE gemini_synthetic_attempts SET finished=? WHERE slot=?',
                   (datetime.now(timezone.utc).isoformat(), slot))
    return results
