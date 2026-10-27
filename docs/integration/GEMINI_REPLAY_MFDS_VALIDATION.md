# Gemini 형태 가상 응답 브라우저 + 식약처 오프라인 검증

2026-10-27. 시작 HEAD 6b6105a9c166200f1659d8b7da4cf654c8d388ae, clean,
전체 원격 fetch 후 origin/codex/mvp-completion과 일치. 다른 팀 브랜치는 변경하지 않음.

## 실제/가짜 구분

앞선 승인 시험에서 Gemini 분석 HTTP 1회가 200으로 성공했고 기대 항목 5개가 일치했다.
이번에는 그 응답 원문을 저장/재사용하지 않았다. 같은 공통 구조에 가상알파정·가상알파성분·100mg·
1회 2정·하루 2회·7일을 넣은 approved-shape 시나리오를 오프라인 harness에 추가했다.
이 데이터는 모델 인식 정확도의 추가 증거가 아니다. 이번 실제 Gemini/MFDS/모델 목록 호출 모두 0회.

SDK는 HTTPX MockTransport로 완전히 교체하고 테스트 전용 가짜 키·모델을 사용했다.
브라우저는 같은 로컬 주소 외의 요청을 차단했다. 실제 설정의 키를 테스트 서버에 전달하지 않았다.

## 실제 브라우저 조작

브라우저에서 가상 계정 가입 → 가족 선택 → 사진 파일 선택 → Gemini 경로(가짜 SDK 전송) → 후보 표시 →
현재 후보 투약량 2에서 3으로 수정/확인 → B 미리보기 → 정규화 확인/D 비교 → 사진 변경 이력 펼침 →
저장 → 상세 원본 2/수정 3/원본 user_confirmed=false/정규화 true 확인 → 별도 먹고 있음 저장 →
새로고침·로그아웃·재로그인·저장 재조회/이전·현재 타임라인 표시를 확인했다.
원본 수량 수정은 편집 기능 검사이며 실제 사용자 복용량 변경 권고가 아니다.

혼합 실패 보존/보류, 공급자 오류/시간초과/JSON 손상, 취소 후 늦은 응답,
가족 A→B→A 후 늦은 응답 차단, 다른 계정 접근 차단도 통과했다.
account-gemini.browser.cjs 13개 검사 묶음, 가짜 SDK 전송 9회, 실제 외부 API 0회.
360/390/768/1280 폭 가로 넘침 없음, 브라우저 런타임 오류 0.

## 최종 검사

- `/tmp/yakeum-live-venv/bin/python -m pytest backend -q`: 356 passed + 5 subtests passed, 기존 Starlette 경고 1개.
- `pnpm --dir frontend test`: 기존 7개 스크립트 통과.
- `pnpm --dir frontend build`: strict TypeScript + Vite 48 modules 성공.
- 별도 실제 앱 서버의 기존 브라우저 검사: account-delete 13, account-storage 7, account-hira 10,
  photo-upload 10, photo-hira-integration 13개 검사 묶음 모두 통과. 중복 흐름이므로 독립 테스트로 합산하지 않음.
- 식약처 transport 가짜 응답: 코드 체계 분리, 정상/없음/복수/오류/함량 null/구조 오류/목록 일부 누락/
  일부 서비스 실패/원본 보존/캐시·재시도 검사 포함.
- 실제 사용자 참여 시험과 실제 MFDS 검증, 운영 인증·저장·배포는 미완료.

## 재현

프로젝트 Python 설치 후 독립 임시 DB/시나리오 파일을 사용한다. 테스트 서버는 반드시 아래 테스트 전용
flag와 가짜 키·모델을 사용하며 일반 앱 서버에서 가짜 응답을 제공하지 않는다.

```bash
mkdir -p /tmp/yakeum-replay
printf normal > /tmp/yakeum-replay/scenario.txt
YAKEUM_GEMINI_TEST_TRANSPORT=1 GEMINI_API_KEY=synthetic-offline-key \
YAKEUM_GEMINI_MODEL=synthetic-offline-model YAKEUM_GEMINI_LIVE_ENABLED=1 \
YAKEUM_GEMINI_LIVE_MAX_REQUESTS=10 \
YAKEUM_GEMINI_FAKE_SCENARIO=/tmp/yakeum-replay/scenario.txt \
YAKEUM_DEV_ACCOUNT_ENABLED=1 YAKEUM_APP_MODE=development \
YAKEUM_DEV_ORIGIN=http://127.0.0.1:4215 \
YAKEUM_DEV_DB_PATH=/tmp/yakeum-replay/synthetic.sqlite3 YAKEUM_SERVE_FRONTEND=1 \
python -m uvicorn backend.tests.gemini_fake_server:app --host 127.0.0.1 --port 4215 --no-access-log
```

다른 터미널에서 YAKEUM_TEST_URL=http://127.0.0.1:4215/,
YAKEUM_GEMINI_FAKE_SCENARIO=/tmp/yakeum-replay/scenario.txt,
YAKEUM_GEMINI_REPLAY_APPROVED_SHAPE=1,
설치된 YAKEUM_PLAYWRIGHT_MODULE/YAKEUM_BROWSER_EXECUTABLE/YAKEUM_TEST_PYTHON을 지정하고
`node frontend/tests/account-gemini.browser.cjs` 실행.
서버 예산은 가짜 전송에만 쓰이며 실제 분석 승인을 늘리는 설정이 아니다.
재실행은 새 임시 경로로 분리한다. 9행의 .calls 파일은 해당 실행에만 속해야 한다.

공식 준비/미확정 매핑/호출 승인 조건은 MFDS_CONNECTION_PREPARATION.md 참고.
