# TASK D — A 원격 SDK 선별 반영·오프라인 연결 검증

2026-10-26 (한국 시간). D 통합 브랜치에서만 작업했다.

## 시작 상태와 정확한 출처

- D 시작: `codex/task-d-weekly-integration` / `9302f95f562262ef34e720c8decc3cf1864b9b6f`, clean.
- fetch/원격 재확인 A: `feature/ai-extraction` / `2787918765e7e9724a1d2f1215b69e6296801a86`.
- A 완료 보고의 구현 SHA는 `67fbc1d7145d579a5650c8129adf2508f9e3e52b`이며,
  이번 반영 출처는 보고서 포함 원격 tip `2787918`이다. 둘을 혼동하지 않는다.
- A 로컬 보완 `d85e537575923c2f516fa14154908df631735c00`은 branch 참조 그대로 보존한다.
  checkout/수정/commit/push/cherry-pick하지 않았다. A/B/C branch는 읽기 전용 검토다.

## 파일별 선별 반영

아래 다섯 파일은 A 원격 tip의 바이트와 동일하다.

| 파일 | 필요성 |
| --- | --- |
| backend/api/extraction_provider.py | 기존 공개 함수/결과 계약 유지, 전송만 request_image로 위임 |
| backend/services/extraction/sdk.py | 모델 명시, JSON 응답, 60초 timeout, SDK retry attempts=1(재시도 0), 요청 예산 1회 |
| backend/services/extraction/requirements.txt | google-genai==2.30.1, python-dotenv==1.2.4 |
| backend/services/extraction/scripts/run_image.py | SDK 테스트가 의존하는 명시적 수동 사전검사 도구. 실제 실행은 별도 --allow-live 필요 |
| backend/tests/test_extraction_sdk.py | SDK 메모리 전송·503 무재시도·빈 응답·수동 도구 보호의 기존 5개 검사 |

D 추가 변경:

- backend/requirements.txt: extraction requirements 포함. 설치 누락/버전 중복 선언 방지.
- backend/tests/test_a_provider_integration.py: 실제 SDK + HTTPX 가짜 전송과 D 검토/B/D/
  복용 확인 연결, 실패 후 무잔존, 출처 ID, A 알려진 문제 관찰/엄격한 xfail.
- frontend/tests/photo-hira-integration.browser.cjs: 실패 요청 뒤 이전 비교/사용자 복용 확인
  제거와 정상 재시도 초기값을 확인하는 브라우저 회귀 1개 그룹 추가. 앱 화면 코드는 그대로.
- extraction README와 이 보고서: 현재 SDK/Mock 범위 및 미통합 항목 설명.

동일한 공통 adapter/parser/models/config/prompt/__init__와 공통 추출 테스트는
A와 실제 diff가 없음을 확인했으며 복사/수정하지 않았다. B 정규화, D 엔진/복용 상태,
HIRA v1/v2 모델·원본 출처·전체 보류 계약도 변경하지 않는다.

이전 `task-a/`, extraction.py/schema.py/test.py/test_offline.py, 사진/동영상, 모델
목록 도구, 합성 이미지 생성 PowerShell은 반영하지 않는다. A 최초 31개 중 legacy
전용 6개는 해당 코드가 D에 없으므로 실행하지 않았다. 공통 20개 + SDK 5개는 실행한다.

## D 연결 검사 방식

운영 코드의 photo_demo.extract_virtual은 계속 가상 fixture → 공통 adapter다.
새 upload API·provider 선택 UI·실제 이미지 전송을 추가하지 않는다.

검사에서만 동일한 fixture JSON을 실제 genai SDK의 **HTTPX MockTransport**로 반환해
`extract_image_candidates → 공통 adapter → 후보 수정/내용 확인 → B 정식 정규화
→ D 비교 → 별도 복용 확인 → 결과/타임라인`에 연결했다. 모델/API key는 fake 값이다.
SDK 모의 전송도 요청 hook의 1회 예산·60초·재시도 0을 검사한다.

backend integration test는 patch로만 이 source를 주입한다. 브라우저는 `/tmp`에
아래 wrapper를 만든 별도 로컬 검사 프로세스를 사용했다. 기존 경로와 인자·응답은
그대로이며 route를 추가하거나 프로젝트 app.py를 덮어쓰지 않는다.

```python
# /tmp/yakeum-d-browser-harness/provider_harness.py
from backend.api import photo_demo
from backend.api.main import app
from backend.tests.test_a_provider_integration import run_fake_extraction
photo_demo.extract_virtual = run_fake_extraction
```

```bash
# 저장소 루트, 격리된 프로젝트 Python 사용
/tmp/yakeum-task-a-venv/bin/python -m pip install -r backend/requirements.txt
/tmp/yakeum-task-a-venv/bin/python -m pytest backend/tests/test_extraction_contract.py backend/tests/test_extraction_provider.py backend/tests/test_extraction_sdk.py backend/tests/test_a_provider_integration.py backend/tests/test_photo_demo.py -q
/tmp/yakeum-task-a-venv/bin/python -m pytest backend -q
/tmp/yakeum-task-a-venv/bin/python -m pip check
PYTHONPATH=/workspace/yakeum /tmp/yakeum-task-a-venv/bin/python -m uvicorn provider_harness:app --app-dir /tmp/yakeum-d-browser-harness --host 127.0.0.1 --port 8000
```

