# 약이음 팀 개발 시작 안내서

이 문서는 TASK A, TASK B, TASK C 담당 팀원이 별도의 설명 없이 개발을 시작하고 3주간의 핵심 기능 개발과 E2E 통합까지 마칠 수 있도록 만든 공통 안내서입니다. 팀장은 TASK D(Reconciliation / Integration)를 담당합니다. 처음 참여했다면 위에서부터 차례대로 읽어 주세요.

프로젝트 기능 개발기간은 **3주**입니다. 3주 안에 핵심 기능과 E2E 통합을 완료하고, 이후 기간은 전체 검토, 오류 수정, 사용자 테스트, UI/UX 개선, 발표 준비와 Demo 안정화에 사용합니다.

## 1. 약이음은 어떤 프로젝트인가요?

약이음은 단순한 약 검색이나 복약알림 서비스가 아닙니다. 가족 구성원별로 여러 자료에 흩어진 복용정보를 한곳에 모아 다음 기능을 제공하는 프로젝트입니다.

- 과거와 현재 복용정보 연결
- 처방 변화 확인
- 약봉투·처방전·건강기능식품 같은 비정형 자료 구조화
- HIRA 「내가 먹는 약! 한눈에」 자료 구조화
- 식약처 등 공식 의약품 데이터 연결
- 가족별 Medication Timeline
- 과거·현재 기록의 Reconciliation

AI는 자료를 읽고 구조화하는 도구입니다. AI가 질병을 진단하거나 의약품을 처방하지 않으며, 복용 중단이나 용량 변경을 의료적으로 결정하지 않습니다. 불확실한 결과는 사용자가 확인하고 수정할 수 있어야 합니다.

## 2. 전체 작업 흐름

```text
[A - AI 문서인식]

약봉투 / 처방전 / 건강기능식품
              │
              ▼
       Multimodal AI
              │
              ▼
      ExtractionResult
              │
              └──────────────┐
                             ▼
[B - 데이터·정규화]     정규화 흐름

HIRA Excel ──→ Deterministic Parser
              │              ▲
              ▼              │
       MedicationRecord ◀────┘
              │
       공식 데이터 매칭
              │
              ▼
[D - 팀장 / 통합]

       Reconciliation
              │
              ▼
    ReconciliationResult
              │
              ▼
[C - Frontend]

가족 선택 / 현재 복용정보 / 변경사항 / Medication Timeline
```

TASK A의 결과도 TASK B의 정규화 흐름을 거쳐 TASK D로 전달될 수 있습니다. 모든 팀은 `docs/DATA_SCHEMA.md`와 `docs/API_CONTRACT.md`를 공통 기준으로 사용합니다.

## 3. 작업은 동시에 시작합니다

> **중요: A → B → C 순서로 앞 팀의 완료를 기다리는 프로젝트가 아닙니다. A, B, C, D가 모두 동시에 개발을 시작합니다.**

```text
개발 시작

A ─┐
B ─┼── 동시에 시작
C ─┤
D ─┘

첫 번째 통합

B → D → C

두 번째 통합

A → B → D → C
```

첫 번째 통합에서 `B → D → C`를 먼저 확인하는 이유는 HIRA Excel이 이미 구조화된 입력이기 때문입니다. AI 인식 정확도에 영향을 받지 않고 `MedicationRecord → Reconciliation → Frontend` 전체 흐름을 먼저 검증할 수 있습니다. 그다음 TASK A의 비정형 입력을 같은 흐름에 연결합니다.

### 개발 순서와 통합 순서는 다릅니다

- **개발 순서:** A/B/C/D가 동시에 시작합니다. 다른 담당자의 완료를 기다리지 않습니다.
- **통합 순서:** 안정적인 구조화 입력부터 연결하기 위해 `B → D → C`를 먼저 검증하고, 이후 `A → B → D → C`를 연결합니다.

### 3주 전체 Roadmap

#### 1주차 — 각 담당 기능의 독립 PoC

- TASK A: 비정형 자료 → Multimodal AI → `ExtractionResult`
- TASK B: HIRA Excel → deterministic parser → `MedicationRecord`
- TASK C: API Contract Mock → 가족 선택 → 현재 복용목록 → 자료 등록 UI
- TASK D: Previous/Current MedicationRecord → Reconciliation → `ReconciliationResult`

#### 2주차 — 실제 프로젝트 기능으로 확장

