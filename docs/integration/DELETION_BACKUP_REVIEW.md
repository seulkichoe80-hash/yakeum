# 개발용 저장 결과 삭제·백업·사용 흐름 점검

2026-10-27. codex/mvp-completion 시작 `21db82bf2658c71655b3b826c7ca99b05e6eb51b`, clean.
전체 원격 fetch 후 새 변경 없음. 기존 작업·팀원 브랜치·main/develop 보존.

## 삭제 기능과 데이터 범위

저장 결과 상세의 '이 사진/HIRA 저장 결과 삭제' → 가족·자료 종류·저장 시각·자료 ID와 삭제 범위 확인 →
'삭제 취소' 또는 '이 사진/HIRA 결과 삭제 확인'. 확인 전에는 DELETE 요청을 보내지 않는다.

- 사진: 해당 runs의 원본/수정/정규화/비교 snapshot·검토 내용과 연결 intake를 한 transaction에서 삭제.
- 사진 documents는 다른 saved/미저장 run이 같은 문서를 참조하지 않을 때만 정리한다.
  공유 중인 임시 후보는 남을 수 있다. 기존 15분 유효기간/다음 업로드의 만료 정리와 초안 24시간 정리를 유지한다.
- HIRA: 해당 hira_runs의 원본 행/정규화/비교 또는 보류 snapshot과 연결 hira_intake를 함께 삭제.
- 사진/HIRA 테이블과 소유 가족을 구분한다. 다른 결과·다른 가족·계정·세션을 삭제하지 않는다.
- 삭제 후 목록/상세에서 제거하고 재조회·재저장·복용 수정은 404. 삭제된 사진과 같은 현재 업로드 결과도 무효화한다.
- 진행 중 상세 응답은 abort/세대 번호로 차단한다. 가족 변경/로그아웃 시 상태를 제거한다.
- 삭제는 DB의 논리적 행 제거다. 디스크의 물리적 완전 삭제나 기존 백업까지의 삭제를 보장하지 않는다.

기존 공통 MedicationRecord/Normalization/Reconciliation 의미와 사진/HIRA 저장 응답은 유지한다.
추가 API(같은 세션·Origin·CSRF·소유권 검사):

- DELETE /api/dev-account/families/{family}/runs/{run}: 저장 사진만. {deleted:true,source_type:PHOTO,run_id}.
- DELETE /api/dev-account/families/{family}/hira-runs/{run}: 저장 HIRA만. {deleted:true,source_type:HIRA,run_id}.

임의 다른 가족/자료/종류의 ID는 404, 미로그인 401, Origin/CSRF 오류 403.
미저장 초안 전체 삭제/계정 삭제/가족 삭제/법적 보관기간 정책을 이번에 구현한 것은 아니다.
SQLite schema는 기존 버전 2 그대로다. 자식 복용 기록을 먼저 지우고 부모 결과를 지워 FK 일관성을 유지한다.
처리 실패 시 전체 transaction을 rollback하는 검사도 포함한다.

## 현재 저장 위치와 보관 상태

활성 DB는 YAKEUM_DEV_DB_PATH의 저장소 밖 절대 경로다. 기본 DB/자동 운영 저장은 없다.
현재 계정/가족, 비밀번호 scrypt hash, 해시 세션/CSRF, 임시 사진 후보, 사진/HIRA snapshot과 복용 확인을 저장한다.
사진/XLSX bytes와 파일명은 저장하지 않는다. raw 정보는 기존 계약의 제한된 값과 source_rows 참조다.
DB 파일은 0600, 새 폴더는 0700이다. 파일 권한은 디스크/백업 암호화를 대신하지 않는다.
현재 SQLite/로그인은 개발용이며 실제 건강정보를 넣지 않는다.

