# 약이음

약이음은 가족의 복용정보를 AI로 구조화하고, 사용자가 저장한 심평원 투약이력 및 식약처 공식 데이터와 연결해 시간에 따른 복용정보 변화를 확인하도록 돕는 웹서비스입니다. AI는 의료적 판단을 대신하지 않습니다.

## 핵심 서비스 흐름

정보 추출 → 사용자 확인 → 제품·성분·함량·단위 정규화 → 식약처 공식 데이터 매칭 → 과거/현재 Reconciliation → 사용자·가족 확인 → 현재 복용상태 및 Timeline

## Repository 폴더

- `frontend/`: 사용자 화면을 위한 작업 공간
- `backend/`: API, 데이터 모델, 서비스 및 백엔드 테스트 작업 공간
- `backend/services/extraction/`: 문서 정보 추출 영역
- `backend/services/hira/`: 심평원 투약이력 연계 영역
- `backend/services/mfds/`: 식약처 공식 데이터 연계 영역
- `backend/services/normalization/`: 제품·성분·함량·단위 정규화 영역
- `backend/services/reconciliation/`: 과거/현재 복용정보 비교 영역
- `docs/`: 팀 Task, 공통 데이터 초안, API 계약 문서
- `sample-data/`: 가상 또는 충분히 비식별화된 테스트 자료 안내
- `tests/`: 프로젝트 공통 테스트 작업 공간

## 담당영역

- TASK A / AI 문서인식
- TASK B / 데이터·백엔드
- TASK C / Frontend
- TASK D / 핵심엔진·통합

## 팀 개발 안내

- [팀 개발 전체 안내 (착수 → 3주 개발 → 통합)](docs/TEAM_START_GUIDE.md)
- [TASK A - AI 문서인식](docs/tasks/TASK_A_AI_EXTRACTION.md)
- [TASK B - 데이터·백엔드](docs/tasks/TASK_B_DATA_BACKEND.md)
- [TASK C - Frontend](docs/tasks/TASK_C_FRONTEND.md)
- [TASK D - Reconciliation·통합](docs/tasks/TASK_D_RECONCILIATION_INTEGRATION.md)

작업을 시작하기 전에 반드시 Repository 루트의 `AGENTS.md`를 먼저 읽고 공통 개발규칙을 확인하세요.

현재 TASK D 통합 브랜치는 **Mock 기반 1차 통합 시연**을 지원합니다. 가상 사진 후보 검토 → B 정규화 → D 비교 → 복용 확인·타임라인과 가상 HIRA XLSX 비교를 로컬에서 실행합니다. 실제 외부 API·DB·인증·배포 완료를 의미하지 않습니다.

- [실행 준비·설정 변수·3분 시연 순서](docs/integration/MVP_DEMO.md)
- [1차 MVP 마감 검토](docs/integration/MVP_CLOSEOUT_REVIEW.md)
- [HIRA 비교 보류 v2 — TASK D 통합안](docs/integration/HIRA_COMPARISON_HOLD_V2.md)

사진 파일을 로컬 서버로 업로드하고 가짜 AI 후보의 수정·정규화·비교까지 연결하는
[사진 업로드 검사 경로](docs/integration/PHOTO_UPLOAD_V1.md)를 추가했습니다.
자료 등록에서 **사진 업로드 연결 열기 (가짜 AI)**를 선택합니다.
이 경로는 가짜 추출·공식 조회를 사용합니다. 계정별 저장·로그인은 아래 개발용 기능에서만 제공합니다. 가상 사진만 사용하세요.

[개발용 로그인·가족 구분·저장 실행 안내](docs/integration/DEV_ACCOUNT_STORAGE_V1.md):
기능을 명시적으로 켜고 Git 밖의 SQLite 경로를 지정하면, 가상 계정의 가족별 사진 결과를
저장·다시 조회할 수 있습니다. 첫 화면의 **개발용 로그인·저장 열기**에서 사용합니다.
운영용 인증·저장 또는 실제 건강정보 사용 준비 완료를 뜻하지 않습니다.

개발용 계정에서 [HIRA 결과 저장·재조회](docs/integration/ACCOUNT_HIRA_STORAGE_V1.md)도
지원합니다. 가족별 사진/HIRA 목록은 분리되며 비교 보류와 정상 0건, 별도 복용 확인을 보존합니다.
SQLite v1은 기존 자료를 유지하는 v2 추가 마이그레이션을 적용합니다. 가상 자료 전용입니다.

저장 상세에서 사진/HIRA 결과를 확인 후 삭제할 수 있습니다.
[삭제 범위·가상 DB 백업/복원](docs/integration/DELETION_BACKUP_REVIEW.md),
[5~20명 가상 자료 사용자 시험 안내](docs/testing/USER_TEST_KIT.md)를 참고하세요.
실제 사용자 참여 시험과 운영 보안·백업·삭제 정책은 아직 완료하지 않았습니다.

[Gemini 사진 연결 준비](docs/integration/GEMINI_PHOTO_PREPARATION.md): 계정 사진 화면에서
Mock/Gemini 요청 경로를 구분합니다. 기본은 Mock이며 실제 분석·모델 조회는 검증하지 않았습니다.
서버 활성화·키·모델·호출 예산과 별도 승인이 필요합니다. 공식 약품 매칭은 계속 Mock입니다.

[10월 31일 핵심 개발·11월 8일 제출 계획](docs/integration/DEADLINE_PLAN_20261031.md)에서 필수/선택 작업과 외부 연동의 남은 조건을 확인하세요.
[컨테이너 실행·배포 준비](deploy/README.md)는 가상 자료 내부 시연용입니다. 공개 배포·운영 인증 완료를 뜻하지 않습니다.
[이번 통합 검증 결과](docs/integration/DEADLINE_VALIDATION_20261027.md)를 별도로 기록했습니다.

[Gemini 형태 가상 응답의 브라우저 검증](docs/integration/GEMINI_REPLAY_MFDS_VALIDATION.md)과 [식약처 실제 연결 준비·미확정 명세](docs/integration/MFDS_CONNECTION_PREPARATION.md)를 기록했습니다. 실제 식약처 연결은 아직 Mock입니다.
