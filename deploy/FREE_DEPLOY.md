# 무료 가상 시연: Render Free Web Service + Supabase Free PostgreSQL

현재 권장안. 이전 유료 Render+disk 안내는 기록으로만 남기며 이번에는 유료 플랜/결제를 진행하지 않는다.
실제 서비스 생성·Supabase 접속·외부 공개는 별도 승인 전 하지 않는다. 가상 자료 전용이다.

## 달라지는 점

Render 무료 서버의 임시 파일은 재시작/재배포 때 사라질 수 있으므로 SQLite 파일을 두지 않는다.
화면/API는 기존 단일 Docker 이미지, 계정/가족/세션/사진/HIRA 원본 후보·수정·정규화·비교·복용 확인은
Supabase PostgreSQL의 전용 `yakeum_demo` 스키마에 저장한다. 이미지 원본은 DB에 저장하지 않는다.
로컬 기본 YAKEUM_STORAGE_BACKEND=sqlite는 유지한다. 기존 SQLite 파일을 자동 이동/삭제하지 않는다.
postgres 선택 시 다른 저장소로 자동 fallback하지 않는다. 초기 원격 DB는 새 가상 계정으로 시작한다.
기존 SQLite 자료를 옮기는 자동 데이터 마이그레이션/대응 백업 기능은 이번에 구현하지 않았다.

사진 보류 저장 제한, HIRA 보류와 비교 미실행 null/정상 0건 구분, 별도 복용 확인은 그대로다.
Supabase Auth/Storage/REST API를 새로 사용하는 것이 아니다. 기존 개발용 로그인과 서버 측 소유권 검사를 유지한다.
DB 변경은 공통 MedicationRecord/ExtractionResult/HIRA API 버전 의미를 바꾸지 않는다.

## 무료 범위와 중지 조건 — 최신 공식 확인은 미완료

현재 환경에서 https://render.com/docs/free 및 https://supabase.com/pricing 를 열려고 했으나
프록시 CONNECT 403으로 차단됐다. 아래 숫자는 과거 알려진 안내로, **현재 계정 적용/약정이 아니다**.
계정 화면을 볼 수 없으므로 결제수단 불필요/무료 이용 보장을 확인했다고 말하지 않는다.

| 서비스 | 확인할 무료 조건 | 실제 계정에서 확인할 것 |
|---|---|---|
| Render Free | 과거 유휴 약 15분 후 sleep, 월 750 free instance hours, 임시 파일시스템/영속 disk 없음 | 현재 시간/대역폭/빌드 한도, 지연 기동, 한도 소진 시 중지 여부, 결제수단/본인 확인 요구 |
| Supabase Free | 과거 프로젝트 DB 500MB, 조직의 활성 무료 프로젝트 2개, 약 7일 미활동 시 pause | 현재 DB·egress·연결 수/프로젝트 수 제한, pause/복구/보관 기간, 백업·복구 제공 여부 |

HTTPS 기본 주소는 플랫폼이 제공하는 기능을 활용할 계획이지만 실제 발급/접속은 아직 미검증이다.
무료 서버 첫 접속은 느릴 수 있다. 10/31·발표 전날 DB pause 상태를 직접 확인하고 시작 시간을 확보한다.
서버를 자동 ping해 무료 정책을 우회하거나 가짜 트래픽으로 깨우는 설정은 추가하지 않는다.
유료 업그레이드/디스크/IPv4 추가 요금/백업 add-on은 선택하지 않는다.
카드를 요구하거나 Free가 보이지 않으면 중단하고 화면(개인정보 가림)을 확인한 후 다음 방법을 판단한다.
Free 선택이어도 변경된 약관·제공 한도까지 무조건 $0이라고 보장할 수 없다. 결제 화면의 예상 청구가 $0인지 확인한다.

공식 확인 경로:
- https://render.com/docs/free / https://render.com/pricing
- https://supabase.com/pricing / https://supabase.com/docs/guides/platform/billing-on-supabase
- https://supabase.com/docs/guides/database/connecting-to-postgres
- https://supabase.com/docs/guides/platform/going-into-prod (무료/운영 한계 검토용)

