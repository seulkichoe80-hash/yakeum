"""Opt-in, single-process live request gate. No API calls at import time."""
import os
from threading import Lock
from fastapi import HTTPException
from backend.services.extraction.config import GeminiSettings, GeminiConfigurationError
from backend.api.extraction_provider import extract_image_candidates

_lock=Lock()
_attempts=0


def extract_approved_image(data,mime,context):
    global _attempts
    if os.environ.get('YAKEUM_GEMINI_LIVE_ENABLED')!='1':
        raise HTTPException(503,'Gemini 호출이 비활성화되어 있습니다. 승인 후 서버 설정을 확인하세요. Mock으로 자동 대체하지 않습니다.')
    try:
        GeminiSettings.from_environment()
        limit=int(os.environ.get('YAKEUM_GEMINI_LIVE_MAX_REQUESTS','1'))
        if not 1<=limit<=10:raise ValueError()
    except (GeminiConfigurationError,ValueError):
        raise HTTPException(503,'Gemini 키·모델·호출 한도 설정이 필요합니다. 키를 화면이나 로그에 입력하지 마세요.') from None
    with _lock:
        if _attempts>=limit:
            raise HTTPException(429,'승인용 서버 호출 한도를 사용했습니다. 추가 호출 전 승인과 설정을 다시 확인하세요.')
        _attempts+=1  # Failed/timeout attempts also consume budget. Never retry automatically.
    return extract_image_candidates(data,mime,context)
