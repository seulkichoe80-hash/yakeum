# 실제 매칭 선택 → 요청 → 응답 → 표시 추적

2026-10-30 (한국 시간), codex/mvp-completion, 시작 HEAD 6cc468f.
추가 실제 식약처/Gemini 호출 0회, Render 설정 변경·배포 없음.

## 판정

사용자 보고의 LOCAL_MOCK / TASK_D_HIRA_V2 / OFFICIAL-0001은 가상 결과의 지표다.
OFFICIAL-0001은 backend/services/mfds/data/mock_items.json의 가상 제품 ID다.
다만 당시 요청 URL·official_mode·POST 처리인지 저장 GET인지·배포 SHA가 제공되지 않아
**사용자가 본 현상의 정확한 발생 원인은 미확인**이다.

현재 코드에서 'MFDS_LIVE 요청에 LOCAL_MOCK 응답을 받아 새 성공 결과로 표시'하는 문제는 재현되지 않았다.
실제 브라우저에서 해당 응답을 주입하자 기존 검사로 거절했고 결과 영역은 비어 있었다.
재현하지 못한 서버/전송 문제를 추정해서 로직을 바꾸지 않았다.

## 코드 연결

| 단계 | 코드/의미 |
|---|---|
| 체크 상태 | AccountWorkspace의 Families가 officialMode를 관리. 기본 LOCAL_MOCK, 체크 시 MFDS_LIVE |
| 하위 전달 | FamilyWorkspace → AccountHiraPanel/PhotoWorkflow에 명시적 prop 전달 |
| HIRA 파일 선택 | 파일 state와 처리 상태만 변경. 부모 officialMode를 변경하지 않음 |
| HIRA 요청 | multipart에 body.append('official_mode',officialMode). 같은 계정·Origin·CSRF 사용 |
| 사진 요청 | accountProcess JSON의 official_mode. 응답 result.mode가 요청값과 다르면 거절 |
| 서버 분기 | 계정 account_hira.process의 Literal official_mode. 생략은 구형 호환 LOCAL_MOCK |
| 실제 분기 | configured_lookup가 실제 허용 flag/비밀키를 검사. 꺼져 있으면 503, Mock fallback 없음 |
| 결과 검사 | 새 처리에서는 응답 processing.official_data_mode를 요청 mode와 비교한 후 snapshot 설정 |
| 버전 검사 | 실제 경로 TASK_D_HIRA_MFDS_V1, 가상 TASK_D_HIRA_V2를 mode와 함께 검사 |
| 새 결과 표시 | start(true)에서 이전 snapshot 제거. 불일치/오류는 setError, 성공 snapshot 표시 안 함 |
| 저장 결과 열기 | GET의 저장된 mode/버전을 검사. 현재 체크는 다음 처리 선택이므로 과거 Mock 조회도 허용 |

공개 `/api/v2/reconciliations/hira`는 기존 Mock 전용이다. 계정의 실제 선택은
`/api/dev-account/families/{family}/hira/process`에 적용되며 공개 시연 API의 동작을 바꾸지 않는다.

## 실제로 재현한 두 상황

1. 실제 매칭이 체크된 상태에서 이전에 저장한 가상 HIRA 결과를 열면
   체크는 MFDS_LIVE지만 표시 결과는 LOCAL_MOCK / TASK_D_HIRA_V2 / OFFICIAL-0001이다.
   이는 새 실제 처리의 fallback이 아니라 **저장 결과 조회**다.
   저장 데이터 접근을 막거나 현재 선택에 맞춰 출처를 덮어쓰지 않는다.
2. '가상 시연 화면으로 돌아가기'로 나가고 다시 로그인 작업을 열면 Families가 새로 만들어져
   체크가 **눈에 보이게 해제**되고 기본 LOCAL_MOCK으로 돌아간다. 새로고침도 기본값으로 돌아간다.
   이후 실제 클릭한 파일 처리는 LOCAL_MOCK을 전송했다.
   이는 파일 선택에 따른 값 유실이나 서버가 실제 요청을 바꾼 동작은 아니다.

