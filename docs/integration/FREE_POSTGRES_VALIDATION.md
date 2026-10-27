# 무료 배포용 PostgreSQL 저장 전환 검증

2026-10-27. 시작 codex/mvp-completion / 640d98e030b189b89238af082fa06e1e42d67f0d,
작업 트리 clean, 전체 원격 fetch 후 이후 원격 변경 없음. 기존 브랜치/SQLite/작업 기록 보존.
공통 데이터·API 상태 의미는 변경하지 않았다. 기존 원본/수정/정규화/비교/복용 확인 분리를 유지한다.

## 변경

YAKEUM_STORAGE_BACKEND=postgres와 서버 secret YAKEUM_DATABASE_URL로 선택하는 PostgreSQL 저장 경로 추가.
기본은 sqlite. 기존 SQLite 파일을 옮기거나 삭제하지 않으며 자동 자료 이전은 구현하지 않았다.
PostgreSQL은 별도 yakeum_demo schema, 외래키, 트랜잭션, 버전 2를 사용한다.
공유 입구와 개발용 로그인·세션·가족 소유권·CSRF는 유지한다. Supabase Auth로 전환한 것이 아니다.
연결 실패 시 원본 오류/주소/키/자료 없이 503을 반환하고 SQLite로 fallback하지 않는다.
원격 TLS 인증서 검증을 강제하고 로컬 전용 SSL 예외는 loopback 가상 DB에만 허용한다.
개발용 DB가 PostgreSQL일 수 있으므로 화면의 SQLite 전용 문구를 개발용 데이터베이스로 수정했다.

## 실제 실행

- `YAKEUM_TEST_POSTGRES_URL=<폐기 가능한 loopback 가상 DB> python -m pytest backend -q`:
  **416 passed**, 5 subtests passed, 기존 Starlette 경고 1개. SQLite 기존 검사와 PostgreSQL 통합 검사 모두 포함.
  환경변수가 없는 일반 실행에서는 PostgreSQL 통합 검사를 skip한다. skip을 통과로 계산하지 않는다.
- PostgreSQL 17 실제 로컬 컨테이너를 사용했다. Mock DB가 아니라 가상 계정/자료를 저장하는 실제 로컬 DB다.
  Supabase/외부 DB에는 접속하지 않았다. 테스트 초기화는 명시적 loopback + 이름 yakeum_synthetic만 허용.
- 기존 SQLite 전용 PRAGMA 검사를 PostgreSQL에 그대로 실행할 수 없어 새 PG 검사에서 동일한 삭제/재조회/
  자식 기록·고아 기록 없음/계정·가족 보존을 SQL로 확인했다. 기존 SQLite 검사 조건은 수정하지 않았다.
- 사진/HIRA 저장·독립 복용 확인·정상 0건/보류 null·타인·타가족 차단·중복 가입·DB 오류 정제 검사.
- PG trigger로 부모 삭제 오류를 유도해 자식 삭제까지 rollback되는 것을 확인했다.
- `pnpm --dir frontend test`: 기존 7개 스크립트 통과.
- `pnpm --dir frontend build`: strict TypeScript/Vite 48 modules 성공.
- 새 psycopg가 포함된 Docker 이미지 build 및 이미지 내부 psycopg import/기본 앱 시작 성공.
  이미지 sha256:54fafb0cb00ca0345797c55b313cf4db560e62b7d5a29e74affd2ac4400b154a.
  최종 이미지의 Supabase 원격 접속/TLS 성공을 확인한 것은 아니다.

## 실제 브라우저

같은 화면 빌드 + PostgreSQL을 선택한 FastAPI를 loopback 4245에서 실행했다.

| 스크립트 | 통과 검사 묶음 |
|---|---:|
| account-delete.browser.cjs | 13 |
| account-storage.browser.cjs | 7 |
| account-hira.browser.cjs | 10 |
| photo-upload.browser.cjs | 10 |
| photo-hira-integration.browser.cjs | 13 |

사진/HIRA 등록·정상/보류·후보 확인·별도 복용·저장·재조회·삭제·로그아웃/재로그인,
타인·타가족 거부·취소·가족 A→B→A·늦은 응답·360/390/768/1280 폭을 검사했다.
외부 API 요청/브라우저 런타임 오류 0. 묶음 간 중복이 있어 독립 테스트 수로 합산하지 않는다.
앱 프로세스 종료/재시작 전후 PostgreSQL 계정/세션/가족/사진/HIRA/복용 상태 내용 집계 해시 일치.
재시작 후 별도 Python 프로세스에서 가상 계정 로그인 및 저장한 사진 결과 조회 성공.
실제 자료·세션 값·비밀번호·DB URI는 출력하지 않았다.

## 설정/미검증

deploy/render.yaml은 Free, disk 없음, postgres 선택·DB URI 수동 secret·Gemini/MFDS 키 비움으로 변경.
로컬 YAML 구조 검사는 통과하지만 최신 공식 Blueprint schema·계정 적용은 미검증이다.
GitHub CI에는 폐기 가능한 PostgreSQL 서비스를 추가했다. 실제 원격 CI 성공은 별도 확인이다.
Render 무료 안내/Supabase 가격 공개 페이지는 프록시 CONNECT 403으로 차단됐다.
무료 한도/카드 요구/중지·복구 조건은 계정 화면·공식 안내에서 사용자가 확인해야 한다.

실제 Supabase 세션 pooler/IPv4/TCP/TLS·CA·프로젝트 권한/휴면·복구·무료 한도,
실제 Render 재시작/재배포/HTTPS·공유 입구 연결은 미검증이다.
운영 인증·암호화·자동 백업/원격 복원·삭제 정책 완료가 아니다. 가상 자료 전용.
이번 Gemini 분석/모델 목록/MFDS 호출은 모두 0회. 이전 합성 Gemini 1회 성공 기록은 유지한다.
실제 계정 생성·결제·외부 배포·공개는 하지 않았다.

가입/확인/연결 절차는 deploy/FREE_DEPLOY.md를 따른다.
