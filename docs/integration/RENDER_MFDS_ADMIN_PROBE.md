# Render 관리자 임시 식약처 검증 — 구현 완료, 실제 실행/배포 전

2026-10-29, codex/mvp-completion. PC 설치·실행은 필요 없다.
이 기록의 검증은 가상 계정·가상 DB·가짜 식약처 전송만 사용했다.
실제 Render 설정 변경/배포, Supabase 접속/초기화, 추가 Gemini/식약처 호출은 하지 않았다.
클라우드 개발 환경의 기존 503/envoy/upstream 연결 오류가 Render에서도 발생한다고 단정하지 않는다.

## 동작과 접근 제한

- 기본 꺼짐. `YAKEUM_MFDS_PROBE_ENABLED=1`과 서버 지정 계정이 모두 필요하다.
- 기존 개발용 계정 로그인 세션을 검증하고, 서버가 읽은 사용자명과
  `YAKEUM_MFDS_PROBE_ADMIN_USERNAME`을 정확히 비교한다. 요청 body/화면의 관리자 표시는 신뢰하지 않는다.
  첫 가입자 자동 관리자 지정/관리자 자동 가입/임시 로그인은 없다.
- 지정 계정은 **미리 본인이 가입하고 정상 로그인 가능한 기존 계정**이어야 한다.
  아직 만들지 않은 이름이나 다른 사람의 계정을 지정하지 않는다.
- 로그인 전 401, 일반 계정 403, 비활성 404, POST Origin/CSRF 불일치 403.
- 외부 시연 설정(YAKEUM_EXTERNAL_DEMO=1)에서는 PostgreSQL 영속 저장만 허용한다.
  Render Free의 임시 SQLite로 실행 예산을 보관하지 않는다.
- 보호된 별도 HTML 화면을 서버에서 제공한다. 일반 사용자 화면에 실행 버튼은 추가하지 않았다.
  이 페이지에도 인증키 입력란/표시는 없다. CSP·frame 차단·no-store 및 기존 공유 입구 보호를 유지한다.
- 사진·HIRA 경로는 계속 LOCAL_MOCK이며 기존 저장/삭제/가족 권한, SSL, Gemini 설정을 바꾸지 않는다.
- 기존 개발 인증을 제한해서 쓰는 임시 진단 기능이며 운영용 관리자 인증/MFA/RBAC 완성을 뜻하지 않는다.

## DB의 단 한 번 실행 기록

기존 PostgreSQL `yakeum_demo` 스키마(SQLite 로컬 검사에서는 해당 DB)에
`mfds_probe_attempts(slot TEXT PRIMARY KEY, started TEXT NOT NULL, result TEXT)`를 추가한다.
기존 테이블/자료를 수정·삭제하지 않는다. 별도 진단 테이블로 기존 schema_version=2는 유지한다.
테이블은 첫 관리자 상태 조회/실행 때 additive CREATE IF NOT EXISTS로 준비한다.
Supabase 콘솔에서 스키마를 삭제하거나 수동 초기화할 필요가 없다.
해당 DB 역할이 테이블을 만들 수 없으면 검증이 실패하며 외부 요청은 시작하지 않는다.

고정 slot은 `mfds-render-v1` 하나이며 검색어나 사용자/세션/배포 SHA/날짜로 새 slot을 만들지 않는다.

1. 관리자·Origin·CSRF·명시적 동의·키 설정을 먼저 검사한다.
2. 기존 DB의 직렬화 트랜잭션에서 slot을 읽고 없을 때만 시작 기록을 삽입한다.
3. **DB commit이 끝난 뒤에만** 공개 제품명 타이레놀/1페이지/3건/XML 조회를 시작한다.
4. 네트워크 중에는 DB 트랜잭션을 잡고 있지 않다. 동시에 들어온 요청은 저장된 상태만 반환한다.
5. 성공·HTTP 오류·시간 초과·XML 실패 결과도 이 slot에 정제하여 저장한다.
6. 프로세스 종료/저장 실패/응답 유실이면 result=NULL인 STARTED_OR_UNCERTAIN이 남는다.
   이 상태도 소비된 예산이며 **자동/수동 재전송으로 다시 조회하지 않는다**.

초기화/삭제/재실행/예산 갱신 API가 없다. 기능을 껐다 켜거나 재시작해도 동일 DB의 기록은 유지된다.
동일 영속 DB 유지가 전제다. 과거 백업 복원·새 DB 교체·수동 테이블 삭제로 기록이 사라지면
예산도 복원할 수 없으므로 검증 후에는 이 기능을 비활성화하고, 이 기록을 임의로 지우지 않는다.

