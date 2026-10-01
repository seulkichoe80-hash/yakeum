# TASK D — Reconciliation·통합 개발 안내서

# 1. 내가 맡은 역할

나는 과거와 현재의 `MedicationRecord`를 비교하는 Reconciliation 핵심 엔진을 맡는다. TASK A의 추출 결과, TASK B의 정규화 결과, TASK C의 화면을 Backend/API 흐름으로 연결한다. 최신 자료에 약이 없다는 이유만으로 중단으로 판정하지 않고 `NEEDS_CONFIRMATION`을 반환해야 한다. 엔진은 의료적 판단을 하지 않고 정해진 데이터 비교 규칙만 수행한다.

# 2. 약이음 전체에서 내 기능의 위치

TASK A 정보 추출 + TASK B parsing·정규화 → **[TASK D: Reconciliation·Current Intake State·Backend 통합]** → TASK C Frontend

# 3. 3주 동안의 최종 목표

입력된 MedicationRecord가 Reconciliation과 Current Intake State 처리를 거쳐 Frontend에 전달되는 전체 경로를 만든다. 가족 구성원별 과거·현재 기록을 안전하게 비교하고 4개의 v1 상태만 반환해야 한다. A/B/C 기능을 연결하고 E2E 테스트와 배포 준비가 가능한 상태로 만든다.

# 4. 1주차 목표

가상 MedicationRecord로 가장 작은 Reconciliation PoC를 만든다.

흐름: previous + current → Reconciliation 결과

최소 Case와 기대 결과:

- 동일 성분·동일 함량 → `MAINTAINED`
- 이전 기록 없음·현재 존재 → `NEW`
- 동일 성분·함량 변화 → `DOSE_CHANGED`
- 과거 존재·최신 자료에서 확인되지 않음 → `NEEDS_CONFIRMATION`

완료조건:

- 네 Case가 독립된 테스트로 검증된다.
- 최신 미확인을 복용 중단으로 판정하지 않는다.
- `product_strength`와 `dose_per_administration`을 같은 값으로 취급하지 않는다.
- 새로운 상태값을 임의로 추가하지 않는다.

# 5. 2주차 목표

- Current Intake State를 구성한다.
- `family_member_id` 단위로 데이터를 분리한다.
- Timeline에 필요한 결과를 준비한다.
- 팀 합의된 계약 범위에서 Backend 기본 API를 연결한다.
- 누락 필드, 중복 입력, 미정규화 성분 등 예외를 처리한다.
- 필요한 API 변경은 먼저 `docs/API_CONTRACT.md` 협의 대상으로 보고한다.

# 6. 3주차 목표

- TASK A 추출 흐름을 연결한다.
- TASK B parsing·normalization 흐름을 연결한다.
- TASK C가 사용할 결과를 연결한다.
- 전체 E2E 테스트를 실행하고 통합 오류를 수정한다.
- 배포 준비사항을 정리하되 의료적 판단 기능을 추가하지 않는다.

최종 완료조건은 입력된 MedicationRecord가 Reconciliation을 거쳐 Frontend에 결과로 전달되는 전체 경로가 작동하는 것이다.

# 7. 내가 수정해도 되는 영역

주 수정영역:

- `backend/services/reconciliation/`
- `backend/api/`
- 통합 관련 테스트 영역
- 팀 합의가 끝난 공통 연결 영역

TASK A/B/C의 핵심 구현을 대신 수정하기보다 인터페이스 문제를 해당 담당자와 협의한다.

# 8. 임의로 수정하면 안 되는 영역

- TASK A의 `backend/services/extraction/`
- TASK B의 `backend/services/hira/`, `mfds/`, `normalization/`
- TASK C의 `frontend/`
- `AGENTS.md`
- `docs/DATA_SCHEMA.md`
- `docs/API_CONTRACT.md`

통합을 이유로 다른 담당자의 기능을 대규모 재작성하거나 API 계약을 독자적으로 확정하지 않는다.

# 9. 공통 데이터 규칙

모든 비교 입력은 `docs/DATA_SCHEMA.md`를 기준으로 한다. 성분 비교에는 normalized 값을 우선 사용하되 매칭되지 않은 값을 자동으로 동일하다고 확정하지 않는다. `product_strength`와 `dose_per_administration` 변화는 별도로 취급한다. Schema나 상태값 변경이 필요하면 코드로 우회하지 말고 팀장에게 먼저 알린다.

# 10. Git 작업방법

이 안내서 작성 단계에서는 branch를 만들지 않는다. 실제 작업은 다음 순서로 진행한다.

develop 최신화 → 자신의 feature branch 생성 → 작업 → 테스트 → commit → push → Pull Request → develop 병합

`main`에는 직접 commit하지 않는다. 통합 변경은 작은 단위로 유지하고 force push를 사용하지 않는다.

# 11. Codex 사용방법

VS Code에서 Codex에게 아래 프롬프트를 그대로 붙여넣고 시작한다.

```text
AGENTS.md를 가장 먼저 읽고 모든 규칙을 준수해줘.
그다음 docs/tasks/TASK_D_RECONCILIATION_INTEGRATION.md와 docs/DATA_SCHEMA.md를 읽어줘.
Reconciliation 및 통합 관련 기존 코드를 먼저 분석하고 바로 수정하지 마라.
먼저 다음을 보고해라.
1. 구현 계획
2. 수정 예상 파일
3. 구현 방법
4. 다른 기능에 미치는 영향
5. Schema/API 변경 여부
6. 테스트 방법
내 승인 전에는 구현을 시작하지 마라.
최신 자료 미확인을 복용 중단으로 판단하거나 새로운 상태값을 임의로 만들지 마라.
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
- Schema와 Reconciliation 상태를 임의로 변경하지 않는다.
- 다른 담당자의 기능을 대규모 수정하지 않는다.
- 테스트 실패 상태를 완료로 보고하지 않는다.
- AI나 Reconciliation 엔진이 진단, 처방, 복용량 변경, 복용 중단 또는 안전성 최종 판단을 하도록 구현하지 않는다.
