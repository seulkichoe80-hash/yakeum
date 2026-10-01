# TASK C — Frontend 개발 안내서

# 1. 내가 맡은 역할

나는 사용자가 가족별 복용정보를 등록하고 확인하는 웹 화면을 맡는다. AI 인식 결과를 사용자가 수정·확정할 수 있게 하고 현재 복용목록, 변경사항, Timeline, 공식 근거를 이해하기 쉽게 보여준다. Frontend에서 약물 상태를 자체 판정하지 않고 Backend와 TASK D의 결과를 표시한다. 의료적 조언처럼 보이지 않도록 표현에도 주의한다.

# 2. 약이음 전체에서 내 기능의 위치

TASK A 정보 추출 + TASK B 정규화 → TASK D Reconciliation·Backend → **[TASK C: 사용자 확인·수정·복용정보 화면]**

# 3. 3주 동안의 최종 목표

사용자가 가족을 선택하고 자료를 등록하며, 현재 복용목록과 변경사항을 실제 Backend 데이터로 확인할 수 있는 화면을 만든다. AI 결과의 확인·수정, Timeline, 공식 근거, 확인필요 상태를 표현해야 한다. 모바일 화면과 오류·로딩·빈 상태까지 포함해 E2E 통합 가능한 상태로 만든다.

# 4. 1주차 목표

Backend가 준비되기 전까지 `docs/DATA_SCHEMA.md`를 따르는 가상 Mock 데이터로 작은 PoC를 만든다.

최소 화면:

- 가족 선택
- 현재 복용목록
- 자료 등록 영역

완료조건:

- 세 영역 사이의 기본 사용자 흐름을 확인할 수 있다.
- Mock 데이터가 MedicationRecord 필드와 충돌하지 않는다.
- 실제 개인정보나 건강정보를 사용하지 않는다.
- 유지·신규·함량변경·확인필요를 Frontend가 자체 계산하지 않는다.

# 5. 2주차 목표

- AI 인식 결과 확인·수정 화면을 만든다.
- 변경사항과 Timeline 화면을 만든다.
- `NEEDS_CONFIRMATION` 상태를 명확히 표시한다.
- 공식 근거를 표시할 영역을 준비한다.
- 복수 `ingredients`와 raw/normalized 값을 필요한 화면에서 구분한다.
- 접근성, 기본 반응형 레이아웃과 사용자 오류 메시지를 확인한다.

# 6. 3주차 목표

- Mock 데이터 연결을 실제 Backend API 연결로 교체한다.
- 모바일 화면을 확인한다.
- 로딩, 오류, 빈 목록, 부분 데이터 상태를 처리한다.
- TASK A의 사용자 확인 데이터와 TASK D의 Reconciliation 결과를 연결한다.
- 전체 E2E 테스트에 참여한다.

최종 완료조건은 사용자가 가족을 선택하고 실제 Backend 데이터로 복용목록과 변경사항을 확인하며 필요한 AI 결과를 수정·확정할 수 있는 것이다.

# 7. 내가 수정해도 되는 영역

주 수정영역:

- `frontend/`
- Frontend 관련 테스트 파일

Mock 데이터가 필요하면 Frontend 내부의 명확한 개발용 위치에 두며, 실제 개인정보를 사용하지 않는다.

# 8. 임의로 수정하면 안 되는 영역

- `backend/services/` 아래 각 담당자의 핵심 로직
- 공통 `backend/api/`
- `AGENTS.md`
- `docs/DATA_SCHEMA.md`
- `docs/API_CONTRACT.md`

화면 구현을 쉽게 만들기 위해 Backend 판정 로직이나 공통 데이터 계약을 임의로 바꾸지 않는다.

# 9. 공통 데이터 규칙

`docs/DATA_SCHEMA.md`를 기준으로 Mock과 실제 데이터를 처리한다. raw와 normalized 값, `product_strength`와 `dose_per_administration`, `null`과 `0`·`false`를 구분한다. Reconciliation 상태는 Backend 결과를 표시하며 Frontend가 새 상태를 만들지 않는다. 필요한 필드나 API가 없으면 임시 우회 필드를 추가하지 말고 팀장과 Backend 담당자에게 먼저 알린다.

# 10. Git 작업방법

이 안내서 작성 단계에서는 branch를 만들지 않는다. 실제 작업 시작 시 다음 순서를 따른다.

develop 최신화 → 자신의 feature branch 생성 → 작업 → 테스트 → commit → push → Pull Request → develop 병합

`main`에는 직접 commit하지 않는다. 생성된 빌드 결과와 `.env`를 commit하지 않는다.

# 11. Codex 사용방법

VS Code에서 Codex에게 아래 프롬프트를 그대로 붙여넣고 시작한다.

```text
AGENTS.md를 가장 먼저 읽고 모든 규칙을 준수해줘.
그다음 docs/tasks/TASK_C_FRONTEND.md와 docs/DATA_SCHEMA.md를 읽어줘.
Frontend 관련 기존 코드를 먼저 분석하고 바로 수정하지 마라.
먼저 다음을 보고해라.
1. 구현 계획
2. 수정 예상 파일
3. 구현 방법
4. 다른 기능에 미치는 영향
5. Schema/API 변경 여부
6. 테스트 방법
내 승인 전에는 구현을 시작하지 마라.
Frontend에서 의료적 판단이나 Reconciliation 판정 로직을 새로 만들지 마라.
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
- AI 또는 Frontend가 의료적 판단을 하도록 구현하지 않는다.