## Render에서 나중에 사용자가 할 설정 (이번에 적용하지 않음)

먼저 현재 서비스가 Free·Docker·codex/mvp-completion이고 자동 배포가 꺼져 있는지 확인한다.
기존 Supabase의 가상 계정/자료가 유지되는 PostgreSQL 설정을 그대로 사용한다.

Render Dashboard → 해당 약이음 Web Service → **Environment**에서 준비할 항목:

| 항목 | 설정 |
|---|---|
| MFDS_API_KEY | 해당 의약품 서비스의 Decoding(일반) 인증키. 비공개 서버 환경변수에만 직접 입력 |
| YAKEUM_MFDS_PROBE_ENABLED | `1` (임시 검증을 명시적으로 켬) |
| YAKEUM_MFDS_PROBE_ADMIN_USERNAME | 본인이 소유하고 정상 로그인한 기존 약이음 계정 아이디와 정확히 일치 |

VITE_*에 키를 넣지 않는다. YAML value/채팅/스크린샷/로그/URL/명령행에 키를 넣지 않는다.
MFDS_API_KEY는 Render 프로세스 환경에서만 읽으며 브라우저 요청에서는 받지 않는다.
클라우드 개발 환경에 등록한 키가 Render에 자동 전달되는 것은 아니다.
기존 YAKEUM_DATABASE_URL, SSLROOTCERT, Origin, 보안 쿠키, 공유 입구, Gemini 관련 설정은 그대로 둔다.
기존 render.yaml은 키를 비우는 시연 초안이므로 Blueprint를 새로 적용해 기존 설정을 덮어쓰지 않는다.
유료 플랜·디스크·새 DB·Shell은 필요하지 않다.

**설정 저장이 재배포를 동반할 수 있다. 지금은 준비 목록만 확인하고 별도 승인 후 적용한다.**

## 배포와 클릭 순서 (배포/외부 실행 승인 후)

1. 검증한 최종 commit을 선택해 현재 서비스에서 수동 배포한다.
   현재 Render의 실제 배포 SHA/설정은 이 작업에서 조회하지 못했다.
2. 앱에서 지정한 기존 계정으로 로그인한다. 브라우저가 HTTPS와 기존 공유 입구를 정상 사용하게 둔다.
3. 로그인·저장 화면의 **식약처 관리자 검증 열기** 버튼을 누른다.
   서버의 관리자 상태 GET에 성공한 계정에서만 버튼이 나타나며, 앱 안에서 같은 인증 요청 함수를 사용한다.
   주소창 이동이나 토큰 복사/URL 전달은 필요 없다. 버튼을 열어도 실제 외부 조회는 실행하지 않는다.
   기존 보호 HTML `/api/dev-account/admin/mfds-probe/view`는 보존하지만 기본 진입 경로로 안내하지 않는다.
4. 페이지를 열거나 **저장된 상태 확인**을 눌러도 외부 API를 호출하지 않는다.
   UNUSED를 확인한다. 401은 로그인, 403은 지정 계정, 404는 활성화 설정/배포 버전을 확인한다.
   503이면 DB/비밀 설정 원인을 점검한다. 키는 화면에 입력하지 않는다.
5. 실제 호출을 승인받은 뒤 동의 체크박스를 선택하고 **실제 조회 1회 실행**을 한 번 누른다.
   서버 시작·화면 열기·타임라인·기존 업로드에서는 이 검증이 실행되지 않는다.
6. 응답이 느리거나 불명확하면 다시 실행하지 않는다.
   **저장된 상태 확인** GET만 사용한다. STARTED_OR_UNCERTAIN이면 추가 호출하지 않는다.
7. 정상/오류 결과 모두 안전한 JSON만 확인한다. 완료 후 페이지를 새로 열어도 실행 버튼은 잠긴다.
   이후 설정에서 YAKEUM_MFDS_PROBE_ENABLED=0으로 닫는 변경도 별도 승인 후 진행한다.

Render에서 성공할 경우에도 기존 앱의 공식 매칭을 live로 전환하지 않는다.
향후 사진/HIRA 실제 매칭 연결은 별도 작업이다.

## 별도 진단 API 계약

약 정보 공통 Schema/기존 API는 유지한다. ADMIN_MFDS_PROBE_V1은 별도 진단 envelope다.

