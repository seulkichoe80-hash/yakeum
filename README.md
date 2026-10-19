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
