# TASK A — AI 문서인식 개발 안내서

# 1. 내가 맡은 역할

나는 약봉투, 처방전, 건강기능식품처럼 표 형태가 일정하지 않은 이미지와 문서를 `MedicationRecord` 형태로 바꾸는 일을 맡는다. Multimodal AI가 읽은 결과를 바로 확정하지 않고, 사용자가 확인하고 수정할 수 있는 데이터로 전달해야 한다. 완벽한 OCR보다 원본값 보존, 실패 처리, 신뢰도 표시가 중요하다. 심평원 Excel은 내 담당이 아니며 TASK B가 deterministic parser로 처리한다.

# 2. 약이음 전체에서 내 기능의 위치

비정형 이미지·문서 → **[TASK A: AI 정보 추출 및 사용자 확인용 결과]** → TASK B 정규화·공식 데이터 매칭 → TASK D Reconciliation → TASK C Frontend

# 3. 3주 동안의 최종 목표

약봉투·처방전·건강기능식품 중 하나 이상의 비정형 입력을 공통 `MedicationRecord` Draft로 변환한다. 복수 `ingredients`, 원본 복용법, record-level `confidence`를 전달하고 인식 실패를 안전하게 표시해야 한다. 결과는 사용자가 수정·확정할 수 있으며 TASK B의 정규화 흐름과 Backend에 연결 가능한 상태여야 한다.

# 4. 1주차 목표

가상 또는 충분히 비식별화된 약봉투나 처방전 샘플 1건으로 작은 PoC를 만든다.

흐름: 이미지 → Multimodal AI → 구조화 JSON

최소 추출 대상:

- `product_name_raw`
- `ingredients` 후보
- `dosage_text_raw` 등 dose 관련 원문
- `source_type`
- record-level `confidence`

완료조건:

- 비식별 입력 1건이 구조화 JSON으로 변환된다.
- raw 값과 AI가 해석한 값을 구분한다.
- 필수값 누락과 인식 실패가 오류로 드러난다.
- Schema에 없는 정보가 발견되면 임의 필드를 추가하지 않고 보고한다.

# 5. 2주차 목표

- 건강기능식품 입력까지 확장한다.
- 복수 `ingredients`를 처리한다.
- 사용자가 AI 결과를 확인하고 수정할 수 있는 데이터 흐름을 준비한다.
- 읽을 수 없는 이미지, 필드 누락, 잘못된 형식 등 실패 처리를 추가한다.
- record-level `confidence` 처리 기준을 정리한다.
- 실제 개인정보나 건강정보가 아닌 테스트 자료로 검증한다.

# 6. 3주차 목표

- TASK B normalization에 전달 가능한 출력 형식을 맞춘다.
- TASK D 및 Backend와 연결해 추출 결과가 다음 단계로 전달되게 한다.
- TASK C가 사용자 확인·수정 화면에서 사용할 데이터를 협의한다.
- 전체 E2E 테스트에 참여하고 연결 오류를 수정한다.

최종 완료조건은 비정형 입력 1건 이상이 공통 `MedicationRecord` 구조로 변환되고, 사용자가 확인·수정할 수 있는 데이터 형태로 전달되는 것이다.

# 7. 내가 수정해도 되는 영역

주 수정영역:

- `backend/services/extraction/`
- 해당 기능의 테스트 파일
- 팀이 합의한 비식별·가상 샘플 영역

공통 영역이나 Backend API 수정이 필요하면 TASK B/D와 먼저 협의한다.

# 8. 임의로 수정하면 안 되는 영역

- TASK B의 `backend/services/hira/`, `mfds/`, `normalization/`
- TASK D의 `backend/services/reconciliation/`와 공통 API
- TASK C의 `frontend/`
- `AGENTS.md`
- `docs/DATA_SCHEMA.md`
- `docs/API_CONTRACT.md`

다른 담당자의 핵심 폴더를 편의를 위해 대규모 수정하지 않는다.

# 9. 공통 데이터 규칙

반드시 `docs/DATA_SCHEMA.md`의 MedicationRecord Schema v1 Draft를 기준으로 개발한다. raw 값은 normalized 값으로 덮어쓰지 않고, `product_strength`와 `dose_per_administration`을 구분한다. Schema를 임의로 바꾸거나 코드에 임시 필드를 만들어 우회하지 않는다. 변경 필요성을 발견하면 구현 전에 팀장에게 알리고 합의 결과를 기다린다.

# 10. Git 작업방법

이 안내서 작성 단계에서는 branch를 만들지 않는다. 실제 작업을 시작할 때 다음 순서를 사용한다.

develop 최신화 → 자신의 feature branch 생성 → 작업 → 테스트 → commit → push → Pull Request → develop 병합

`main`에는 직접 commit하거나 push하지 않는다. 다른 사람의 변경을 삭제하지 않고 force push를 사용하지 않는다.

# 11. Codex 사용방법

VS Code에서 Codex에게 아래 프롬프트를 그대로 붙여넣고 시작한다.

```text
AGENTS.md를 가장 먼저 읽고 모든 규칙을 준수해줘.
그다음 docs/tasks/TASK_A_AI_EXTRACTION.md와 docs/DATA_SCHEMA.md를 읽어줘.
TASK A 관련 기존 코드를 먼저 분석하고 바로 수정하지 마라.
먼저 다음을 보고해라.
1. 구현 계획
2. 수정 예상 파일
3. 구현 방법
4. 다른 기능에 미치는 영향
5. Schema/API 변경 여부
6. 테스트 방법
내 승인 전에는 구현을 시작하지 마라.
심평원 Excel parser는 TASK A 범위가 아니며, 실제 개인정보·건강정보를 Repository에 추가하지 마라.
```

# 12. 작업 완료 시 Codex 보고 형식

1. 최종 판정
2. 변경 파일
3. 구현 기능
4. 테스트 결과
5. 발견 문제
6. 남은 문제
7. Schema/API 변경 여부
8. 다른 팀원과 연동할 사항
9. commit SHA

# 13. 절대 하지 말아야 할 것

- 실제 환자 개인정보를 GitHub에 업로드하지 않는다.
- 실제 건강정보를 commit하지 않는다.
- API Key, Secret, 비밀번호를 commit하지 않는다.
- `.env`를 commit하지 않는다.
- `main`을 직접 수정하지 않는다.
- Schema를 임의로 변경하지 않는다.
- 다른 담당자의 기능을 대규모 수정하지 않는다.
- 테스트 실패 상태를 완료로 보고하지 않는다.
- AI가 진단, 처방, 복용량 변경, 복용 중단 또는 안전성 최종 판단 같은 의료적 판단을 하도록 구현하지 않는다.
