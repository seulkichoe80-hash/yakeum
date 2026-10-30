# HIRA 성공 결과가 사라지는 경로와 저장 전 초안 복구

2026-10-30 (한국 시간), codex/mvp-completion, 시작 HEAD 13d444a.
사용자가 실제 매칭·비교 성공 JSON을 확보했지만 결과/저장 버튼 대신 기존 저장 목록만 보인다고 보고했다.
실제 Render의 해당 run_id/DB row/당시 클릭 이력은 이번에 조회하지 못했다.
이번 조사/검증에서는 추가 실제 식약처/Gemini 호출·Render 설정 변경·배포를 하지 않았다.

## 재현한 문제

기존 AccountHiraPanel.list()는 저장 목록을 새로고침할 때 start(true)를 호출해
현재 snapshot을 null로 만들었다. 저장 목록은 saved=1만 조회하므로,
아직 저장하지 않은 성공 결과와 저장 버튼이 사라지고 기존 목록만 남을 수 있었다.
가짜 응답을 사용한 실제 브라우저에서 이 동작을 수정 전에 재현했다.
사용자의 실제 발생 원인이 반드시 이 클릭이었다고 확정하는 것은 아니다.

다른 초기화/응답 무시 경로도 확인했다.

- 파일 선택 변경·작업 취소: clear()가 현재 결과 제거/요청 무효화.
- 새 처리 시작·다른 상세 결과 열기: start(true)가 이전 결과 제거.
- 가족/매칭 모드 변경: 부모 key가 바뀌어 결과 컴포넌트 재구성.
- 로그인 작업 전체 나가기/새로고침/로그아웃: 컴포넌트 해제와 상태 제거.
- 60초 UI 대기 종료·취소·가족 변경 뒤의 늦은 응답: version/AbortController가 무시.
- 응답의 출처/버전/가족 검사가 실패하면 성공 JSON처럼 보여도 화면에 넣지 않고 오류 표시.

가족 변경/취소 뒤 늦은 결과를 다시 표시하지 않는 안전장치는 유지했다.
임의로 타임아웃을 늘리거나 성공 검사를 완화하지 않았다.

## 실제 현재 결과가 복구될 조건

기존 계정 HIRA 처리 API는 결과를 반환하기 **전에** hira_runs에 saved=0 초안과 result JSON을 저장한다.
정상적인 계정 처리 응답에 run_id가 있으면 그 시점에는 DB 저장이 완료된 것이다.
화면 snapshot 제거 자체는 DB row를 삭제하지 않는다.
다만 다음 경우에는 현재 복구를 보장할 수 없다.

- 다른 사용자/가족의 결과이거나 현재 세션의 권한이 없음.
- 결과가 이미 저장됨(이 경우 기존 저장 목록에서 연다).
- 기존 처리 정책에 따라 24시간 넘은 미저장 초안이 이후 처리 시 정리됨.
- DB가 초기화/복원/교체됐거나 DB 저장 전 처리 실패였음.
- 확보한 JSON이 계정 처리 응답 전체가 아니라 다른 진단/부분 데이터였음.

실제 Render에 row가 남았는지는 미확인이다. 현재 도구에 해당 서비스의 DB/사용자 세션 접근이 없으며
사용자의 비밀번호/키를 요청하거나 원격 DB를 직접 조작하지 않았다.
새 복구 기능으로 해당 가족의 DB 초안 존재 여부를 **외부 재조회 없이** 확인할 수 있게 준비했다.

## 수정과 추가 API

1. 저장 목록 새로고침은 start(false)로 바꿔 현재 처리 결과와 저장 버튼을 유지한다.
2. 본인 가족의 저장 전 결과 목록/상세를 읽는 GET을 추가한다.

- GET `/api/dev-account/families/{family}/hira-drafts`
  → source_type=HIRA, drafts=[{id,created}]. 본인 가족의 saved=0만.
- GET `/api/dev-account/families/{family}/hira-drafts/{run_id}`
  → 기존 DEV_ACCOUNT_HIRA_V1 envelope, saved=false, 원래 result/초기 intake_states.