TASK A:

- 약봉투, 처방전, 건강기능식품 입력 처리
- 복수 `ingredients`와 record-level `confidence` 처리
- 사용자 확인·수정 흐름
- 실패 및 미확인 값 처리

TASK B:

- HIRA Parser 안정화
- 공식 의약품 데이터 연결
- 제품명·성분명 정규화
- `product_strength` 처리
- 공식 데이터 매칭 실패 처리

TASK C:

- AI 인식결과 확인·수정 화면
- 변경사항과 Medication Timeline
- 확인필요 상태와 공식 근거 표시 영역
- 가족별 데이터 구분

TASK D:

- Current Intake State
- `family_member_id` 단위 처리
- Timeline 연결
- Backend/API 연결 준비
- Reconciliation 예외처리

#### 3주차 — 통합 및 완성

- TASK A: `ExtractionResult`를 TASK B normalization 흐름에 연결
- TASK B: TASK A/HIRA 입력을 동일한 MedicationRecord 흐름으로 연결
- TASK C: Mock을 실제 Backend 데이터로 교체
- TASK D: TASK A/B/C 전체 연결과 E2E 통합
- 전체 공통: 오류처리, 빈 상태, 로딩 상태, 기본 모바일 대응, 통합 테스트, Demo 핵심 시나리오 검증

## 4. 담당 역할 한눈에 보기

| 담당 | 역할 | 상세 작업안내서 | 1주차 목표 |
| --- | --- | --- | --- |
| A | AI 문서인식 | [`docs/tasks/TASK_A_AI_EXTRACTION.md`](tasks/TASK_A_AI_EXTRACTION.md) | 비정형 입력 1건 → `ExtractionResult` |
| B | 데이터·백엔드 | [`docs/tasks/TASK_B_DATA_BACKEND.md`](tasks/TASK_B_DATA_BACKEND.md) | 가상 HIRA Excel → `MedicationRecord` |
| C | Frontend | [`docs/tasks/TASK_C_FRONTEND.md`](tasks/TASK_C_FRONTEND.md) | Mock → 가족·복용정보 기본 UI |
| D | Reconciliation·통합 | [`docs/tasks/TASK_D_RECONCILIATION_INTEGRATION.md`](tasks/TASK_D_RECONCILIATION_INTEGRATION.md) | MedicationRecord 비교 → `ReconciliationResult` |

## 5. 모든 팀원이 가장 먼저 읽을 문서

작업을 시작하기 전에 다음 순서로 읽습니다.

1. [`AGENTS.md`](../AGENTS.md) — 전체 개발규칙과 의료안전 원칙
2. `docs/TEAM_START_GUIDE.md` — 전체 작업 흐름과 공통 시작방법
3. [`docs/DATA_SCHEMA.md`](DATA_SCHEMA.md) — MedicationRecord 공통 데이터 규격
4. [`docs/API_CONTRACT.md`](API_CONTRACT.md) — 팀 간 데이터 전달 규격
5. 자신의 `docs/tasks/TASK_*.md` — 개인별 상세 개발 범위와 3주 목표

공통 문서와 자신의 TASK 문서가 다르게 보이면 임의로 해석하지 말고 팀장에게 먼저 공유합니다.

## 6. 처음 Repository 받기

