# TASK A Gemini 이미지 추출

실행 기준은 `backend/services/extraction/`이며 이전 `task-a/`와
`backend/services/extraction/test.py`는 참고용 실험 코드입니다.
현재 작업 브랜치는 `feature/ai-extraction`입니다.

## 공통 호출 경로

`backend.api.extraction_provider.extract_image_candidates(image_bytes, mime_type, context)`
→ 재시도 없는 SDK 호출 → 기존 parser → 기존 adapter → 제품별 ExtractionResult 목록

`ExtractionContext(family_member_id, source_document_id, record_date)`는 호출자가
제공합니다. AI가 가족 ID나 공식 ID를 생성하지 않습니다. 공통 함수는 파일을
저장하거나 원문을 기록하지 않습니다. B 정규화·D 비교·C 화면 연결 시 이 함수를
사용하며 이전 A 전용 `extract_medicine_info`의 반환값과 혼용하지 않습니다.
이전 함수는 호환용으로 남겼고 같은 SDK 전송을 사용합니다.

공통 adapter·parser·config·models·prompt와 provider는 통합본
`9302f95f562262ef34e720c8decc3cf1864b9b6f`에서 필요한 파일만 재사용했습니다.
provider의 공개 인자는 그대로이며 전송 부분만 A의 `sdk.py`에 위임합니다.
단일 모델과 단일 HTTP 요청 예산, 60초 제한, JSON 응답 요청을 두 호출 경로에
동일하게 적용합니다. B/C/D 구현이나 공통 Schema/API 문서는 변경하지 않습니다.

## 설치와 오프라인 검사

현재 PC에서 기존 .venv/venv는 다른 계정의 Python 경로를 가리켰습니다.
원본을 보존하고 `venv/task-a-runtime`을 만들었습니다. 다른 PC에서는 사용 가능한
Python으로 새 프로젝트 가상환경을 준비하세요. 전역 설치는 필요하지 않습니다.

```powershell
.\venv\task-a-runtime\Scripts\python.exe -m pip install -r backend/services/extraction/requirements.txt
.\venv\task-a-runtime\Scripts\python.exe -m unittest -v backend.tests.test_extraction_contract backend.tests.test_extraction_provider backend.tests.test_extraction_sdk backend.services.extraction.test_offline
```

31개의 독립 테스트가 있습니다. SDK 테스트는 실제 고정 버전 SDK와 메모리 내
HTTPX 전송을 사용하며 외부 네트워크를 호출하지 않습니다. 503 오류에도 전송이
1회인 것을 확인합니다. 가상 provider 테스트는 실제 SDK가 없어도 실행되지만
`test_extraction_sdk`는 requirements 설치가 필요합니다.

## 로컬 설정과 수동 실행

환경변수 이름은 `GEMINI_API_KEY`, `YAKEUM_GEMINI_MODEL`입니다.
모델 기본값과 자동 모델 전환은 없습니다. 계정에서 사용 가능한 이미지 입력
모델을 지정합니다. 2026-10-22에는 계정 목록과 Google 공식 문서에서
`gemini-3.5-flash-lite`를 확인해 1회 검증에 사용했습니다.

config와 import는 .env를 자동으로 읽지 않습니다. 수동 도구에만
`--env-file .env`를 명시할 수 있습니다. 기존 프로세스 환경변수가 우선하며
dotenv 값의 변수 보간은 끕니다. .env가 Git에서 제외되는지 먼저 확인하세요.
키를 채팅·코드·명령 이력에 입력하거나 설정 파일을 출력하지 마세요.

```powershell
git check-ignore .env
$env:YAKEUM_GEMINI_MODEL = 'gemini-3.5-flash-lite'
.\venv\task-a-runtime\Scripts\python.exe -m backend.services.extraction.scripts.run_image --image venv/task-a-artifacts/synthetic_medicine_bag.png --env-file .env --family-member-id 00000000-0000-4000-8000-000000000001 --source-document-id synthetic-medicine-bag-20261022 --record-date 2026-10-22 --synthetic-input
```

위 명령은 설정 유무·크기·형식만 확인하며 외부 요청은 0회입니다.
새 실제 호출을 별도로 승인받은 경우에만 `--allow-live`를 추가합니다.
수동 도구는 .png/.jpg/.jpeg/.webp, 0바이트 초과 10MiB 이하를 허용합니다.
입력이 합성 자료라는 확인과 유효한 호출자 ID·날짜가 필수입니다.
출력에는 제품 후보와 경고·정제된 오류·실제 HTTP 요청 시작 횟수만 표시합니다.
결과가 SUCCESS여도 `user_confirmed=false`이며 사용자 확인이 필요합니다.

## 가상 이미지와 검증 범위

`scripts/make_synthetic_image.ps1`은 Windows의 System.Drawing과 맑은 고딕으로
개인정보가 없는 테스트 약봉투를 만듭니다. 기본 출력은 Git 제외 경로
`venv/task-a-artifacts/synthetic_medicine_bag.png`입니다. PC 실행 정책에 따라
스크립트 파일 실행이 차단될 수 있습니다. 이번 검증에서는 정책을 변경하지 않고
동일한 이미지 생성 명령을 콘솔에서 직접 실행했습니다.

- 가상제품A 100mg: 가상성분A 100mg, 1회 1정, 하루 2회, 3일
- 가상제품B 복합정: 가상성분B 25mg + 가상성분C 50mg, 1회 2정, 하루 1회, 7일

원본 PNG·실행 마커·응답 결과 JSON은 로컬 Git 제외 경로에만 있습니다.
실제 호출은 이 이미지 1장으로만 확인했습니다. 처방전·건강기능식품·흐린 이미지,
다른 계정·모델, B/C/D 전체 앱 E2E·업로드·DB·로그인·배포는 미검증입니다.
AI confidence는 모델의 반환값이며 인식 정확도 통계나 의학적 확신도가 아닙니다.

## 근거

- [Google 모델 입력 지원](https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash-lite)
- [Google SDK HTTP 및 재시도 옵션](https://googleapis.github.io/python-genai/genai.html)