기존 세션/가족 소유권 검사를 그대로 사용한다. 다른 사용자/가족/없는 자료는 거절한다.
저장된 row는 초안 상세로 반환하지 않는다. 기존 /hira-runs 상세의 saved=true 조건은 완화하지 않았다.
새 GET은 파서/식약처/Gemini/비교 엔진을 실행하지 않고 result JSON만 읽는다.
복구만으로 saved=1, user_confirmed=true, 실제 복용 확인 상태를 만들지 않는다.
기존 저장 POST를 사용자가 별도로 누르면 저장하고, 복용 여부 확인은 계속 독립 단계다.
DB 스키마/공통 약 정보/비교 상태/reason_code/관리자 1회 실행 기록은 변경하지 않았다.

## 새 배포 후 사용자 순서 (이번에는 배포하지 않음)

1. 앱에 로그인해 원래 처리했던 가족을 선택한다.
2. HIRA 영역의 **저장 전 HIRA 처리 결과 복구**를 누른다(GET, 식약처 호출 0회).
3. 생성 시각을 확인하고 해당 **저장 전 HIRA 결과**를 연다(GET, 식약처 호출 0회).
4. '복구한 저장 전 HIRA 결과'의 출처·비교·진단을 확인한다.
   현재 매칭 체크 상태는 다음 새 처리에만 적용된다. 복구/저장을 위해 체크를 바꿀 필요 없다.
5. **이 HIRA 결과 저장 (보류 포함)**을 누른다(식약처 호출 0회).
6. 기존 저장 목록에서 다시 열거나 로그아웃/재로그인 뒤 다시 연다(식약처 호출 0회).

초안 목록이 비어 있으면 선택한 계정/가족과 기존 저장 목록부터 확인한다.
없어진 결과를 얻으려고 'HIRA 파일 처리'를 다시 누르거나 새 외부 호출을 자동 실행하지 않는다.
성공 JSON에서 약품/record UUID와 run_id를 혼동해 임의로 저장 요청하지 않는다.
이전 기능에도 run_id를 아는 소유자는 기존 저장 POST를 사용할 수 있었지만,
이번 구현은 키/CSRF를 개발자 도구에 복사하는 수작업 대신 안전한 앱 버튼으로 복구 경로를 제공한다.

## 검증

가상 계정/가상 DB/XLSX/단일 가짜 XML 응답만 사용했다.
수정 전 브라우저에서 정상 결과→목록 새로고침→결과 영역 0개를 재현했다.
수정 후 `frontend/tests/hira-result-recovery.browser.cjs`의 6개 그룹 통과:

- 성공 결과/저장 버튼 표시.
- 목록 새로고침 후 결과/저장 버튼 유지.
- 모드 재구성 후 초안 GET 복구(출처 유지).
- 복구 GET이 늦게 도착해도 다른 가족 화면에 재표시되지 않음.
- 복구 결과→저장(복용 자동 확인 없음).
- 페이지 새로고침→저장 결과 재조회.

이 전체 브라우저 흐름에서 HIRA 처리 POST는 **최초 1회**이며 나머지는 복구/저장/조회다.
실제 외부 요청 0, runtimeErrors=0. 360/390/412/1280px 가로 넘침 없음.

실행 명령/결과:

```sh
# Python: /tmp/yakeum-mfdstest/bin/python, 실제 키 비움
python -m pytest -q backend
# 542 passed, PG 41 skipped(별도 실행), 5 subtests passed
python -m pytest -q backend/tests/test_postgres_integration.py
# 명시적 loopback 가상 PostgreSQL에서 41 passed
pnpm test
pnpm build
# 프론트 스크립트 10개, 타입 검사, Vite 53 modules 통과
node frontend/tests/hira-result-recovery.browser.cjs
# 6 groups passed; hiraProcessingPosts=1, realExternalRequests=0
node frontend/tests/account-hira.browser.cjs
# 기존 HIRA 회귀 10 groups passed; externalApiRequests=0
```

초안 읽기만으로 새 처리/외부 전송이 호출되지 않는지, 본인 저장/다른 계정·가족/비로그인 차단,
보류 null/정상 0건 보존, 저장된 row의 초안 제외를 API 검사로 확인했다.
각 Python 검사에는 기존 Starlette/httpx deprecation warning 1건이 있었다.
묶음/브라우저 그룹은 중복될 수 있으므로 합산해 독립 테스트 수로 표시하지 않는다.
실제 Render의 새 복구 기능·현재 사용자 초안 존재 여부는 배포/로그인 확인 전까지 미검증이다.
