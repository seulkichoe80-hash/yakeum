# 사진 업로드 연결 v1 — 가짜 AI 기반 로컬 통합

2026-10-27. `codex/mvp-completion`, 시작 SHA `7c8602f84895feab260abdd7b6048a5e86129c34`.
기존 D/A/B/C 브랜치 보존. 모든 원격 branch를 명시적 fetch로 확인했고 새 팀원 변경 없음.
기본 fetch refspec에 새 작업 브랜치가 없어 `origin/codex/mvp-completion` 참조도 함께 갱신했다.

## 범위와 계약 영향

기존 MedicationRecord, ExtractionResult, NormalizationResult, Reconciliation 상태/reason_code,
HIRA v1/v2 및 `/api/local-demo/photos/*` 입력/응답은 그대로다.
새 `/api/local-demo/photo-uploads/*`만 `response_version=UPLOADED_PHOTO_V1`로 구분한다.
이는 승인된 가상 업로드 연결용 계약이며 운영 API/팀 전체 합의 완료를 뜻하지 않는다.

기존 photo_demo의 순수 처리 함수에 **서버 내부** sources 인자를 추가하여 원본 snapshot을
재사용한다. 이 인자는 HTTP 입력 필드가 아니며 클라이언트가 추출 결과를 위조해 보내지 않는다.
업로드 경로는 기존 HIRA 비교 필수값 검사도 재사용한다. 기존 Mock 경로의 정책은 바꾸지 않는다.
새 화면은 기존 후보 수정·확인·정규화 검토·복용 확인·타임라인을 재사용한다.

## 화면에서 사용

1. 자료 등록 → 약봉투/처방전/건강기능식품 사진 선택.
2. 현재 사진 파일·기준일 지정 → **사진 업로드 연결 열기 (가짜 AI)**.
3. 이전 사진 파일·이전 기준일 지정.
4. 이전/현재 각각 **사진 업로드 후 가짜 후보 보기**.
5. 후보 수정·원본 대조 체크·추출 내용 확인 완료.
6. **수정 후보 B 정규화 미리보기**, 경고와 원본/수정/정규화 결과 확인.
7. **정규화 결과 확인 후 D 비교**.
8. 실제 복용 여부를 별도로 선택하고 **사진 변경 이력** 확인.

모든 파일과 약품 정보는 합성/가상 자료만 사용한다. 이미지 픽셀을 실제로 읽어 약품을
인식하는 기능은 아니다. 실제 이미지 bytes는 로컬 서버에 업로드하고 검사하지만,
AI 결과는 서버의 명시적인 fake_response 함수가 생성한다. 공식 매칭도 LOCAL_MOCK이다.
기존 단독 화면 Mock과 로컬 Mock 전체 연결 버튼은 유지한다.

## 입력과 응답

`POST /api/local-demo/photo-uploads/extract`, multipart:

- family_member_id: UUID (인증/권한의 대체 수단 아님)
- record_date: ISO 날짜
- source_type: MEDICINE_BAG / PRESCRIPTION / SUPPLEMENT
- file: PNG/JPEG/WebP 정지 사진
- scenario: single(기본)/multiple/missing/failed/repeat/unknown/mixed; 가짜 AI 검사에만 사용

반환 예시(추출 결과 객체는 기존 공통 계약 그대로):

```json
{
  "response_version": "UPLOADED_PHOTO_V1",
  "mode": "LOCAL_MOCK",
  "persisted": false,
  "document_id": "10000000-0000-4000-8000-000000000001",
  "upload_token": "20000000-0000-4000-8000-000000000001",
  "expires_in_seconds": 900,
  "results": [
    {"status":"FAILED","record":null,"warnings":[],"errors":[
      {"code":"AI_EXTRACTION_FAILED","message":"가상 인식 실패 예시","field":null}
    ]}
  ]
}
```

`POST /api/local-demo/photo-uploads/process`, JSON:

```json
{
  "family_member_id":"00000000-0000-4000-8000-000000000001",
  "previous":{"upload_token":"20000000-0000-4000-8000-000000000001","reviews":[]},
  "current":{"upload_token":"20000000-0000-4000-8000-000000000002","reviews":[]},
  "normalization_confirmed":false
}
```

reviews는 기존 사진 로컬 계약의 index/confirmed/draft. 위 빈 reviews는 구조 예시이며
후보가 있는데 검토가 비어 있으면 비교를 보류한다. 모든 후보 순번을 중복 없이 제출해야 한다.
응답은 기존 사진 처리 응답 + response_version. stage는 held/normalized/compared.
비교 미실행은 reconciliation_result=null, current_intake_states=[]이며 보류 사유를 표시한다.
정상 비교 0건은 items=[]와 구분한다. 추출 원본/사용자 수정/정규화 결과를 각각 보존한다.

## 일관성·보류·확인

- 업로드당 문서 UUID/추측하기 어려운 token을 서버가 생성한다. 약품 source_record_id는 문서:원본순번.
- 정규화 미리보기/최종 비교에서 사진 재추출 없음. 가짜 AI가 호출되는 것은 업로드 시 한 번뿐.
- 정상+숫자 오류 혼합은 같은 순번의 FAILED와 정상 후보를 보존한다. 실패 후보 확인은 비활성화한다.
- 실패/record:null/미확인 비교 필수값/반복/부분 매칭/미확정 제품 식별이 있으면 전체 비교 보류.
- 성분·함량·단위·투약량·횟수는 추정하지 않는다. 자동 대표 선택/기록 삭제 없음.
- 업로드는 user_confirmed=false. 추출 내용 확인, 정규화 결과 확인, 실제 복용 확인은 세 단계다.
- 최종 비교 직후 현재 복용은 UNKNOWN/PENDING, 사용자가 별도 선택해야 한다.
- 수정·파일 교체·취소·가족 변경·새 요청은 이전 결과/복용 확인을 무효화한다.
  세대 번호와 AbortController로 늦은 응답을 차단한다.
