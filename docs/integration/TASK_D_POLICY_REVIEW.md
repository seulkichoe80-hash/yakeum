# TASK D 정책 비교 및 push 전 점검

기준: 2026-10-19, `codex/task-d-weekly-integration`의
`f7e0db7dae081ffa3523e09197953691e1b17f95`. 기존 검증 commit을 되돌리거나
덮어쓰지 않고 후속 변경을 추가한다. 공통 상태/Schema/API 의미는 변경하지 않는다.

## 1. 실제 checkout·원격 상태

- 시작 HEAD는 f7e0db7이며 작업 트리는 깨끗했다.
- fetch 후 A `fa475cf`, B `0721848`, 기존 codex 통합 브랜치는 이전과 같았다.
- C만 `f2f107a` → `d797bc89de5e0fad001d9d152a81f1ff8df9875e`로 전진했다.
  실제 diff는 성분 입력의 접근성 이름/원본 설명 연결, 이미지 파일 미리보기·
  오류 포커스·저장소 불변 브라우저 검사와 작업 문서 보완이다.
- B 0721848, C f2f107a와 기존 codex 통합 단계는 f7e0db7의 조상이다.
  A fa475cf와 C d797bc8은 조상이 아니다. 이번에는 C 최신 commit을 통째로
  병합하지 않았다. 특히 D의 panel ID namespace, 취소/응답 차단을 보존한다.
- 다른 컴퓨터의 미푸시 변경은 확인할 수 없다.

## 2. 검증 집계와 증거 대조

전체 검사를 다시 실행하지 않고 `pytest --collect-only -q`로 **214개 수집 항목**을
확인했다. 다음 합계와 이전 실행 결과/문서가 일치한다.

| 검사 파일 | 수집 항목 |
| --- | ---: |
| HIRA parser | 11 |
| MFDS client (Mock 응답 검사) | 11 |
| normalization adapter / d_repro / normalization | 29 / 4 / 7 |
| repeat_report / structured_input_design / team_decisions / week2_3 | 5 / 17 / 16 / 12 |
| B-D-C API / B-D integration | 12 / 11 |
| Current Intake / extraction contract / extraction provider | 18 / 15 / 5 |
| photo demo / reconciliation | 27 / 14 |
| 합계 | **214** |

`test_extraction_provider.py`의 잘못된 이미지 검사 안에 `subTest` 3개,
설정/호출 오류 정제 검사 안에 2개가 있다. 따라서 이전 출력
`214 passed, 5 subtests passed`는 **214개 독립 수집 항목 + 그 안의 하위 실행 5개**다.
독립 테스트 219개로 합산하지 않는다. 매개변수화된 pytest 사례는 214에 포함한다.

f7의 브라우저 결과는 통합 8개 그룹, 단독 이미지 검토 4개 사례,
360/390/768/1280px, runtime errors 0과 일치한다. 이전 증거는 실행 콘솔과
`LOCAL_PHOTO_VALIDATION.md`의 기록 및 추적 중인 테스트 assertions이다.
별도의 영상·스크린샷·Playwright trace 보관을 주장하지 않는다.

이번 최소 UI 수정 후에는 관련 범위만 재검사했다.

- 백엔드 정책 관련 6개 파일: **78 passed + 5 subtests**, 실패 없음.
  전체 214개를 재실행하지 않았다. 백엔드 구현은 변경하지 않았다.
- 프론트 `pnpm test`, strict 타입 검사·Vite build: 통과, 43 modules.
- 통합 브라우저: 기존 8개 + 혼합 실패 후보 보존 1개 = **9개 그룹 통과**.
- 단독 브라우저: 기존 **4개 사례·가족 reset·키보드 통과**.
- 두 브라우저 모두 네 화면 크기에서 가로 넘침 없음, runtime errors 0.
  통합 검사는 기존 외부 폰트 요청 9개를 차단했고 외부 API 시도는 0이었다.
- 기존 Starlette TestClient deprecation warning 1개는 실패와 구분한다.

## 3. 실제 동작·위험·기존 합의·권장 처리

아래에서 사진은 LOCAL_MOCK 연결 경로, HIRA는 기존 B→D 경로를 뜻한다.

