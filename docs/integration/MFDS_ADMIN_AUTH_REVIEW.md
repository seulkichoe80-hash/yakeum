# 앱 로그인과 관리자 화면 인증 대조

2026-10-30 (한국 시간), codex/mvp-completion, 시작 HEAD 837011e.
실제 식약처/Gemini 호출·Render 설정 변경·배포는 하지 않았다.
계정/쿠키/키/토큰 원문을 기록하거나 URL에 넣지 않았다.

## 확인한 사실과 확인하지 못한 원인

현재 원격·로컬 소스에서 앱 인증은 Bearer 토큰이 아니라 HttpOnly 세션 쿠키다.

| 경로 | 사용하는 인증 |
|---|---|
| 앱 accountRequest | credentials=same-origin으로 쿠키 전송. 쓰기에는 메모리의 X-CSRF-Token |
| /login | 서버가 쿠키 발급. 로그인 JSON에는 CSRF가 있지만 앱용 Authorization 토큰은 없음 |
| /me 및 관리자 /view/status/execute | 같은 principal이 세션 쿠키의 해시를 DB에서 검사 |
| 외부 시연 공유 입구 | 별도의 Authorization: Basic 검사. 앱 로그인/관리자 권한을 대체하지 않음 |

주소창 이동은 앱 JavaScript가 fetch에 넣는 임의 헤더를 복사하지 않는다.
다만 **현재 코드에는 앱용 Authorization 헤더 자체가 없다**. 같은 origin/path의 정상 쿠키는
브라우저가 주소창 이동에도 전송할 수 있다. Basic 헤더는 브라우저의 challenge/cache 정책도 관계되므로
항상 없어진다거나, 그 누락만으로 앱 로그인 오류가 발생했다고 단정하지 않는다.

로컬 실제 브라우저에서 앱 로그인 후 관리자 상태 요청과 직접 /view 이동을 검사했다.
Authorization 없음, 쿠키 있음(값을 출력하지 않고 존재 여부만 검사), /view=200이었다.
따라서 사용자가 본 Render의 401을 이 소스로 동일하게 재현하지는 못했다.
실제 배포 SHA/브라우저 쿠키 전송 조건/세션 유효 상태는 별도 확인이 필요하며 원인은 미확인이다.
현재 서버 오류 문구는 다음 계층을 구분한다.

- '가상 시연 접근 비밀번호가 필요합니다': 공유 입구 Basic 인증(401).
- '로그인이 필요하거나 세션이 만료되었습니다': 앱 세션 쿠키/DB 인증(401).
- '서버에서 지정한 관리자만 사용할 수 있습니다': 유효한 로그인이나 지정 관리자 아님(403).

## 개선한 진입 경로

로그인·저장 화면에서 관리자 /status 조회가 성공하면 **식약처 관리자 검증 열기** 버튼을 표시한다.
일반 계정/비활성 기능에는 버튼을 표시하지 않는다. 이 숨김 처리는 편의 기능이며,
서버의 기존 관리자·세션·Origin/CSRF 검사는 그대로 최종 권한을 검사한다.

버튼은 같은 앱 안의 React 화면을 열고 기존 accountRequest만 재사용한다.
토큰/CSRF/쿠키를 URL·fragment·새 localStorage·window.name·새 인증 쿠키에 복사하지 않는다.
주소창 이동, 새 탭, HTML blob/iframe, JavaScript HTML 삽입을 쓰지 않는다.
기존 관리자 HTML은 보존하고 인증도 변경하지 않았다.

사용자 변경/로그아웃/401 세션 만료 시 관리자 component를 제거하고 진행 요청을 취소해
이전 화면이 남지 않게 한다. 늦은 상태 응답은 generation과 AbortController로 차단한다.
1회 실행은 명시적 동의 후 기존 POST API를 사용하며 실패/응답 불명확 시 화면에서 재전송하지 않는다.
DB 고정 slot과 재시작/중복 호출 차단은 이번에 바꾸지 않았다.

관리자 버튼 표시·화면 열기·상태 새로고침은 GET만 호출하며 식약처 조회를 실행하지 않는다.
서버의 MFDS 키도 브라우저에서 받거나 표시하지 않는다.

## 실제 실행한 검사

```sh
# frontend
pnpm test
pnpm build
# 테스트 스크립트 10개, 타입 검사, Vite 빌드(52 modules) 통과

# backend: 현재 Python은 /tmp/yakeum-mfdstest/bin/python
python -m pytest -q backend/tests/test_mfds_admin.py backend/tests/test_dev_account.py
# 35 passed, 기존 Starlette/httpx deprecation warning 1건

# 가상 계정/가상 DB/실제 앱을 띄운 loopback 서버
node frontend/tests/mfds-admin-login.browser.cjs
# 7개 그룹 통과. 실제 앱 가입/로그인→관리자 버튼→화면 열기/상태 조회,
# Authorization/쿠키 존재 여부 검사, 기존 HTML 주소 이동, 세션 만료 화면 제거,
# 로그아웃/다른 사용자 로그인 뒤 늦은 응답 차단, 일반 사용자 UI/서버 거부, 360/390/412/1280px 가로 넘침 없음
# adminExecuteRequests=0, externalBrowserRequests=0, runtimeErrors=0
```

추가 HIRA 브라우저 회귀도 별도로 실행해 10개 그룹 통과(runtimeErrors=0, externalApiRequests=0)를 확인했다.
명령은 `node frontend/tests/account-hira.browser.cjs`이며 가상 계정·가상 XLSX/사진·가상 DB만 사용했다.
헤더 비교에 원문 로그나 trace/HAR를 저장하지 않았다. 가상 식약처 transport 숫자 카운터 파일도
생성되지 않아 이 작업에서 **가상 식약처 전송 자체도 0회**였음을 확인했다.
Render 실제 로그인/새 화면은 아직 미검증이며, 이 작업에서 배포하지 않았다.
공통 API/DB/가족 접근/실제 비교 정책은 변경하지 않았다.
전체 백엔드는 변경하지 않아 반복하지 않았고, 관련 권한/세션 검사 35개를 실행했다.