명시적 저장 결과의 자동 보관기간은 확정하지 않았다. 임시 후보/미저장 run의 기존 정리는 개발 동작이다.
운영 보관기간, 동의·탈퇴·삭제 요청, 백업 보존/파기, 복원 시 삭제 재적용은 별도 결정 사항이다.

## 가상 데이터 백업·복원 방법

새 도구는 HTTP에서 DB를 내보내지 않는다. 개발 PC/서버의 파일 접근 권한이 있는 진행자만 실행한다.
백업은 가족 하나가 아니라 **전체 개발 DB**를 포함한다. 따라서 사용자 화면의 가족 권한과 다르다.
계정 hash와 가상 자료도 민감하게 취급하고 Git/채팅/공개 저장소에 올리지 않는다.

기존 개발 환경을 활성화하고 다음처럼 실행한다. 출력은 반드시 소스 저장소 밖의 새 절대 경로다.

```bash
export YAKEUM_DEV_ACCOUNT_ENABLED=1
export YAKEUM_APP_MODE=development
export YAKEUM_DEV_DB_PATH=/workspace/.local/yakeum/synthetic-test.sqlite3

# 가상 데이터만 있는 DB인지 확인한 후 실행
python -m backend.storage.dev_backup backup \
  --output /tmp/yakeum-backups/synthetic-20261027.sqlite3 --synthetic-only

# 복원은 서버를 멈춘 뒤 새 파일로만. 기존 활성 DB를 덮어쓰지 않음
python -m backend.storage.dev_backup restore \
  --source /tmp/yakeum-backups/synthetic-20261027.sqlite3 \
  --output /tmp/yakeum-restored/synthetic-restored.sqlite3 --synthetic-only
```

- SQLite backup API로 일관된 사본 생성, integrity_check/foreign_key_check와 버전 1/2 구조 검사.
- source는 read-only로 열고 기존 출력 파일은 덮어쓰지 않는다. 새 파일은 0600.
- 백업과 복원 사본에서 sessions/attempts를 제거한다. 원본 DB 세션은 그대로이며 복원 후에는 다시 로그인해야 한다.
- 백업은 현재 남아 있는 snapshot·별도 복용 확인·계정/가족·초안을 보존한다. 자동 주기/암호화/외부 보관 기능은 없다.
- 복원 후 새 파일의 가상 자료를 검토하고 YAKEUM_DEV_DB_PATH를 새 경로로 바꿔 앱을 재시작한다.
  도구는 활성 DB 설정을 자동으로 바꾸지 않는다. 이전 DB는 별도로 보존한다.
- --synthetic-only는 진행자의 확인이며 실제 건강정보를 자동 판별하는 기능은 아니다.
- 삭제 **전** 백업을 복원하면 삭제한 과거 결과가 다시 들어올 수 있다. 삭제 후 새 백업은 삭제 결과를 반영한다.
  과거 백업을 자동 수정/파기하거나 삭제 표식을 재적용하는 운영 기능은 미구현이다.
- VACUUM으로 사본의 현재 데이터를 정리하지만 SSD/파일시스템/다른 사본의 물리적 완전 삭제는 보장하지 않는다.

## 현재 확인한 것과 운영에 필요한 것

| 영역 | 개발 환경 구현 | 운영 전 필요한 결정/검증 |
|---|---|---|
| 접근 | 세션·소유 가족·CSRF·Origin | HTTPS/Secure cookie, 인증 복구, 권한 위임·감사 |
| 저장 | 로컬 SQLite·파일 권한 | 볼륨 지속성, 전송/디스크/백업 암호화·키 관리 |
| 백업 | 수동 새 파일 사본·검사·복원 | 주기/보존기간·운영자 접근·별도 보관·복구 목표와 훈련 |
| 삭제 | 선택 snapshot/연결 복용의 논리적 삭제 | 법적/동의 정책, 안전 파기·백업 내 삭제/복원 재적용 |
| 사용자 시험 | 자동 브라우저 점검·시험 키트 | 실제 참여자의 사용성 시험, 동의/피드백·문제 수정 |