| 항목 | 실제 현재 동작과 위험 | 기존 합의 | 권장 처리 / 계약 영향 |
| --- | --- | --- | --- |
| 반복 조제 | 사진은 repeat group 발견 시 양쪽 자료 전체 비교 보류. HIRA는 원본을 모두 D에 전달한다. 이전 1/현재 2는 NEEDS_CONFIRMATION+NEW×2, 양쪽 2는 미확인×2+신규×2로 갈라진다. 반대 방향인 이전 2/현재 1은 입력 순서상 먼저 만난 기록이 유지로 연결될 수 있어 비대칭이다 | 반복행·조제일 보존, 임의 삭제/축약 금지. B 그룹 함수는 진단이며 대표 선택 합의가 아님 | 식별자·시점 범위를 먼저 확정하고 대표 선택 또는 그룹 비교를 협의. 자동 최신 1건 선택은 금지. 상태 Enum 변경 없이도 알고리즘 정책 합의가 필요하며, 전체 원본/대표 관계를 응답에 추가하면 API 합의 필요 |
| 동일 성분 복수 제품 | 서로 다른 mfds 제품 ID/약품코드의 두 제품은 같은 성분이어도 합쳐지지 않는다. 실제 실행에서 미확인+신규, repeat group 0을 확인. 같은 성분만으로 묶으면 다른 제품을 잘못 소거할 위험 | 성분만으로 동일 제품을 확정하지 않음. 제품 함량과 투약량 구분 | 이 동작 유지. 제품 간 자동 병합을 추가하려면 별도 정책/근거 필요. 지금 계약 변경 없음 |
| 성분·함량 미확인 | 사진은 누락·빈 성분·미확정 식별/부분 매칭을 별도 처리 보류. HIRA는 PARTIAL/UNMATCHED도 D로 보내고, 비교할 수 없는 값을 변화 없음으로 처리해 SAME_INGREDIENT_SAME_STRENGTH가 붙을 수 있음 | null은 0/false와 다름. 미확인 값 추측 금지. NEEDS_CONFIRMATION은 최신 자료에서의 미확인이라는 뜻 | HIRA에 사진과 같은 사전 검사/설명 전달 방식을 제안하되 공통 사유 의미를 임의 변경하지 않음. 비교 보류를 기존 NEEDS_CONFIRMATION에 끼워 넣지 않는다. 새 사유/보류 응답 구조는 계약 결정 |
| record:null·후보 일부 실패 | 사진 서버는 원본/정규화 결과를 보존하고 전체 비교 보류. HIRA는 FAILED를 review_results에 남긴 뒤 제외하고 나머지를 비교. 현재 실패행의 원래 약을 모르면 과거 약이 최신 자료에 없다고 오인할 수 있음. 실제 이전 1/현재 실패 1에서 NEEDS_CONFIRMATION을 재현 | FAILED와 Reconciliation NEEDS_CONFIRMATION은 다른 의미. 실패 자료와 확인 가능한 원본 보존 | null 기록의 수동 생성·재처리는 미합의. 실패 후보의 범위를 식별 못하면 자료 전체 또는 연결된 양쪽 그룹을 보류하는 정책 협의. 공통 review_results를 실패 이외 의미로 재정의하지 않음. 부분 실패 가시성 오류만 아래 최소 수정 |
| 재업로드·중복 기록 | HIRA는 파싱된 행 내용 hash와 UUID5로 ID 안정화, 동일 행은 occurrence suffix로 모두 보존. 사진 서버는 같은 가족/문서/순번에 같은 ID, UI 새 추출은 새 문서 UUID. 동일 문서 UUID를 이전/현재 양쪽에 내면 보류. 실제 파일 hash를 보내지 않으므로 같은 이미지 재업로드를 탐지하는 기능은 없음 | 시스템 ID 생성. 출처별 source_record_id 및 출처 간 중복 정책은 TODO. 재업로드와 반복 조제는 다름 | 같은 요청 재시도와 새 업로드, 같은 약의 새 조제를 분리해 결정. A/B UUID namespace를 임의 통일하지 않으며 ID가 같다는 이유로 원본 삭제하지 않음. 지속적 중복 처리에는 별도 식별/수정 이력 계약 필요 |

코드 근거:

- `reconciliation/engine.py`: 식별 우선순위, 동률 회피, null 비교, 고정 사유.
- `reconciliation/b_integration.py`: FAILED 제외, PARTIAL/UNMATCHED 포함.
- `normalization/repeat_report.py`, `adapter.py`, `tests/test_team_decisions.py`:
  진단 그룹, source key/UUID5, 반복행·원본 보존.
- `normalization/d_repro/cases.json`, `d_repro/README.md`: R1~R4 가상 사례.
- `api/photo_demo.py`, `tests/test_photo_demo.py`: 보류 gate, 원본·수정·정규화
  분리, 중복 review/문서 검사, ID retry 및 가족 범위.
- `frontend/src/imageReviewModel.ts`: 후보별 확인 상태와 혼합 실패 처리.

