"""Local synthetic-image upload flow. No live provider, database or authentication."""
from copy import deepcopy
from dataclasses import dataclass
from datetime import date
from io import BytesIO
import json
from pathlib import Path
from threading import Lock
from time import monotonic
from typing import Annotated, Literal
from uuid import UUID, uuid4
import warnings

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError
from pydantic import Field, StrictBool

from backend.api import photo_demo
from backend.services.extraction import ExtractionContext, adapt_provider_call

router = APIRouter(prefix='/api/local-demo/photo-uploads', tags=['Synthetic image upload only'])
VERSION = 'UPLOADED_PHOTO_V1'
MAX_BYTES = 10 * 1024 * 1024
MAX_PIXELS = 20_000_000
TTL_SECONDS = 15 * 60
MAX_DOCUMENTS = 128
FORMATS = {'PNG': ('image/png', {'.png'}), 'JPEG': ('image/jpeg', {'.jpg', '.jpeg'}),
           'WEBP': ('image/webp', {'.webp'})}
UploadScenario = Literal['single', 'multiple', 'missing', 'failed', 'repeat', 'unknown', 'mixed']
SourceType = Literal['MEDICINE_BAG', 'PRESCRIPTION', 'SUPPLEMENT']


@dataclass(frozen=True)
class Snapshot:
    document: photo_demo.DocumentInput
    family: str
    results: list[dict]
    expires: float


class SnapshotStore:
    def __init__(self):
        self._documents: dict[str, Snapshot] = {}
        self._lock = Lock()

    def _purge(self):
        now = monotonic()
        for key in list(self._documents):
            if self._documents[key].expires <= now:
                del self._documents[key]

    def put(self, value: Snapshot) -> str:
        with self._lock:
            self._purge()
            if len(self._documents) >= MAX_DOCUMENTS:
                raise HTTPException(503, '가상 자료 처리 공간이 가득 찼습니다. 잠시 후 다시 시도해 주세요.')
            token = str(uuid4())
            self._documents[token] = deepcopy(value)
            return token

    def get(self, token: UUID, family: UUID) -> Snapshot:
        with self._lock:
            self._purge()
            value = self._documents.get(str(token))
            if value is None or value.family != str(family):
                raise HTTPException(410, '자료가 만료되었거나 현재 가족의 자료가 아닙니다. 사진을 다시 등록해 주세요.')
            return deepcopy(value)


store = SnapshotStore()


def fake_response(image: bytes, mime: str, scenario: UploadScenario, source_type: str) -> str:
    """Injectable fake transport. It does not interpret pixels or import Gemini."""
    if scenario == 'failed':
        raise RuntimeError('Synthetic extraction failure')
    raw = json.loads(photo_demo._fixture('single' if scenario == 'mixed' else scenario))
    raw['document_type'] = source_type
    if scenario == 'mixed':
        raw['medications'].append({**deepcopy(raw['medications'][0]), 'dose_per_administration': '읽기불가'})
    return json.dumps(raw, ensure_ascii=False)


async def validated_image(file: UploadFile) -> tuple[bytes, str]:
    data = bytearray()
    while chunk := await file.read(64 * 1024):
        data.extend(chunk)
        if len(data) > MAX_BYTES:
            raise HTTPException(413, '사진은 10MB 이하로 선택해 주세요.')
    if not data:
        raise HTTPException(400, '내용이 없는 사진입니다. 다른 파일을 선택해 주세요.')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as image:
                expected = FORMATS.get(image.format)
                if not expected or Path(file.filename or '').suffix.lower() not in expected[1]:
                    raise HTTPException(415, 'PNG·JPEG·WebP 사진을 선택해 주세요. 파일 확장자와 실제 형식도 같아야 합니다.')
                if file.content_type != expected[0]:
                    raise HTTPException(415, '사진의 전송 형식이 실제 이미지와 다릅니다. 다른 사진을 선택해 주세요.')
                if image.width * image.height > MAX_PIXELS or getattr(image, 'n_frames', 1) != 1:
                    raise HTTPException(422, '2천만 화소 이하의 정지 사진을 선택해 주세요.')
                image.verify()
            # Verify then fully decode: headers alone do not prove a valid image.
            with Image.open(BytesIO(data)) as image:
                image.load()
    except HTTPException:
        raise
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise HTTPException(422, '사진을 읽을 수 없습니다. 손상되지 않은 PNG·JPEG·WebP로 다시 저장해 주세요.') from None
    return bytes(data), expected[0]


@router.post('/extract')
async def extract(
    family_member_id: Annotated[UUID, Form()],
    record_date: Annotated[date, Form()],
    source_type: Annotated[SourceType, Form()],
    file: Annotated[UploadFile, File()],
    scenario: Annotated[UploadScenario, Form()] = 'single',
):
    try:
        data, mime = await validated_image(file)
        document = photo_demo.DocumentInput(document_id=uuid4(), record_date=record_date,
                                             source_type=source_type, scenario='single')
        context = ExtractionContext(str(family_member_id), str(document.document_id), record_date.isoformat())
        results = adapt_provider_call(lambda: fake_response(data, mime, scenario, source_type), context)
        token = store.put(Snapshot(document, str(family_member_id), results, monotonic() + TTL_SECONDS))
        return {'response_version': VERSION, 'mode': 'LOCAL_MOCK', 'persisted': False,
                'document_id': str(document.document_id), 'upload_token': token,
                'expires_in_seconds': TTL_SECONDS, 'results': results}
    finally:
        await file.close()


class UploadBatch(photo_demo.LocalModel):
    upload_token: UUID
    reviews: list[photo_demo.Review] = Field(max_length=32)


class UploadProcess(photo_demo.LocalModel):
    family_member_id: UUID
    previous: UploadBatch
    current: UploadBatch
    normalization_confirmed: StrictBool = False


@router.post('/process')
def process(request: UploadProcess):
    snapshots = {side: store.get(getattr(request, side).upload_token, request.family_member_id)
                 for side in ('previous', 'current')}
    common = photo_demo.ProcessInput(
        family_member_id=request.family_member_id,
        normalization_confirmed=request.normalization_confirmed,
        **{side: photo_demo.Batch(**snap.document.model_dump(), reviews=getattr(request, side).reviews)
           for side, snap in snapshots.items()},
    )
    result = photo_demo.process_virtual(common, sources={side: snap.results for side, snap in snapshots.items()})
    return {'response_version': VERSION, **result}
