# TASK B — 데이터·백엔드 개발 안내서

# 1. 내가 맡은 역할

나는 심평원 「내가 먹는 약! 한눈에」 저장파일을 정해진 규칙으로 읽고 `MedicationRecord`로 변환한다. 심평원 Excel은 구조화된 자료이므로 AI를 사용하지 않고 deterministic parser로 처리한다. 이후 식약처 공식 데이터와 연결하여 제품명·성분명·함량 등을 정규화한다. 매칭되지 않은 값은 버리지 않고 원본 그대로 보존한다.

# 2. 약이음 전체에서 내 기능의 위치

심평원 Excel 또는 TASK A 추출 결과 → **[TASK B: parsing·공식 데이터 매칭·normalization]** → TASK D Reconciliation·Backend 통합 → TASK C Frontend

# 3. 3주 동안의 최종 목표

심평원 형태의 비식별 입력자료 1건 이상을 deterministic parser로 읽어 공통 `MedicationRecord`로 변환한다. 식약처 공식 데이터 매칭과 정규화 결과를 제공하고, 실패한 매칭도 안전하게 표현해야 한다. TASK A 결과가 같은 normalization 흐름을 사용할 수 있고 TASK D에 결과를 전달할 수 있어야 한다.

# 4. 1주차 목표

가상 또는 충분히 비식별화된 심평원 형태의 Excel 샘플로 작은 PoC를 만든다.

흐름: Excel → deterministic parser → MedicationRecord

확인할 주요 원본 필드:

- 번호, 조제일자, 처방기관, 조제기관
- 제품명, 약효분류, 성분명, 약품코드
- 단위, 1회 투약량, 1일 투여횟수, 총 투약일수
- 안전성 서한, 항혈전제 여부

완료조건:

- 입력 1건 이상이 공통 구조로 변환된다.
- AI를 사용하지 않는다.
- `drug_code`를 String으로 보존한다.
- 원본 누락, 잘못된 날짜, Decimal 변환 실패가 명확히 처리된다.
- 실제 사용자의 심평원 원본파일을 Repository에 넣지 않는다.

# 5. 2주차 목표

- 식약처 공식 데이터 매칭을 연결한다.
- 제품명과 성분명을 정규화한다.
- `ingredients[].product_strength`와 단위를 공식 데이터로 보완한다.
- 약품코드의 선행 0과 원래 표현을 보존한다.
- 매칭 실패와 복수 후보를 자동 확정하지 않고 표시한다.
- 공식 근거와 출처 연결 방식을 TASK D와 협의한다.

# 6. 3주차 목표

- TASK A 결과도 동일한 normalization 흐름으로 처리할 수 있게 연결한다.
- Backend API 변경이 필요하면 TASK D 및 공통 계약 담당자와 먼저 협의한다.
- 정규화된 MedicationRecord를 TASK D Reconciliation에 전달한다.
- 통합 및 E2E 테스트에 참여한다.

최종 완료조건은 심평원 형태 입력 1건 이상을 공통 MedicationRecord로 변환하고 공식 데이터 매칭 결과 또는 명확한 매칭 실패 결과를 반환하는 것이다.

# 7. 내가 수정해도 되는 영역

주 수정영역:

- `backend/services/hira/`
- `backend/services/mfds/`
- `backend/services/normalization/`
- 해당 기능의 테스트 파일

`backend/api/`는 TASK D와 협의한 뒤 수정한다.

# 8. 임의로 수정하면 안 되는 영역

- TASK A의 `backend/services/extraction/`
- TASK D의 `backend/services/reconciliation/`와 공통 API
- TASK C의 `frontend/`
- `AGENTS.md`
- `docs/DATA_SCHEMA.md`
- `docs/API_CONTRACT.md`

공식 데이터 매칭에 편리하다는 이유로 공통 Schema를 독자적으로 바꾸지 않는다.

# 9. 공통 데이터 규칙

반드시 `docs/DATA_SCHEMA.md`를 기준으로 개발한다. 날짜는 `YYYY-MM-DD`, 약품코드는 String, 수량은 float 정밀도 문제가 없는 Decimal 방식으로 처리한다. `null`을 `0`, `false`, 빈 문자열과 혼동하지 않는다. raw 값을 normalized 값으로 덮어쓰지 않는다. Schema 변경이 필요하면 코드로 우회하지 말고 팀장에게 먼저 알린다.

# 10. Git 작업방법

이 안내서 작성 단계에서는 branch를 만들지 않는다. 실제 작업은 다음 순서로 진행한다.

develop 최신화 → 자신의 feature branch 생성 → 작업 → 테스트 → commit → push → Pull Request → develop 병합

`main`에는 직접 commit하지 않는다. 공용 파일 충돌이 예상되면 작업 전에 담당자와 협의한다.

# 11. Codex 사용방법

VS Code에서 Codex에게 아래 프롬프트를 그대로 붙여넣고 시작한다.

```text
AGENTS.md를 가장 먼저 읽고 모든 규칙을 준수해줘.
그다음 docs/tasks/TASK_B_DATA_BACKEND.md와 docs/DATA_SCHEMA.md를 읽어줘.
TASK B 관련 기존 코드를 먼저 분석하고 바로 수정하지 마라.
먼저 다음을 보고해라.
1. 구현 계획
2. 수정 예상 파일
3. 구현 방법
4. 다른 기능에 미치는 영향
5. Schema/API 변경 여부
6. 테스트 방법
내 승인 전에는 구현을 시작하지 마라.
심평원 Excel은 AI가 아닌 deterministic parser로 처리하고, 실제 환자 자료를 Repository에 추가하지 마라.
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
- 실제 건강정보나 심평원 원본파일을 commit하지 않는다.
- API Key, Secret, 비밀번호를 commit하지 않는다.
- `.env`를 commit하지 않는다.
- `main`을 직접 수정하지 않는다.
- Schema를 임의로 변경하지 않는다.
- 다른 담당자의 기능을 대규모 수정하지 않는다.
- 테스트 실패 상태를 완료로 보고하지 않는다.
- AI가 의료적 판단을 하거나 공식 안전정보를 임의 생성하도록 구현하지 않는다.