GitHub Repository: [seulkichoe80-hash/yakeum](https://github.com/seulkichoe80-hash/yakeum)

이 Repository는 Private이므로 먼저 Collaborator 초대를 수락해야 접근할 수 있습니다. 접근 권한을 받은 뒤 Repository를 Clone하고, VS Code에서 Clone한 **Repository root**를 엽니다. 올바른 폴더를 열었다면 탐색기 최상위에 `AGENTS.md`가 보여야 합니다.

## 7. Git 작업 원칙

브랜치 역할은 다음과 같습니다.

```text
main       → 안정 버전
develop    → 팀 통합 개발 브랜치
feature/*  → 개인 작업 브랜치
```

팀원은 `main`이나 `develop`에서 직접 기능을 개발하지 않습니다. 실제 작업을 시작할 때 담당별 branch 이름은 다음을 사용합니다.

- TASK A: `feature/ai-extraction`
- TASK B: `feature/data-backend`
- TASK C: `feature/frontend`
- TASK D: `feature/reconciliation`

공통 작업 흐름:

```text
develop 최신화
→ 자신의 feature branch 생성
→ 개발
→ 테스트
→ commit
→ push
→ Pull Request
→ 검토
→ develop 병합
```

현재 변경사항이 있는 상태에서 임의로 branch를 바꾸거나 파일을 지우지 않습니다. `reset --hard`와 force push도 사용하지 않습니다.

## 8. Codex 첫 실행 방법

VS Code에서 Codex를 열고 아래 프롬프트를 그대로 붙여넣습니다. `TASK_*.md` 부분은 자신에게 배정된 실제 파일명으로 바꿉니다.

```text
이 Repository의 AGENTS.md를 가장 먼저 읽어줘.

그다음 다음 문서를 읽어줘.

- docs/TEAM_START_GUIDE.md
- docs/DATA_SCHEMA.md
- docs/API_CONTRACT.md
- 나에게 배정된 docs/tasks/TASK_*.md

나는 Git/GitHub 사용 경험이 많지 않다.

현재 Repository와 Git 상태를 먼저 확인해줘.

아직 기능 구현은 시작하지 마라.

먼저 다음을 보고해줘.

1. 현재 Repository root
2. 현재 branch
3. develop 최신 여부
4. working tree 상태
5. 내가 담당한 TASK
6. 내가 수정해도 되는 영역
7. 수정하면 안 되는 영역
8. 1주차 목표
9. 구현 계획
10. 예상 수정 파일
11. 테스트 방법
12. Schema/API 변경 필요 여부

상태가 정상이라면 develop 최신 상태를 기준으로 내 담당 feature branch를 만드는 방법을 안내하고 내 확인을 받은 후 작업을 시작해줘.

main과 develop에는 직접 기능 코드를 작성하지 마라.
기존 파일을 임의 삭제하지 마라.
reset --hard와 force push를 사용하지 마라.
DATA_SCHEMA.md와 API_CONTRACT.md를 임의 변경하지 마라.
실제 개인정보나 건강정보를 Repository에 저장하지 마라.
```

Codex가 계획과 영향범위를 보고하면 내용을 확인한 후 구현 시작 여부를 알려 주세요.

## 9. TASK A - AI 문서인식

TASK A는 약봉투, 처방전, 건강기능식품 등의 비정형 자료를 Multimodal AI로 읽어 MedicationRecord 후보를 만듭니다.

1주차 목표:

```text
가상·비식별 자료 최소 1건
→ Multimodal AI
→ ExtractionResult
→ MedicationRecord 후보
```

중요사항:

- 심평원 Excel은 TASK A 담당이 아닙니다.
- AI가 확인할 수 없는 정보는 추측하지 않고 `null`로 둡니다.
- `user_confirmed` 기본값은 `false`입니다.
- 공식 의약품 ID, DUR, 안전성 근거처럼 AI가 생성하면 안 되는 값을 임의 생성하지 않습니다.

상세문서: [`docs/tasks/TASK_A_AI_EXTRACTION.md`](tasks/TASK_A_AI_EXTRACTION.md)

## 10. TASK B - 데이터·백엔드

TASK B는 HIRA 「내가 먹는 약! 한눈에」 자료를 읽고 공식 의약품 데이터와 연결하여 정규화합니다.

1주차 목표:

```text
가상 HIRA Excel
→ deterministic parser
→ MedicationRecord
```

중요사항:

- HIRA Excel에는 AI를 사용하지 않습니다.
- 실제 본인이나 가족의 HIRA 파일을 Repository에 commit하지 않습니다.
- raw 데이터는 normalized 데이터로 덮어쓰지 않고 보존합니다.
- 공식 데이터 매칭에 실패해도 원본 MedicationRecord를 삭제하지 않습니다.

상세문서: [`docs/tasks/TASK_B_DATA_BACKEND.md`](tasks/TASK_B_DATA_BACKEND.md)

## 11. TASK C - Frontend

TASK C는 가족 선택, 자료 등록, 현재 복용정보, 변경사항, Medication Timeline, AI 결과 확인·수정 화면을 담당합니다.

1주차에는 Backend를 기다리지 않고 `docs/API_CONTRACT.md`의 Mock을 이용합니다.

```text
Mock
→ 가족 선택
→ 현재 복용목록
→ 자료 등록
→ 기본 화면 PoC
```

중요사항:

- Frontend에서 `MAINTAINED`, `NEW`, `DOSE_CHANGED`, `NEEDS_CONFIRMATION`을 직접 판단하지 않습니다.
- TASK D가 제공한 `ReconciliationResult`를 화면에 표현합니다.
- Mock 구조도 `DATA_SCHEMA.md`와 `API_CONTRACT.md`를 따라야 합니다.

상세문서: [`docs/tasks/TASK_C_FRONTEND.md`](tasks/TASK_C_FRONTEND.md)

## 12. TASK D - Reconciliation·통합

TASK D는 팀장이 담당합니다.

```text
MedicationRecord
→ Reconciliation
→ ReconciliationResult
```

TASK D는 Reconciliation Engine과 A/B/C 전체 연결을 담당합니다. 최신 자료에서 확인되지 않는 약을 복용 중단으로 판단하지 않고 `NEEDS_CONFIRMATION`으로 처리합니다.

상세문서: [`docs/tasks/TASK_D_RECONCILIATION_INTEGRATION.md`](tasks/TASK_D_RECONCILIATION_INTEGRATION.md)

## 13. 1주차 전체 성공 기준

1주차 목표는 각자 완성품을 만드는 것이 아닙니다. 다음 네 개의 작은 PoC가 각각 존재하면 성공입니다.

- TASK A: 비정형 입력 → `ExtractionResult`
- TASK B: HIRA → `MedicationRecord`
- TASK C: Mock → Frontend
- TASK D: MedicationRecord → `ReconciliationResult`

첫 번째 Vertical Slice 목표:

```text
HIRA
  ↓
MedicationRecord
  ↓
Reconciliation
  ↓
ReconciliationResult
  ↓
Frontend
```

이 흐름이 연결된 뒤 TASK A 결과를 TASK B 정규화 흐름 앞에 연결합니다.

## 14. 공통 금지사항

> **반드시 지켜야 합니다**
>
> - 실제 개인정보 commit 금지
> - 실제 건강정보 commit 금지
> - API Key·Secret commit 금지
> - `.env` commit 금지
> - `main` 직접 개발 금지
> - `develop` 직접 기능개발 금지
> - `DATA_SCHEMA.md` 임의 변경 금지
> - `API_CONTRACT.md` 임의 변경 금지
> - 다른 담당자 영역 대규모 수정 금지
> - AI 의료적 판단 구현 금지
> - 테스트 실패 상태를 완료라고 보고 금지
> - force push 금지

## 15. 막혔을 때

다음 상황에서는 코드로 임의 해결하거나 우회하지 말고 팀장에게 먼저 공유합니다.

- Schema 변경이 필요함
- API Contract 변경이 필요함
- 다른 담당자의 코드를 변경해야 함
- 공식 데이터 구조가 예상과 다름
- AI 결과가 Schema에 맞지 않음
- 개인정보·건강정보 처리 판단이 필요함
- 의료적 판단인지 여부가 애매함
- 담당 범위를 넘어서는 기능이 필요함

공유할 때는 현재 상황, 관련 파일, 예상 영향, 가능한 해결안을 함께 정리하면 빠르게 결정할 수 있습니다.

## 16. 작업 완료 보고

Codex 작업이 끝나면 다음 형식으로 결과를 보고합니다.

1. 최종 판정
2. 담당 TASK
3. branch
4. 변경 파일
5. 구현 기능
6. 테스트 결과
7. 발견 문제
8. 남은 문제
9. Schema/API 변경 필요 여부
10. 다른 팀원과 연동할 사항
11. commit SHA
12. push 여부
13. Pull Request 여부

## 17. TASK별 3주 전체 완료기준

아래 항목은 각 담당 기능이 3주 후 완료되었다고 판단하는 최소 기준입니다. 상세 구현범위는 반드시 자신의 TASK 문서를 함께 따릅니다.

### TASK A 완료기준

- 약봉투 입력을 처리한다.
- 처방전 입력을 처리한다.
- 건강기능식품 입력을 처리한다.
- 비정형 자료를 `ExtractionResult`로 전달한다.
- MedicationRecord 후보를 생성한다.
- 복수 `ingredients`에 대응한다.
- record-level `confidence`를 제공한다.
- 미확인 값은 추측하지 않고 `null`로 처리한다.
- 사용자가 결과를 확인하고 수정할 수 있다.
- 공식 의약품 정보와 안전정보를 AI가 임의 생성하지 않는다.
- 실패 상태를 명확히 처리한다.
- TASK B normalization에 연결 가능한 결과를 전달한다.
- 관련 테스트가 통과한다.

상세 구현은 [`docs/tasks/TASK_A_AI_EXTRACTION.md`](tasks/TASK_A_AI_EXTRACTION.md)를 따릅니다.

### TASK B 완료기준

- HIRA Excel을 deterministic parser로 처리한다.
- HIRA 입력에서 MedicationRecord를 생성한다.
- raw 값을 normalized 값으로 덮어쓰지 않고 보존한다.
- 제품명을 정규화한다.
- 성분명을 정규화한다.
- 공식 의약품 데이터와 매칭한다.
- `product_strength`와 단위를 올바르게 처리한다.
- 공식 데이터 매칭 실패를 안전하게 처리하고 원본 record를 유지한다.
- TASK A의 결과도 같은 normalization 흐름으로 처리할 수 있다.
- TASK D에 MedicationRecord를 전달할 수 있다.
- 관련 테스트가 통과한다.

상세 구현은 [`docs/tasks/TASK_B_DATA_BACKEND.md`](tasks/TASK_B_DATA_BACKEND.md)를 따릅니다.

### TASK C 완료기준

- 가족을 선택할 수 있다.
- 향후 가족 추가를 수용할 수 있는 화면·상태 구조를 사용한다.
- 자료 등록 화면이 있다.
- 현재 복용정보를 표시한다.
- AI 결과를 확인하고 수정할 수 있다.
- 변경사항과 Medication Timeline을 표시한다.
- `MAINTAINED`, `NEW`, `DOSE_CHANGED`, `NEEDS_CONFIRMATION`을 표시한다.
- 공식 근거 표시 영역이 있다.
- 오류, 빈 상태, 로딩 상태를 처리한다.
- Mock이 아닌 실제 Backend 데이터와 연결된다.
- 기본 모바일 화면에 대응한다.
- 관련 테스트가 통과한다.

Frontend는 Reconciliation 상태나 의료적 판단을 직접 만들지 않고 Backend의 `ReconciliationResult`를 표시합니다. 상세 구현은 [`docs/tasks/TASK_C_FRONTEND.md`](tasks/TASK_C_FRONTEND.md)를 따릅니다.

### TASK D 완료기준

TASK D는 팀장이 담당합니다.

- Previous/Current MedicationRecord를 비교한다.
- `MAINTAINED`, `NEW`, `DOSE_CHANGED`, `NEEDS_CONFIRMATION`을 처리한다.
- deterministic `reason_code`를 제공한다.
- `family_member_id` 단위로 처리한다.
- Current Intake State를 구성한다.
- Timeline과 연결한다.
- Backend/API를 통합한다.
- TASK A/B/C를 연결한다.
- E2E 테스트가 통과한다.
- Demo 핵심 시나리오가 안정적으로 작동한다.

최신 자료에 없다는 이유만으로 복용 중단으로 판단하지 않습니다. 이 경우 `NEEDS_CONFIRMATION`을 사용합니다. 상세 구현은 [`docs/tasks/TASK_D_RECONCILIATION_INTEGRATION.md`](tasks/TASK_D_RECONCILIATION_INTEGRATION.md)를 따릅니다.

## 18. 주차별 체크포인트

각 주 마지막에는 다음 질문에 답하고 결과를 팀에 공유합니다.

### 1주차 종료

- [ ] 내 기능이 독립적으로 최소 1건 작동하는가?
- [ ] 가상 또는 비식별 데이터만 사용했는가?
- [ ] PoC의 입력과 출력이 문서의 Contract를 따르는가?
- [ ] 실패한 테스트와 미완료 항목을 숨기지 않고 기록했는가?

### 2주차 종료

- [ ] 실제 프로젝트 Contract에 맞게 데이터를 주고받을 수 있는가?
- [ ] `DATA_SCHEMA.md`와 `API_CONTRACT.md`를 임의로 바꾸지 않았는가?
- [ ] 오류·미확인·매칭 실패를 안전하게 처리하는가?
- [ ] 다음 통합에 필요한 입력과 출력 예시를 담당자에게 공유했는가?

### 3주차 종료

- [ ] 내 기능이 다른 담당 기능과 연결되어 E2E에서 작동하는가?
- [ ] 오류, 빈 상태와 로딩 상태를 확인했는가?
- [ ] 통합 테스트와 핵심 Demo 시나리오가 통과하는가?
- [ ] 남은 문제와 제한사항이 완료보고에 기록되어 있는가?

## 19. 1주차 이후 작업을 계속하는 방법

1주차 PoC가 끝났다고 팀장 지시를 기다리며 작업을 중단하지 않습니다. 자신의 TASK 문서에 적힌 **2주차 → 3주차** 순서로 계속 진행합니다. 각 단계에서 공통 Contract와 담당 범위를 다시 확인합니다.

다만 다음 상황에서는 구현을 멈추고 팀장에게 먼저 공유합니다.

- `DATA_SCHEMA.md` 변경이 필요함
- `API_CONTRACT.md` 변경이 필요함
- 다른 담당자의 핵심 코드를 변경해야 함
- 의료안전 판단이 필요함
- 개인정보·건강정보 처리 문제가 있음
- 담당범위가 충돌함
- 통합 Contract와 실제 결과가 다름

## 20. Git과 Codex로 지속 작업하기

각 담당자는 처음 만든 자신의 feature branch에서 작은 단위로 다음 흐름을 반복합니다.

```text
구현 → 테스트 → git diff 확인 → commit → push
```

- TASK A: `feature/ai-extraction`
- TASK B: `feature/data-backend`
- TASK C: `feature/frontend`
- TASK D: `feature/reconciliation`

다른 사람의 branch에 직접 commit하지 않습니다. `main`과 `develop`에도 직접 기능 코드를 작성하지 않으며, `develop` 병합은 검토 후 수행합니다.

Codex를 사용할 때마다 처음부터 프로젝트를 설명할 필요는 없습니다. 대신 매 작업 시작 시 Codex가 다음 문서를 먼저 확인하도록 합니다.

1. `AGENTS.md`
2. `docs/TEAM_START_GUIDE.md`
3. `docs/DATA_SCHEMA.md`
4. `docs/API_CONTRACT.md`
5. 자신의 `docs/tasks/TASK_*.md`

그리고 구현 전에 다음을 먼저 보고하도록 요청합니다.

- 현재 Git 상태와 branch
- 현재까지 구현된 기능
- 이번 작업 목표
- 예상 변경 파일
- 다른 담당자에게 미치는 영향
- 테스트 계획

## 21. 기능 완료 후 절차

기능이 완료되어도 바로 `develop`에 병합하지 않습니다.

```text
기능 구현 완료
↓
테스트
↓
git diff 확인
↓
commit
↓
feature branch push
↓
완료보고
↓
팀장 검토
↓
Pull Request
↓
develop 병합
```

테스트 실패나 미해결 문제가 있으면 완료라고 보고하지 않고 완료보고에 정확히 기록합니다.

## 22. 3주 개발 종료 성공 기준

3주 개발 완료는 각 기능이 따로 동작하는 상태가 아니라 다음 E2E 시나리오가 연결되어 작동하는 상태를 뜻합니다.

### 시나리오 1 — HIRA 기반 첫 번째 Vertical Slice

```text
HIRA 자료
→ Parser
→ MedicationRecord
→ Reconciliation
→ ReconciliationResult
→ 가족별 Timeline·변경사항 화면
```

### 시나리오 2 — 약봉투·처방전 기반 두 번째 Vertical Slice

```text
약봉투 또는 처방전
→ AI Extraction
→ 사용자 확인
→ 공식정보 정규화
→ MedicationRecord
→ Reconciliation
→ Timeline 반영
```

### 시나리오 3 — 건강기능식품

```text
건강기능식품
→ AI Extraction
→ 사용자 확인
→ 복수 성분 구조화
→ 가족별 복용정보에 반영
```

약과 건강기능식품의 병용 가능 여부에 대한 의료적 판단을 AI가 임의 생성하지 않습니다. 공식 근거 또는 별도 안전 규칙이 확보된 범위만 처리합니다.

## 23. 3주 이후 단계

3주가 끝난 직후 새로운 기능부터 추가하지 않습니다. 다음 순서로 현재 결과의 품질과 Demo 안정성을 높입니다.

1. E2E 오류 수정
2. 데이터 정확성 검증
3. 사용자 테스트
4. UI/UX 개선
5. 의료안전 검토
6. Demo 안정화
7. 발표자료 준비
8. 사용자 테스트 결과와 KPI 정리

새 기능 제안은 위 검토 결과와 우선순위를 확인한 뒤 별도로 결정합니다.