- 같은 token을 이전/현재로 쓰면 보류. 같은 파일 재업로드는 새 문서이며 자동 중복 삭제하지 않는다.

## 파일·메모리 제한

- 최대 10MiB, PNG/JPEG/WebP만. 확장자·MIME·Pillow 실제 포맷이 일치해야 한다.
- 이미지 헤더 verify 후 실제 decode도 수행한다. 손상/빈 파일/동영상·애니메이션 거절.
- 최대 20,000,000 pixels. 압축 폭탄 경고/오류는 안전한 사용자 안내로 처리한다.
- 400 빈 파일, 413 용량 초과, 415 형식 불일치, 422 손상/픽셀/입력 오류.
- 처리한 사진 bytes·파일명은 snapshot에 보관하지 않고 UploadFile을 닫는다.
  multipart 처리 중 임시 spool 파일이 생길 수 있으나 요청 종료 시 닫힌다. 영구 저장 없음.
- 후보 snapshot만 프로세스 메모리에 최대 128문서, 15분 유효. 만료 정리는 다음 store 접근 시 수행한다.
- 만료/없는 token/다른 가족 token은 모두 410 + 다시 등록 안내. 공간이 차면 503.
- 서버 재시작 시 소멸. 단일 프로세스 개발용이며 여러 worker/서버에 공유되지 않는다.
- 취소 후 이미 도착한 snapshot이 있어도 화면에서 사용하지 않고 만료된다.
  이 기능은 로그인/가족 권한/영구 저장을 제공하지 않으므로 공개 운영과 실제 건강정보 사용 금지.

## 실제 Gemini 설정

기존 공식 함수 backend.api.extraction_provider.extract_image_candidates와 SDK는 보존한다.
설정 이름은 GEMINI_API_KEY, YAKEUM_GEMINI_MODEL. 이번 환경에서 둘 다 미설정임만 확인했고
값을 출력하지 않았다. 새 업로드 경로에는 live 전환이 없으며 키를 넣어도 실제 호출하지 않는다.
실제 Gemini 분석/모델 목록 조회/MFDS 호출 0회, 실제 인식 성능·실제 연동은 미검증이다.
향후 live 연결 전 모델·가격/무료 범위·최대 호출 수와 개인정보 처리 범위를 안내해야 한다.

## 다음 단계

1. 서버가 검증하는 로그인 세션·가족 소유권 계약 설계. UUID/token을 접근 권한으로 오해하지 않기.
2. 후보 원본/수정/정규화/복용 확인을 구분하는 저장 모델·마이그레이션과 사용자 동의/삭제 정책.
3. 권한 검사를 거친 repository로 snapshot store 교체, 재시작/동시 처리/가족 간 조회 거부 검사.
4. 실제 Gemini·공식 MFDS 연결은 별도 사전 안내/승인 후 최소 횟수로 검증.

## 최종 검증 결과

- 백엔드 전체 **285 passed**, 내부 subtest 5개 통과(독립 테스트에 합산하지 않음),
  실패/xfail 0. 기존 Starlette deprecation 경고 1개. 새 업로드 API 검사 26개 포함.
- 프론트 기존 테스트 7 script 그룹, strict TypeScript, Vite build 모두 통과(44 modules).
- 새 업로드 브라우저 **10개 그룹**: 실제 multipart 업로드/수정/정규화/비교/별도 복용/이력,
  재추출 없음, 혼합 실패 보존, 미확인 보류/정상 재처리, 취소·가족 A→B→A 늦은 추출/정규화,
  만료 오류 후 이전 결과/복용 제거, 파일 교체, 손상 사진 안내.
- 기존 사진 Mock·HIRA 브라우저 **13개 그룹** 통과. HIRA 정상/전체 보류/재처리/정상 0건 유지.
- 360/390/768/1280px 가로 넘침 없음, runtime errors 0, 외부 의료 API 요청 0.
- 비교·복용 확인·타임라인 실제 화면 screenshot을 /tmp에서 열어 육안 확인. Git에는 넣지 않음.
- pip check, git diff --check 통과. 실제 Gemini/MFDS/인식 성능/영구 저장/인증/배포는 미검증.

실행 명령(저장소 루트, 프로젝트 Python 가상환경 활성화):

```bash
python -m pip install -r backend/requirements.txt
python -m pytest backend -q
python -m pip check
pnpm --dir frontend test
pnpm --dir frontend build
```

브라우저 검사는 최신 backend를 8020, 프론트를 4196(`/api`→8020 프록시)으로
격리 실행했다. 기존 8000/4192 프로세스는 건드리지 않았다. `/tmp`의 임시 Vite config만 사용.
기본 개발 실행은 MVP_DEMO.md의 8000/4192를 사용해도 동일한 앱이다.

```bash
# 실제 사용 중인 venv Python/Chromium/Playwright 경로에 맞게 지정
export YAKEUM_TEST_URL=http://127.0.0.1:4196/
export YAKEUM_TEST_PYTHON=/tmp/yakeum-task-a-venv/bin/python
export YAKEUM_BROWSER_EXECUTABLE=/usr/bin/chromium
export YAKEUM_PLAYWRIGHT_MODULE=/opt/codex/runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright
node frontend/tests/photo-upload.browser.cjs
node frontend/tests/photo-hira-integration.browser.cjs
```