## 준비된 코드와 연결 설정

- SQLite 기본 동작과 기존 파일·백업 CLI 유지. PostgreSQL에는 SQLite 백업 CLI를 쓸 수 없도록 명시적으로 거부.
- psycopg 3, 기존 SQL의 바인딩/충돌 방지/행 접근/가족 순서를 변환하는 작은 저장 어댑터.
- PostgreSQL 전용 스키마, 외래키/원자적 commit·rollback, 버전 2, 짧은 트랜잭션 직렬화.
- 준비된 statement를 끄고 연결 제한/오류를 정제하며, DB 오류 시 키/주소/SQL/자료를 응답에 포함하지 않음.
- 원격 PostgreSQL은 TLS verify-full과 CA 검증을 강제. URL에 sslmode=disable을 넣어도 우회하지 못함.
- `YAKEUM_PG_LOCAL_TEST=1`은 loopback 가상 PostgreSQL에만 허용하며 외부 시연 flag와 함께 쓰면 거부.
- `deploy/render.yaml`은 free 플랜·disk 없음·postgres 선택 초안으로 변경. 공식 Blueprint schema/계정 적용은 미검증.

| 서버 환경변수 | 설정 |
|---|---|
| YAKEUM_STORAGE_BACKEND | postgres |
| YAKEUM_DATABASE_URL | Supabase의 DB 연결 URI, **secret** |
| YAKEUM_PG_SSLROOTCERT | 선택: 신뢰할 Supabase CA 파일의 서버 경로. 기본 시스템 CA 사용 |
| YAKEUM_EXTERNAL_DEMO | 1 |
| YAKEUM_DEV_ORIGIN | 정확한 Render https://호스트, 끝 / 없이 |
| YAKEUM_DEV_COOKIE_SECURE | 1 |
| YAKEUM_DEV_ACCOUNT_ENABLED / YAKEUM_SERVE_FRONTEND | 각각 1 |
| YAKEUM_APP_MODE | development(운영 인증 아님) |
| YAKEUM_DEMO_GATE_USERNAME / YAKEUM_DEMO_GATE_PASSWORD | 공유 입구, 비밀번호 최소 20자 무작위 secret |
| YAKEUM_GEMINI_LIVE_ENABLED | 0 |
| GEMINI_API_KEY / MFDS_API_KEY | 빈 값 |

DATABASE_URL/DB 비밀번호를 프론트 VITE_* 변수, YAML value, 대화, 로그, 명령행 인자로 넣지 않는다.
Supabase anon/service_role API 키는 PostgreSQL 연결 비밀번호가 아니다. 이 앱에는 해당 API 키를 넣지 않는다.
전용 스키마를 Supabase Data API의 exposed schemas에 추가하지 않는다. anon/authenticated 역할에 권한을 주지 않는다.
DB 연결 역할은 서버 비밀이며 전체 권한이 클 수 있으므로 이 프로젝트는 가상 시연용 별도 프로젝트로만 만든다.
운영 최소 권한 역할/RLS/접근 감사·복구·백업 정책이 완성됐다는 뜻은 아니다.

## 가입·연결 순서 (사용자 실행, 실제 생성은 별도 승인 후)

1. **Supabase 가입 화면**에서 Free organization을 선택할 수 있는지 확인한다.
   결제/Pro를 선택하지 않는다. 계정 화면의 현재 무료 한도·카드 요구 여부를 확인한다.
2. 별도 가상 시연 프로젝트를 만들 계획을 세운다. 이름·지역(가능하면 Render와 가까운 지역)·DB 비밀번호를 정한다.
   실제 프로젝트 생성은 사용자가 확인하고 배포/외부 연결을 승인한 뒤 진행한다.