다른 터미널에서 frontend 폴더 기준:

```bash
pnpm test
pnpm build
pnpm dev --port 4192 --strictPort
YAKEUM_TEST_PYTHON=/tmp/yakeum-task-a-venv/bin/python YAKEUM_BROWSER_EXECUTABLE=/usr/bin/chromium node tests/photo-hira-integration.browser.cjs
YAKEUM_TEST_URL=http://127.0.0.1:4192/ YAKEUM_BROWSER_EXECUTABLE=/usr/bin/chromium node tests/image-review.browser.cjs
```

## 최종 검사 결과

| 검사 | 실제 결과 |
| --- | --- |
| 최초 관련 검사 | 56 passed + 내부 subtest 5 passed (엄격한 기대 동작 xfail 추가 전) |
| 최종 backend 전체 | **239 passed, 1 xfailed, 5 subtests passed**, 실패/오류 0, 종료 코드 0 |
| 경고 | 기존 Starlette TestClient deprecation 1개, 실패와 구분 |
| frontend | 7개 script groups 통과, strict TypeScript + Vite build 통과, 43 modules |
| 통합 browser | **13개 그룹 통과**, 360/390/768/1280px, runtime errors 0 |
| 단독 C image browser | **4개 시나리오 통과**, 4 viewport, 이미지/초점/파일교체/가족 reset/키보드/저장소 불변 |
| 외부 통신 | 실제 Gemini 분석·모델 목록·MFDS 요청 0. 통합 browser는 기존 font 요청 9개 차단 |
| 의존성 | pip check: No broken requirements found |

backend 전체는 독립 수집 항목 240개(239 통과 + 1 알려진 문제 xfail)이며
그 안의 unittest subtest 5개를 별도 독립 테스트로 합산하지 않는다.
브라우저 groups는 pytest 독립 개수와 별도 집계다.

유지 확인: D panel ID namespace, 혼합 실패 후보 보존/실패 확인 차단, 원본과 수정 분리,
B 미리보기·명시적 정규화 확인, 복용 UNKNOWN/PENDING 초기화, 타임라인, 편집 후 결과 무효화,
가족 A→B→A·취소·늦은 추출/정규화 응답 차단. 정상 결과를 사용자 확인한 후 처리 요청이
503이면 이전 결과/복용 확인이 사라지며 재시도는 UNKNOWN/PENDING부터 시작한다.
HIRA v2의 정상·실패/함량/반복/순서 변경 보류·원본 표시·재처리·정상 0건도 유지된다.

## A에게 전달할 재현·기대 결과·수정 요청

A 원격의 공통 parser는 아래 응답에서 정상 후보까지 문서 전체 실패로 만든다.
외부 호출 없이 재현할 수 있다.

```python
from backend.services.extraction import ExtractionContext, adapt_gemini_response
import json
context = ExtractionContext('00000000-0000-4000-8000-000000000001',
                            'virtual-mixed', '2026-10-26')
raw = json.dumps({'document_type':'약봉투','medications':[
    {'product_name_raw':'가상 정상제품','confidence':'0.9','ingredients':[
        {'ingredient_name_raw':'가상성분','product_strength':'100','product_strength_unit':'mg'}]},
    {'product_name_raw':'가상 오류제품','dose_per_administration':'읽기불가'}
]}, ensure_ascii=False)
results = adapt_gemini_response(raw, context)
# 현재: FAILED 1개 / record=null. 정상 후보도 없어짐.
```

기대: 정상 결과와 같은 위치의 FAILED를 함께 반환하고 원본 순번을 유지한다.
뒤 정상 후보의 source_record_id가 당겨지면 안 된다. JSON/배열 구조·호출자/가족
오류의 문서 전체 실패는 유지하고 공통 필드/상태/오류 코드는 바꾸지 않는다.

D는 관찰 테스트와 원하는 결과의 **strict xfail**을 함께 남겼다. xfail은 문제 해결이나
통과를 뜻하지 않는다. A 후속 코드가 원격에 게시되면 실제 diff 검토 후 반영하고,
그때 해당 strict xfail 표식을 제거해 정상 회귀로 전환해야 한다. 기대 결과가 의도치
않게 달라지면 XPASS(strict)가 실패하므로 조용히 문제를 숨기지 않는다.
로컬 d85e537은 이번 출처가 아니며 임의로 가져오지 않았다.

## 통합 가능 범위와 미검증

현재 통합 가능 범위는 **게시된 A SDK 전송과 기존 공통 결과의 오프라인 연결 호환성**이다.
알려진 A 혼합 숫자 오류를 고친 상태, 실제 사진 업로드 기능, live Gemini→앱 전체
완료라고 보고하지 않는다. 실제 Gemini/MFDS·모델 목록·실제 이미지 인식 성능·
인증/DB/배포는 이번 미검증이다. B/C/A 기능 자체 수정·새 임계값·정책 확정도 하지 않는다.
검증된 D 변경만 로컬 commit하며 push·PR·merge·force push는 하지 않는다.