운영 정책은 이번에 확정하지 않았다. 실제 Gemini/MFDS 호출·건강정보·운영 배포도 없다.
[5~20명 가상 자료 시험 안내](../testing/USER_TEST_KIT.md)와 익명 피드백 CSV를 준비했지만 실제 참여자는 아직 없다.

## 실제 검증 결과

- 백엔드 전체 **332 passed**, 내부 subtest 5 passed(독립 수에 합산하지 않음), 실패/xfail 0.
  기존 Starlette deprecation 경고 1개. 새 삭제·백업 검사 13개 포함.
- 본인 삭제/삭제 후 404/재저장 차단, 타인·다른 가족·미로그인·CSRF·Origin 차단,
  사진/HIRA 분리, 공유 후보 참조 보존, 삭제 실패 시 자식 기록 rollback 검사 통과.
- 가상 DB backup/restore 함수 검사와 실제 CLI 명령 모두 통과. 원본 DB는 그대로이며 새 사본만 생성.
  사진/HIRA/가족/복용 값 보존, 로그인 세션 제외, 덮어쓰기·잘못된 파일·운영 모드 거부,
  삭제 전/후 백업 차이와 활성 DB 비변경 확인.
- 프론트 기존 7 script 그룹, strict TypeScript/Vite build 통과(48 modules).
- 새 삭제 브라우저 **13개 그룹**, 기존 계정 저장 **7개**, HIRA 저장 **10개**, 사진 업로드 **10개**,
  사진 Mock/HIRA **13개 그룹** 통과. 그룹 간 중복 범위가 있어 독립 테스트 총계로 합산하지 않는다.
- 새 삭제 브라우저는 실제 사진/정상 HIRA/보류 HIRA 등록→저장→로그아웃/재로그인→조회→취소/삭제,
  삭제 후 목록·상세 제거, 현재 사진 작업 결과 재표시 차단까지 확인했다.
- 360/390/768/1280px 가로 넘침 없음, runtime errors 0, 실제 외부 의료 API 요청 0.
  삭제 확인 화면을 /tmp에서 열어 확인했다. 실제 참여자 수 0명, 사용자 시험 완료 판정은 하지 않는다.
- 시험 키트의 샘플 생성 명령을 실행해 합성 PNG와 XLSX 4종을 생성했다.
- pip check / git diff --check 통과. DB·백업·샘플 이미지/XLSX·screenshot은 Git에 넣지 않는다.

```bash
# 저장소 루트, 프로젝트 Python 환경
python -m pytest backend -q
python -m pip check
pnpm --dir frontend test
pnpm --dir frontend build

# 최신 backend 8043, Vite 4202 -> 8043, 가상 QA DB를 별도로 설정해 실행
export YAKEUM_TEST_URL=http://127.0.0.1:4202/
export YAKEUM_TEST_PYTHON=/tmp/yakeum-task-a-venv/bin/python
export YAKEUM_BROWSER_EXECUTABLE=/usr/bin/chromium
export YAKEUM_PLAYWRIGHT_MODULE=/opt/codex/runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright
node frontend/tests/account-delete.browser.cjs
node frontend/tests/account-storage.browser.cjs
node frontend/tests/account-hira.browser.cjs
node frontend/tests/photo-upload.browser.cjs
node frontend/tests/photo-hira-integration.browser.cjs
```

최종 QA DB는 /tmp/yakeum-delete-final/accounts.sqlite3.
CLI 백업 시험은 별도 가상 DB /tmp/yakeum-delete-qa/accounts.sqlite3에서
/tmp/yakeum-backup-validation/synthetic-backup.sqlite3 및 synthetic-restored.sqlite3 새 사본으로 실행했다.
운영 백업 주기·암호화·실제 건강정보/사용자 권한·삭제 재적용·실제 참여자 시험은 미완료다.
