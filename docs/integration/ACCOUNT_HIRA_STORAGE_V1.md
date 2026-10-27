# 개발용 계정 HIRA 저장·재조회 v1

2026-10-27. codex/mvp-completion, 시작 HEAD `8e4647a628a08131b7eb2683f6fd91e349bf6ccb`.
시작 작업 트리 clean. 전체 원격 fetch 후 이후 팀원 변경 없음. 기존 HEAD/브랜치/작업을 보존했다.

## 추가 기능과 사용 순서

기존 개발용 로그인 화면에서 본인 가족을 선택하면 **HIRA 자료 비교·저장** 영역이 보인다.

1. 가상의 이전/현재 XLSX 파일을 각각 선택하고 **HIRA 파일 처리**.
2. 원본 행/정규화/보류 사유와 비교 결과를 확인.
3. **이 HIRA 결과 저장 (보류 포함)**. 저장 자체는 내용 확인·실제 복용 확인이 아니다.
4. 비교 항목이 있다면 실제 복용 여부를 별도로 선택해 저장한다.
5. 로그아웃·재로그인 후 **HIRA 저장 결과**를 선택하면 원본/보류/비교/복용 확인을 다시 볼 수 있다.

사진과 HIRA의 목록·결과·복용 확인은 별도다. 사진 자료가 HIRA로 바뀌거나 덮어써지지 않는다.
가족을 바꾸면 이전 결과가 즉시 제거되고 선택 가족의 저장 목록을 새로 조회한다.
취소·파일 교체·가족 변경·로그아웃 뒤 늦은 처리/상세 응답은 화면에 반영하지 않는다.
저장은 서버에서 완료될 수 있으므로 요청 취소가 이미 완료된 저장의 자동 삭제를 뜻하지는 않는다.

## 저장하는 정보와 확인 의미

- 기존 HIRA v2 snapshot 전체를 서버가 계산해 보관한다. 클라이언트가 비교 결과를 위조해 제출하지 않는다.
- 원본은 제한된 `source_rows.raw_fields`, 원본 위치/순번/문서 ID와 normalization_ref로 보존한다.
  XLSX 파일 bytes/파일명/시트명을 추가 저장하거나 실제 건강정보를 수집하지 않는다.
- `accepted_results`, `review_results`는 정규화 결과와 실패 후보를 모두 보존한다.
- `comparison.executed=false`, 보류 사유/영향 참조, `reconciliation_result=null`은 그대로다.
- 정상 0건은 `executed=true`, `holds=[]`, `reconciliation_result.items=[]`이며 null로 바꾸지 않는다.
- HIRA 원본의 `user_confirmed=false`는 저장 후에도 유지한다. 자료 저장만으로 확인됐다고 표시하지 않는다.
- 비교가 실행된 항목의 복용 초기값은 UNKNOWN/PENDING. 별도 명시적 선택만 USER_VERIFIED로 저장한다.
  UNKNOWN을 사용자가 직접 선택한 경우와 아직 선택하지 않은 UNKNOWN/PENDING도 구분한다.
- 복용 확인에는 서버가 로그인 사용자 ID와 UTC 시각을 기록한다. 원본/정규화/비교 snapshot은 바뀌지 않는다.
- 보류/0건은 복용 항목이 없으므로 복용 확인을 만들 수 없다. 엉뚱한 record ID·중복 확인은 거부한다.
- 실패 후보 제외를 이유로 과거 기록을 중단/미확인으로 잘못 판정하지 않으며 기존 전체 보류 정책을 유지한다.

공식 정보 매칭은 기존 LOCAL_MOCK이다. deterministic XLSX 처리와 B/D 함수는 실제 실행하지만,
실제 MFDS/Gemini/모델 목록은 호출하지 않는다. 실제 HIRA export·실제 사용자 자료도 미검증이다.

## API/Schema 영향 — 추가 계약