R1~R4와 반대 방향 반복, 다른 제품 동일 성분, 현재 행 실패를 이번에 실제
함수로 실행했다. 새 의료/대표 선택 정책을 정한 결과가 아니라 관찰 기록이다.

## 4. 전체 보류와 문제 후보만 보류의 차이

| 방식 | 장점 | 위험·선행조건 |
| --- | --- | --- |
| 자료 전체 비교 보류 | 실패행의 정체를 몰라도 잘못된 사라짐/신규 판정을 막기 쉽다. 현재 사진 Mock 방식 | 정상 후보도 비교 결과를 못 봄. 원본·정규화 미리보기는 계속 제공해야 함 |
| 문제 후보만 제외 | 정상 후보의 결과를 빨리 볼 수 있음. 현재 HIRA는 FAILED 행을 제외하는 방식 | 제외한 현재 후보의 상대 과거 기록이 미확인으로 바뀔 수 있음. null record는 어느 과거 약과 연결되는지 몰라 안전한 제외 범위를 정할 수 없음 |
| 연결된 양쪽 그룹을 함께 보류 (제안) | 신뢰할 수 있는 제품 ID가 있으면 영향 범위를 줄일 가능성 | 충돌 없는 그룹 식별, 이전/현재 대응 범위, 입력 완전성, 보류 원본 참조와 UI 설명을 먼저 합의해야 함. 성분명만으로 그룹화 불가 |

**권장 순서:** 우선 HIRA 실패/비교 불가 진단을 설계하고 보류 응답 계약을 합의한다.
그다음 확실히 식별 가능한 그룹에 한해 양쪽 영향 범위를 닫는 부분 보류를 검토한다.
식별 불가 null 후보가 있으면 전체 보류를 유지하는 안을 제안한다. 이는 미확정
제안이며 이번에는 HIRA 비교 방식이나 사진 보류 범위를 변경하지 않았다.

## 5. 기존 합의 안에서 고친 오류

정상 1개+FAILED 1개를 reducer에 넣으면 이전에는 `phase=failed`,
`candidates=[]`가 되어 정상 후보까지 화면에서 사라졌다. 비교 전체 보류와
원본 후보 숨김은 다른 문제다.

최소 수정:

- 혼합 응답은 정상/실패 후보를 모두 표시하며 원본 배열을 변경하지 않는다.
- 실패 후보의 errors를 표시하고 확인 버튼을 비활성화한다. reducer에서도
  강제 confirm을 거부하므로 수동 입력으로 실패를 성공으로 바꾸지 않는다.
- 전부 실패한 기존 오류·재시도 화면은 유지한다.
- 자료 전체 보류, user_confirmed 의미, 공통 상태/Schema/API는 유지한다.
- unit test로 원본 불변·정상 확인·실패 강제 확인 차단을 검증했고,
  브라우저의 가상 혼합 응답으로 실제 두 카드와 오류/버튼 상태를 확인했다.

## 6. push 대상 점검과 다음 우선순위

검사 범위는 현재 branch가 origin의 기존 refs에 없는 commit과 blob 버전,
후속 변경 파일, 전체 추적 파일명이다. 토큰/개인키/인증 URL/국내 개인 식별 패턴은
일치한 값 자체를 출력하지 않고 위치·종류만 검사한다. 테스트 데이터는 가상
family UUID·제품·기관·자료임을 코드와 fixture에서 확인한다.

`.env`, node_modules, dist, 캐시, 로컬 실행 결과는 push 대상에 포함하지 않는다.
새 업로드 이미지·영상·환자 파일은 없다. 기존 원격에 있는 프로젝트 흐름도 PNG는
이번 신규 blob이 아니다. 문서에 키 값이나 실제 개인정보를 넣지 않는다.

f7 보존 여부와 일반 push의 원격 SHA 일치는 push 후 별도로 확인한다.
검사·정책 검토 기록을 새 commit으로 보존하며 main/develop 병합, force push,
PR 생성은 하지 않는다.

다음 구현 우선순위:

1. HIRA의 비교 불가/부분 실패 보류와 사유 전달 계약 결정.
2. 신뢰 ID 기반 양쪽 그룹 보류 및 반복 대표 선택 기준 결정.
3. 문서/후보 수동 복구와 재업로드·출처 간 중복 식별 정책 결정.
4. C d797bc8의 접근성·이미지 검사를 D의 namespace/취소 기능과 충돌 없이
   별도 선별 반영. 이번 push를 최신 C 전체 통합 완료로 표현하지 않는다.

실제 Gemini/MFDS·DB·인증·배포는 이번에 실행하거나 추가하지 않았다.
