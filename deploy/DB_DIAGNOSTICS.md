# Render DB 오류의 안전한 분류

2026-10-28 한국 시간. 배포 기준 27e16c4 이후 진단 로그만 추가한다.
실제 원격 DB의 원인은 아직 확인하지 않았다. 이 변경은 해결 완료가 아닌 안전한 진단 준비다.
SSL verify-full, 인증/가족 소유권/CSRF, 기존 데이터·API 계약을 변경하지 않는다.

## 로그에 남는 것

```text
YAKEUM_DB_FAILURE category=SSL_CERTIFICATE phase=CONNECT
```

고정된 category/phase만 WARNING으로 기록한다. 예외 원문·traceback·SQLSTATE 원문·SQL·요청·DSN·host·
DB명·비밀번호·쿠키·사용자/가족 식별자·약 정보는 넣지 않는다.
예외의 SQLSTATE를 먼저 분류하고 연결 단계에서는 libpq 메시지의 알려진 형태를 메모리에서만 검사한다.
메시지 형태에 따른 분류는 진단 단서이며 원인 확정이 아니다. 모르는 연결 오류는 CONNECTION_UNKNOWN이다.
프론트엔드의 기존 503 안내에는 내부 분류를 추가 노출하지 않는다.

처리 단계: CONFIG(설정 검사), CONNECT(DB 연결), INITIALIZE(기존 초기화 경로), QUERY(일반 읽기/쓰기),
COMMIT(트랜잭션 확정). 정상 요청에는 진단 오류 로그가 생기지 않는다.

| category | 의미 / 사용자가 확인할 항목 |
|---|---|
| CONFIGURATION | YAKEUM_STORAGE_BACKEND=postgres, 비밀 YAKEUM_DATABASE_URL의 URI 형식·필수값 확인 |
| DNS | Supabase Connect의 Session pooler host가 정확한지, placeholder/공백이 없는지 비공개로 확인 |
| NETWORK_TIMEOUT / NETWORK_UNREACHABLE | 프로젝트 running 여부, IPv4 지원 pooler·포트/접속 경로 확인. 유료 IPv4 add-on을 선택하지 않음 |
| AUTHENTICATION | DB 비밀번호·pooler 사용자명(프로젝트 참조 포함)을 비공개로 확인. Supabase 로그인 비밀번호/API 키와 혼동 금지 |
| SSL_CERTIFICATE | 인증서 체인·유효기간·hostname·신뢰 CA 파일을 확인. SSL 검증을 끄지 않음 |
| SSL_NEGOTIATION | 선택한 pooler endpoint/port의 TLS 지원과 올바른 DB 연결 경로 확인 |
| DATABASE_SELECTION | Connect 화면의 DB 이름 확인. 임의 DB를 새로 만들거나 기존 DB를 삭제하지 않음 |
| CONNECTION_LIMIT | 무료 DB/pooler의 연결 수와 다른 클라이언트 사용 확인. 유료 업그레이드를 자동 선택하지 않음 |
| SCHEMA_PERMISSION | 초기화 단계의 DB 역할 권한 확인. anon/service_role API 키가 DB 비밀번호가 아님. 무조건 권한 전체를 열지 않음 |
| SCHEMA_INITIALIZATION / SCHEMA_VERSION | 초기화 단계 또는 지원 버전 문제. 기존 schema/table을 DROP/TRUNCATE하지 말고 분류를 공유 |
| PERMISSION | 일반 조회/수정 단계의 DB 역할 권한 문제. 가족별 API 권한 검사와는 별개이며 권한 검사를 끄지 않음 |
| DATABASE_TIMEOUT | 명령 시간 제한/잠금 대기 관련. 반복 요청으로 몰아붙이지 않음 |
| CONSTRAINT | 중복 가입/외래키 등 제약 충돌. 중복 아이디 409와 함께 나타나는 것은 예상된 동작일 수 있음 |
| CONNECTION_UNKNOWN / QUERY_FAILED / COMMIT_FAILED | 현재 단서로 세부 원인 확정 불가. 고정 분류와 phase만 공유 |

## 재배포하고 확인하는 순서

1. Render Dashboard에서 해당 **yakeum Web Service**를 연다. Free·disk 없음·기존 환경변수는 유지한다.
2. Manual Deploy에서 **Deploy latest commit**을 선택한다. codex/mvp-completion의 진단 변경 commit인지 확인한다.
   처음부터 캐시 삭제/서비스 재생성/DB 초기화를 하지 않는다. auto deploy off를 임의로 바꾸지 않는다.
3. 배포가 Live가 된 뒤 웹 화면의 공유 입구를 통과해 개발용 로그인·저장을 **한 번** 연다.
   기존 계정·가족·DB 자료를 지우거나 신규 스키마 초기화 시험을 하지 않는다.
4. Render Logs에서 같은 시간대의 `YAKEUM_DB_FAILURE`를 찾는다.
5. **category와 phase가 들어간 해당 줄만** 전달한다. 전체 로그·환경변수 화면·DB 주소·키/비밀번호·쿠키를 복사하지 않는다.
6. 새 로그가 없으면 먼저 실제 배포 SHA, 해당 서비스/시간대, 화면에서 요청이 발생했는지 확인한다.
   /api/health 성공은 DB 연결 성공을 의미하지 않는다.

현재 환경에서는 Render Dashboard/비밀 설정을 직접 바꾸거나 실제 Supabase에 접속하지 않았다.
이 문서의 절차로 사용자가 재배포한 뒤 분류를 확인해야 실제 원인을 좁힐 수 있다.

## SSL_CERTIFICATE인 경우에만 필요한 설정

- 프로젝트의 SSL/인증서 안내에서 올바른 **공식 CA 인증서**를 확보한다. 다른 프로젝트/임의 인증서를 신뢰하지 않는다.
- Render의 Secret Files에 공식 CA 인증서를 추가한다(예: 파일명 `supabase-ca.crt`).
- Render에 표시된 실제 파일 경로를 `YAKEUM_PG_SSLROOTCERT` 환경변수에 지정한다.
  일반적인 예는 `/etc/secrets/supabase-ca.crt`지만 화면의 경로를 우선한다.
- CA 인증서는 비밀키가 아니며 **개인키·DB 비밀번호를 이 파일에 넣지 않는다**.
- 저장 후 Render가 재배포하는지 확인하고 같은 방식으로 한 번 검사한다.
- sslmode=disable/require로 검증을 낮추거나 YAKEUM_PG_LOCAL_TEST=1을 설정하지 않는다.
  URI의 sslmode를 바꿔도 앱은 원격 verify-full을 강제한다.

## 인증 오류인 경우에만 필요한 설정

Supabase Connect의 Session pooler URI를 비공개로 다시 확인한다. 사용자명·프로젝트 참조·DB 비밀번호가
맞는지와 URI 예약문자 인코딩을 확인해 Render의 YAKEUM_DATABASE_URL에 직접 저장한다.
무조건 비밀번호부터 초기화하거나 로그/채팅에 URI를 붙이지 않는다. 기존 사용자·가족 자료를 삭제하지 않는다.

## 검사 범위

원격 연결/데이터 읽기나 진단용 DB 초기화 명령은 실행하지 않는다.
가짜 psycopg 예외·가상 schema version으로 category/phase·비노출·기존 503·SSL 강제 유지를 검사한다.
전체 회귀의 PostgreSQL은 명시적인 loopback 전용 폐기 가능한 가상 DB만 사용한다.
실제 Supabase URL에서는 스키마 삭제·초기화 테스트를 절대 실행하지 않는다.