3. 프로젝트의 Connect 화면에서 **Postgres connection string → Session pooler**를 확인한다.
   Render의 네트워크와 맞는 IPv4 지원 경로를 우선 확인한다. 일반적으로 pooler의 사용자명은 프로젝트 참조를 포함한다.
   화면에 나온 host/user/port/database를 그대로 사용하며 기존 ITEM_SEQ/HIRA 약품코드와는 무관하다.
   Direct IPv6-only 주소가 안 된다고 유료 IPv4 add-on을 결제하지 않는다.
4. 연결 URI의 password 부분을 해당 DB 비밀번호로 설정한다. 예약문자는 URI percent-encoding이 필요하다.
   전체 주소를 채팅/스크린샷/GitHub에 보내지 않는다. Session pooler가 없거나 조건이 다르면 확인 후 진행한다.
5. 프로젝트의 SSL/인증서 안내를 확인한다. 시스템 CA로 검증되지 않으면 공식 CA 인증서를
   Render secret file에 등록하고 YAKEUM_PG_SSLROOTCERT를 그 경로로 지정한다. TLS 검증을 끄지 않는다.
6. **Render 가입 화면**에서 Free Web Service가 가능한지와 카드/본인 확인 요구를 확인한다.
   서비스를 아직 생성/배포하지 않고 표시된 조건만 확인한다.
7. 외부 연결·배포 승인을 받은 뒤 GitHub 저장소의 `codex/mvp-completion`과 검증 SHA를 선택한다.
   Docker runtime, **Free**, 단일 인스턴스, 자동 배포 off, **영속 disk 추가 없음**.
8. 위 환경변수를 입력한다. DB URI와 공유 입구 비밀번호는 Render secret 값으로만 입력한다.
   YAKEUM_DEV_DB_PATH는 PostgreSQL 모드에서 사용하지 않는다.
9. Render 서비스 URL이 정해지면 정확한 HTTPS Origin을 입력한다. `/api/health`가 200이어도 DB 준비 완료는 아니다.
   최초 로그인 요청이 성공해야 DB 연결/스키마 권한을 확인한 것이다. 실패하면 503으로 표시하고 원인부터 검사한다.
10. 입구 없는 화면/API 접근 거부, 가상 계정 가입→가족→사진/HIRA→저장→재로그인→삭제를 확인한다.
    Render 재시작/재배포 후 계정/자료 유지, 타인·타가족 거부, Supabase pause/복구 조건을 확인한다.
11. 모든 검사를 통과한 뒤 초대한 시험자에게만 링크/입구 자격증명을 안전한 경로로 전달한다.
    실제 약봉투/건강정보는 받지 않는다. 시연 후 프로젝트/자료 유지 또는 삭제 시점을 별도 결정한다.

## 로컬 가상 PostgreSQL 재현

실제 Supabase가 아닌 loopback의 폐기 가능한 PostgreSQL 17에서 검사한다.
`backend/tests/test_postgres_integration.py`는 명시적 테스트 URL이 없으면 skip하며,
localhost/127.0.0.1 + DB 이름 yakeum_synthetic만 허용한다. 각 테스트는 **그 가상 DB 전용 스키마만 초기화**한다.
다른 DB/실제 Supabase URL로 실행하지 않는다. 기존 개발 SQLite를 건드리지 않는다.
CI에도 비밀값 없는 가상 PostgreSQL 서비스를 추가했다. 실제 GitHub 실행 결과는 별도 확인이다.

실제 Supabase 연결, 무료 계정 화면, 원격 TLS/CA/IPv4·pooler/권한/자동 pause/외부 주소는 아직 미검증이다.
SQLite용 백업/복원 검증이 Supabase 백업 검증을 대신하지 않는다. 무료 DB의 백업/복구를 보장하지 않는다.

연결의 TCP 경로도 확인해야 한다. PostgreSQL은 HTTPS API 호출이 아니므로 실제 cloud 작업 공간에서
추후 검사하려면 pooler host의 PostgreSQL TCP 포트 허용과 TLS 신뢰가 필요하다.
HTTP 도메인 허용만으로 DB 연결이 된다고 판단하지 않는다. Render→Supabase의 해당 경로도 실제 배포 후 별도 검사다.
