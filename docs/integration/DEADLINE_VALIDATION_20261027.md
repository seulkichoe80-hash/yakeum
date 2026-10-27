# 2026-10-27 마감 준비 검증

시작 기준 e8f05c60316b4a55831ac04e6814a0f041104ac3, codex/mvp-completion.
공통 MedicationRecord/ExtractionResult/HIRA v2 계약과 판정 정책 변경 없음.
추가 GET /api/health는 최소 liveness이며 외부 API/DB 준비 완료 확인이 아니다.

## 실제 실행

- `/tmp/yakeum-task-a-venv/bin/python -m pytest backend -q`: 348 passed, 5 subtests passed. 기존 Starlette 경고 1개. 하위 검사를 독립 테스트로 합산하지 않음.
- `pnpm --dir frontend test`: 기존 7개 검사 스크립트 통과(타입 검사 포함).
- `pnpm --dir frontend build`: 48 modules 빌드 성공.
- Docker 다단계 이미지 빌드 및 UID 10001 비root 실행 성공. 처음 발견한 소스 읽기 권한 오류는 이미지 내 읽기 권한 부여로 수정 후 재빌드/재검증.
- 빌드 화면/API 같은 주소에서 접속 성공. 테스트 컨테이너는 호스트 loopback 4205만 바인딩, 외부 공개 아님.
- 이름 있는 /data 볼륨의 모든 테이블 행 집계·내용 해시를 재시작 전후 비교해 일치. 실제 행/세션 값은 출력하지 않음.

실제 컨테이너 주소에서 아래 Playwright 스크립트를 실행했다.

| 스크립트(frontend/tests/) | 통과 검사 묶음 |
|---|---:|
| account-delete.browser.cjs | 13 |
| account-storage.browser.cjs | 7 |
| account-hira.browser.cjs | 10 |
| photo-upload.browser.cjs | 10 |
| photo-hira-integration.browser.cjs | 13 |

묶음 사이에 중복 흐름이 있으므로 독립 테스트 53개라고 표현하지 않는다.
환경: YAKEUM_TEST_URL=http://127.0.0.1:4205/, YAKEUM_TEST_PYTHON=위 Python,
YAKEUM_BROWSER_EXECUTABLE=/usr/bin/chromium, YAKEUM_PLAYWRIGHT_MODULE=설치된 Playwright 절대 경로.
각 실행은 `node frontend/tests/<스크립트>`.
사진 후보 수정/B/D/별도 복용/타임라인, HIRA 정상·보류·재처리·0건,
가족 변경·취소·늦은 응답, 계정 접근 거부·로그아웃·재로그인·삭제를 확인했다.
360/390/768/1280 폭 가로 넘침 없음, 런타임 오류 0, 외부 API 요청 0.
컨테이너 초기 기동 실패 중의 브라우저 접속 실패는 해결 후 위 5개 스크립트 모두 다시 통과했다.

## 미실행/제한

- 실제 Gemini 분석/모델 목록/MFDS 조회 0회. 가짜 추출/공식 매칭으로만 검증.
- GitHub Actions workflow는 추가했으나 원격 실행 성공은 이 로컬 검사 결과에 포함하지 않음.
- 실제 사용자 참여 시험, 새 최종 시연 영상, 외부 공개 URL, 운영 배포 미실행.
- 계정·SQLite는 개발용. 운영 인증/암호화/동의·보관·백업 정책 완료 아님.
- 이미지 태그와 전이 의존성 완전 고정, 운영 취약점 감사는 별도 필요.
- 비밀값·실제 자료·DB·영상·node_modules·빌드 산출물은 commit 대상 제외.