기존 MedicationRecord, 정규화 결과, Reconciliation 상태/reason_code,
`TASK_D_HIRA_V2`와 사진/계정 `DEV_ACCOUNT_V1` 계약은 바꾸지 않는다.
새 소유권 검사 API만 `DEV_ACCOUNT_HIRA_V1` envelope로 분리한다.
기존 파일 크기·XLSX 구조·행/열·압축 해제 제한과 HIRA v2 helper를 재사용한다.

모든 경로 접두사: `/api/dev-account/families/{family}`.
세션·소유권·Origin·CSRF 검사는 기존 개발용 계정과 같다. 타인 가족/자료는 404, 미로그인은 401.

| Method / path | 입력과 역할 |
|---|---|
| POST /hira/process | multipart previous_file/current_file. family는 인증된 소유 경로에서 지정. 서버 결과를 미저장 snapshot으로 생성 |
| POST /hira-runs/{run}/save | 기존 SaveInput: intake_confirmations=[{record_id,choice}], 기본 []. 보류도 저장 가능하지만 복용 확인은 없음 |
| GET /hira-runs | 본인 선택 가족의 명시적으로 저장한 HIRA 목록 |
| GET /hira-runs/{run} | 원본·정규화·비교 snapshot과 별도 복용 상태 |
| PATCH /hira-runs/{run}/intake | 기존 Choice: {record_id,choice}. 저장한 비교 항목의 복용 상태만 변경 |

process/detail 공통 응답 예시(결과는 기존 v2 전체 객체, 아래는 의미상 발췌):

```json
{
  "response_version":"DEV_ACCOUNT_HIRA_V1",
  "development_only":true,
  "source_type":"HIRA",
  "run_id":"10000000-0000-4000-8000-000000000001",
  "family_member_id":"00000000-0000-4000-8000-000000000001",
  "saved":true,
  "result":{
    "response_version":"TASK_D_HIRA_V2",
    "comparison":{"executed":false,"holds":[{"kind":"UNIDENTIFIED_FAILED_INPUT","message":"실패 후보가 있어 비교를 보류했습니다.","affected_refs":[{"side":"current","document_id":"20000000-0000-4000-8000-000000000001","input_index":0}]}]},
    "reconciliation_result":null
  },
  "intake_states":[]
}
```

위 예시는 발췌이며 전체 result에는 source_rows와 정규화 결과 등 기존 v2 필드가 포함된다.
holds의 의미와 영향 참조는 HIRA_COMPARISON_HOLD_V2.md를 유지한다. 내부 result.processing.persisted=false는
파일 처리 함수의 무저장 계약이고, 계정 저장 여부는 envelope.saved로 구분한다.
서버가 보관한 결과만 저장하며 사진 run ID를 HIRA 경로에 넣어도 조회/저장/수정할 수 없다.
저장 결과는 덮어쓰지 않고 같은 run의 save는 목록을 중복 생성하지 않는다.

## SQLite 버전 1 → 2

- 기존 테이블은 그대로 두고 `hira_runs`, `hira_intake`만 추가한다.
- 사진 runs/intake와 별도 테이블/외래키를 사용한다. 사용자·가족·세션·사진 데이터는 보존한다.
- schema 생성과 user_version=2 갱신을 하나의 SQLite transaction으로 수행한다.
- 새 DB, 버전 1, 버전 2를 지원하며 지원하지 않는 버전은 초기화하지 않고 거부한다.
- 미저장 HIRA snapshot은 24시간 후 다음 HIRA 처리 요청에서 정리한다. 명시적 저장 자료는 삭제하지 않는다.
- 운영 백업/마이그레이션 배포 체계는 미구현이다. 기존 DB를 업그레이드할 때는 서버를 멈추고
  별도 안전한 백업을 먼저 보관해야 한다. 이전 코드로 돌린다고 DB 버전이 자동으로 낮아지지 않는다.
- 실제 사용자 DB가 아닌 가짜 DB에서 이전 계정/세션/가족/사진/복용 값의 보존을 검증했다.

## 실행 설정과 남은 범위