둘 다 현재 브라우저에서 재현했으나 사용자가 당시 이 경로를 거쳤다고 단정하지 않는다.

## 최소 수정

- 현재 선택과 다른 출처의 저장 결과를 열면 '현재 선택과 다른 출처의 이전 저장 결과' 안내를 표시한다.
  체크 상태는 다음 처리에만 적용되고 아래 자료를 새로 처리한 것이 아니라는 점을 명시한다.
- 로그인 작업 전체 재진입/새로고침 시 가상 기본값으로 돌아간다는 안내를 추가했다.
- 실조회 선택을 localStorage 등에 영구 보존하거나 자동으로 켜지 않는다.
- 모드 전달/서버 분기/기존 불일치 차단/비교 로직/DB/권한/관리자 1회 기록은 변경하지 않았다.
- 실제 모드의 가상 응답을 허용하도록 검사 조건을 완화하지 않았다.

## 브라우저 추적 기록

실제 앱·가상 계정·가상 XLSX·가상 SQLite를 사용했다.
서버 MFDS_API_KEY는 빈 값, YAKEUM_MFDS_MATCH_ENABLED=0으로 강제한 검사 프로세스다.
오프라인 동작 확인이며 Render 설정을 바꾼 것이 아니다.
가상 응답 주입은 브라우저 route.fulfill에서만 했으며 외부 식약처 전송은 없다.
헤더/파일 전체/키/사용자 자료의 trace/HAR는 저장하지 않고 official_mode 값만 기록했다.

| 브라우저 행동 | POST official_mode | 결과 |
|---|---|---|
| 기본 미체크 처리 | LOCAL_MOCK | 실제 가상 서버 분기. LOCAL_MOCK/TASK_D_HIRA_V2/OFFICIAL-0001 확인 |
| 체크 → 파일 선택/해제/재선택 → 처리 | MFDS_LIVE | 비활성 서버의 503. 성공/과거 결과 표시 없음 |
| 체크 유지 → 가상 응답 강제 주입 | MFDS_LIVE | '요청한 의약품 매칭 출처와 응답이 다릅니다.'로 거절. 결과 영역 없음 |
| 가족 추가·A-B-A 재구성 → 파일 처리 | MFDS_LIVE | 체크/필드 유지, 서버 503. 가상 결과로 대체 안 함 |
| 체크 상태에서 저장 가상 결과 GET | POST 없음 | 저장된 가상 출처 유지, 새 안내 표시 |
| 작업 화면 전체 재진입 후 처리 | LOCAL_MOCK | 눈에 보이는 미체크와 요청·응답이 일치 |
| 전체 페이지 새로고침 후 작업 열기 | POST 없음 | 미체크 기본값 확인, 자동 처리 없음 |

캡처한 요청 mode 순서는
`[LOCAL_MOCK, MFDS_LIVE, MFDS_LIVE, MFDS_LIVE, LOCAL_MOCK]`이며 누락 필드는 없었다.
선택값은 파일 선택/해제·가족 변경 동안 유지됐다.
360/390/412/1280px에서 새 안내에 가로 넘침이 없었다.

## 실행한 검사

```sh
# backend: /tmp/yakeum-mfdstest/bin/python 사용, 실제 키 없이 실행
python -m pytest -q backend/tests/test_live_mfds_matching.py
# 30 passed, 기존 Starlette/httpx deprecation warning 1건

# frontend
pnpm test
pnpm build
# 기존 테스트 스크립트 10개, 타입 검사, Vite 53 modules 통과

# localhost의 실제 앱/가상 DB, 실제 provider 비활성화 상태에서
node frontend/tests/mfds-mode-trace.browser.cjs
# 7개 그룹, realExternalRequests=0, runtimeErrors=0
```

백엔드 기능은 변경하지 않아 전체/PG 검사를 불필요하게 반복하지 않았다.
초기 브라우저 helper의 가족 선택 요소는 기존 테스트와 같은 combobox 접근 이름으로 맞춘 뒤 통과했다.
실제 Render에서 같은 상황이 발생한 당시의 요청/응답을 새로 조회한 것은 아니다.