| Method / 경로(모두 /api/dev-account/admin/mfds-probe 아래) | 의미 |
|---|---|
| GET /view | 관리자 화면, 외부 호출 없음 |
| GET /status | 저장된 실행 상태/결과 조회, 외부 호출 없음 |
| POST /execute | body는 정확히 `{"confirm":true}`. 고정 검색만 허용, 최초 1회만 조회 |

상태: UNUSED(consumed=false), STARTED_OR_UNCERTAIN(consumed=true), FINISHED(consumed=true).
FINISHED는 성공을 뜻하지 않는다. result의 api_success/xml_valid 또는 error/http_status를 확인한다.
POST 중복은 새 호출 대신 저장된 상태를 반환한다. 페이지가 보내는 CSRF 값은 기존 /me에서 얻는다.

결과에는 요청 시도 수·정상 API 응답 여부·XML·제품 필드 존재/성분/함량 개수·전체/반환 건수,
미수신 페이지 여부 또는 기존 정제 오류/헤더/본문 신호만 들어간다.
제품명/성분명·원문·키·요청 전체 URL·쿠키·내부 주소는 저장/표시하지 않는다.
단일 제품 후보가 사용자 자료의 성분/함량 검증 완료를 뜻하지 않는다.

## 검사와 한계

- SQLite: 비로그인/일반 사용자 차단, 비활성/설정 미비, CSRF/Origin, 동의/임의 인자 거절,
  성공/503/시간 초과/손상 XML, commit 전 실패, 결과 저장 실패, 동시 요청, 중단/새 세션 후 차단.
- PostgreSQL: loopback의 가상 DB `yakeum_synthetic`에서 기존 자료/권한과 신규 1회 검증을 검사했다.
  실제 Supabase는 접속하지 않았고 스키마 삭제/초기화도 하지 않았다.
- 브라우저: 실제 로그인·관리자 화면·동의·가짜 요청·안전한 결과·재조회/재로그인/로그아웃 차단,
  360/390/412/1280px 가로 넘침 없음. 테스트 서버 프로세스를 종료/재시작해도 모의 전송 누계는 1회다.
- 실제 Render 배포/HTTPS에서의 새 관리자 화면, 계정/키 설정, 실제 식약처 원본 응답은 미검증이다.
- DB가 보존되는 범위에서 최대 1회이며 원 서버에 도달했는지는 request_attempts만으로 확정하지 않는다.

### 실행한 명령과 결과

```sh
# 실제 키를 전달하지 않고 전체 백엔드 검사
MFDS_API_KEY='' GEMINI_API_KEY='' YAKEUM_GEMINI_LIVE_ENABLED=0 python -m pytest -q backend
# 495 passed, 37 skipped, 5 subtests passed

# loopback 가상 PostgreSQL만 명시적으로 선택(실제 주소는 쓰지 않음)
python -m pytest -q backend/tests/test_postgres_integration.py
# YAKEUM_TEST_POSTGRES_URL이 지정된 가상 환경에서 37 passed

# frontend 디렉터리
pnpm test
pnpm build
# 테스트 스크립트 10개 통과, tsc/Vite 빌드 통과(51 modules)

# 가짜 전송 서버를 먼저 켠 별도 환경
node frontend/tests/mfds-admin.browser.cjs
# 4개 그룹 통과
# 같은 가상 DB로 서버 프로세스를 종료/재시작 후
YAKEUM_MFDS_ADMIN_RESTART=1 node frontend/tests/mfds-admin.browser.cjs
# 4개 그룹 통과, /tmp의 숫자 전송 카운터는 여전히 1
```

실제 Python은 /tmp/yakeum-mfdstest/bin/python을 사용했다.
기본 backend 실행에서 제외한 37개가 별도 PostgreSQL 실행의 37개다.
subtests 5개와 브라우저 그룹은 독립 테스트 수로 합산하지 않는다.
기존 Starlette/httpx deprecation warning 1건(각 Python 실행)이 있었다.
가상 서버는 backend.tests.mfds_admin_fake_server를 명시적인 합성 환경에서만 사용하며
배포 Docker 이미지에는 테스트 서버/테스트 모듈을 복사하지 않는다.

2026-10-30 로그인 전달 방식 대조·앱 내 진입 검증: [MFDS_ADMIN_AUTH_REVIEW.md](MFDS_ADMIN_AUTH_REVIEW.md).