새 외부 계정/키는 필요 없다. [개발용 실행 설정](DEV_ACCOUNT_STORAGE_V1.md)의
YAKEUM_DEV_ACCOUNT_ENABLED=1, YAKEUM_APP_MODE=development, 저장소 밖 YAKEUM_DEV_DB_PATH,
정확한 YAKEUM_DEV_ORIGIN을 사용한다. DB 파일과 이미지·실제 건강정보는 Git에 넣지 않는다.
운영 인증/HTTPS 쿠키/암호화/백업 복구/사용자 삭제·동의 정책/권한 위임/운영 배포는 여전히 미완료다.

다음 우선순위는 합성 자료 사용자 테스트, 사진/HIRA 목록 사용성 확인, 저장 자료의 삭제·보관·백업 정책,
실제 연동 전 비용/호출 범위 확인과 별도 승인이다. 자동 대표 선택·출처 간 중복 병합은 임의 구현하지 않았다.

## 최종 검증 결과

- 백엔드 전체 **319 passed**, 내부 subtest 5 passed(독립 수에 합산하지 않음), 실패/xfail 0.
  기존 Starlette deprecation 경고 1개. 새 HIRA 저장 검사 13개 포함.
- 새 검사: 정상 저장/재로그인/원본 값과 미확인 플래그 유지, 실패·함량·반복 보류,
  정상 비교 0건, 별도 복용 확인, 사용자 2명/여러 가족 권한, 사진/HIRA 저장 분리,
  v1 DB의 기존 계정·세션·사진·복용 확인 보존 마이그레이션, 잘못된 업로드/CSRF/실제 API 차단.
- 프론트 기존 7 script 그룹, strict TypeScript, Vite build 통과(47 modules).
- 새 HIRA 계정 브라우저 **10개 그룹 통과**. 정상·보류·0건 저장/재로그인 복원,
  사진 목록 공존, 별도 복용 확인, 타인 조회·수정 차단, 취소·가족 A→B→A·로그아웃의 늦은 응답 차단.
- 기존 계정/사진 저장 브라우저 **7개**, 사진 업로드 **10개**, Mock/HIRA 통합 **13개 그룹** 통과.
- 검사 중 확인된 모바일 가로 넘침은 파일 입력/버튼 너비를 제한해 수정했다.
  최종 360/390/768/1280px에서 가로 넘침 없음. 브라우저 runtime errors 0, 실제 외부 의료 API 요청 0.
- 저장된 HIRA 결과 screenshot을 /tmp에서 열어 확인했고 Git에는 넣지 않았다.
- pip check / git diff --check 통과. 실제 건강정보·Gemini/MFDS 호출·운영 배포 없음.

```bash
# 저장소 루트, 프로젝트 Python 활성화
python -m pytest backend -q
python -m pip check
pnpm --dir frontend test
pnpm --dir frontend build

# 실제 검증 환경: 최신 backend 8041, Vite 4200 -> 8041 프록시
export YAKEUM_TEST_URL=http://127.0.0.1:4200/
export YAKEUM_TEST_PYTHON=/tmp/yakeum-task-a-venv/bin/python
export YAKEUM_BROWSER_EXECUTABLE=/usr/bin/chromium
export YAKEUM_PLAYWRIGHT_MODULE=/opt/codex/runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright
node frontend/tests/account-hira.browser.cjs
node frontend/tests/account-storage.browser.cjs
node frontend/tests/photo-upload.browser.cjs
node frontend/tests/photo-hira-integration.browser.cjs
```

QA DB는 /tmp/yakeum-hira-account-final/accounts.sqlite3이며 가상 자료만 사용했다.
기존 프로세스·DB·브랜치는 보존했다. 브라우저 계정 검사는 새 가상 계정을 만들고 실제 시도 제한도
적용되므로 반복 검사 시에는 별도 QA DB/프로세스를 쓰거나 대기하며 제한을 완화하지 않는다.
운영용 인증·HTTPS/암호화·백업 복구·실제 사용자 삭제/동의·실제 외부 연동은 미검증으로 남긴다.
