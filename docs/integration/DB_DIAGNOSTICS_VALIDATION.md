# DB 오류 안전 분류 검증

2026-10-28 한국 시간. 시작 codex/mvp-completion / 27e16c49263d1499d5ee2aac322c7aee0cecc665.
전체 원격 fetch 후 local/origin 일치, clean. 사용자가 알려 준 Render 배포 기준과 Git commit을 대조했다.
실제 Render의 배포 상태·원격 DB 오류 원인은 아직 직접 확인하지 않았다.

## 범위

- 기존 psycopg 오류 처리에 고정 category/phase WARNING 로그 추가.
- 설정/연결/초기화/조회/commit 단계 구분. SQLSTATE 우선, 연결 문자열 메시지는 메모리 내 휴리스틱만 사용.
- DNS/네트워크/인증/SSL/권한/초기화/버전/연결 수/제약/시간 초과/미확인 분류.
- 예외 원문/traceback/SQL/DSN/host/비밀번호/쿠키/사용자·약 정보/원시 SQLSTATE는 로그에 포함하지 않음.
- 기존 사용자용 503 응답과 원격 SSL verify-full, 가족별 소유권/CSRF·입구 보호를 유지.
- 새로운 DB 요청/진단 endpoint/스키마 reset 명령/자동 재시도를 추가하지 않음.

## 실제 검사

- `python -m pytest backend/tests/test_db_diagnostics.py backend/tests/test_postgres_config.py backend/tests/test_demo_deployment.py -q`: 55 passed.
- 명시적 loopback 폐기용 가상 DB URL로 `python -m pytest backend -q`: **445 passed + 5 subtests passed**.
  SQLite와 로컬 PostgreSQL 회귀 포함, 기존 Starlette deprecation 경고 1개.
  이 테스트는 실제 Supabase URL을 쓰지 않았고 원격 스키마 삭제/초기화를 실행하지 않았다.
- 새 분류 검사 29개는 가짜 예외/가상 버전만 사용하며 비밀 마커가 로그 메시지·인자·traceback에 없음을 확인.
- UI/공통 Schema/API 계약/의존성은 수정하지 않았다. 프론트·실제 배포 브라우저 검사는 이번에 반복하지 않음.
- Render Dashboard 설정 변경·재배포·실제 Supabase 접속·Gemini/MFDS 분석/조회는 실행하지 않음.

로컬 Docker 이미지 build 성공. 이미지 내 가짜 SSL 예외 분류를 실행해
`YAKEUM_DB_FAILURE category=SSL_CERTIFICATE phase=CONNECT`만 표준 오류 로그로 출력됨을 확인했다.
빌드 완료 전 smoke를 먼저 실행한 1차 시도는 이미지 미생성으로 실패했고, 빌드 완료 후 재실행에 성공했다.
이 이미지를 Render에 직접 게시하거나 실제 DB에 연결하지 않았다.
실제 오류 원인은 사용자가 새 commit을 재배포하고 기존 화면 요청 1회 후 category/phase를 확인해야 한다.
재배포/각 분류별 조치는 deploy/DB_DIAGNOSTICS.md를 따른다.
