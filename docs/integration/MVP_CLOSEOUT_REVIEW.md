# TASK D 1차 MVP 마감 검토

검토일 2026-10-19. 시작 브랜치 `codex/task-d-weekly-integration`,
HEAD `ad3713c01ba792963e36696934e3082f479f4646`, 작업 트리는 깨끗했다.
해당 commit과 이전 검증본을 보존하며 후속 변경만 추가한다.

**최종 판정: Mock 기반 1차 통합 시연 가능.** 실제 외부 연동/서비스 출시 판정은 아니다.
이번 변경은 문서와 선택 필드 경계 회귀 테스트뿐이다. API/Schema/보류 조건/앱 코드는 변경하지 않는다.

## 1. 원격 팀원 변경 비교

기본 fetch refspec이 develop/TASK D에 한정되어 있어 `git fetch origin` 뒤
`git ls-remote --heads origin`으로 전체 원격 head를 확인하고 A/B/C를 명시적으로 fetch했다.
SHA·포함 관계·실제 diff/코드를 확인했으며 직전 검토 이후 새 tip은 없다.
팀원 PC의 미푸시 변경은 확인할 수 없다.

| 담당 | 원격 SHA | 현재 포함·필요성·위험 |
| --- | --- | --- |
| A feature/ai-extraction | fa475cf76bbd8d0dd09721dcb694dfa6409fdfb4 | 조상 아님. Gemini 호출/모델 열거·별도 dataclass 출력·중복 task-a 스크립트/미디어. 기존 common contract adapter의 codex/a-extraction-contract 4758dea는 포함. live 스크립트를 옮기면 기존 정규화 입력과 다른 스키마/import와 미디어가 유입되므로 이번 Mock 마감에 선별 반영할 새 오류 수정 없음 |
| B feature/data-backend | 0721848aab2c4e41765ebd8e529e02d20613fe55 | 조상으로 포함. HIRA parser, MFDS Mock/클라이언트, 정규화/adapter, 반복 진단·structured 설계/재현 사례 포함. 담당 핵심 디렉터리의 tip 대비 추가 파일은 승인된 D structured.py 연결 구현. 재복사/병합 불필요 |
| C feature/frontend | d797bc89de5e0fad001d9d152a81f1ff8df9875e | commit 전체는 조상이 아니나 f2f107a 이후 성분 입력 aria-label/original+error 설명 연결 및 브라우저 검사를 bd4af98에서 선별 반영. 실제 패널 diff로 확인. D panel ID namespace·mixed FAILED 보존·abort/late guard가 추가로 존재하므로 전체 파일 복사는 회귀 위험. C 지시서/과거 검증 문서는 덮어쓰지 않음 |

기존 codex/a-extraction-contract, b-to-d-integration, b-d-c-integration,
current-intake-ui, current-intake-ux-polish는 포함된 단계다. 원격 TASK D도 ad3713c로
시작 HEAD와 일치했다. 새 팀원 변경을 반영하거나 다른 브랜치를 수정하지 않았다.

## 2. v2 계약·코드·소비 화면 대조

| 항목 | 확인 결과·근거 |
| --- | --- |
| v1 호환 | main.py에 별도 v1/v2 경로·모델. pipeline 기본 version=1 유지. 기존 v1 정규화/엔진 경로 그대로이며 화면만 명시적 v2 요청. v1의 과거 제한도 그대로이므로 시연에서 v1을 쓰지 않음 |
| 미실행/0건 | hira_hold.py의 holds는 engine 호출을 건너뛰고 null/빈 intake 반환. 정상 empty는 기존 결과 객체 items=[] 반환. schemas.py 불변 조건 및 api.ts의 version/held/empty 검증. main.tsx는 보류와 정상 0건 문구를 구분 |
| 원본·정규화·출처 | adapter 이전 B raw_row 허용 목록, document UUID/side/input_index, 실제 row 또는 null, accepted/review JSON Pointer. 기존 결과는 deepcopy 보존. 화면은 모든 후보의 원본·정규화 결과 상세를 표시. affected_refs는 각 전체 보류 사유에 양쪽 자료 전체를 연결 |
| 이전 결과 제거 | analyzeHira 시작 시 상세 선택·가족 intake 초기화. integrationReducer started는 response=null, resultView는 EMPTY. 보류 응답은 items=[]만 화면에 연결하므로 이전 결과/복용 확인 재사용 없음. 정상 재처리는 새 UNKNOWN/PENDING |
| 가족·취소·늦은 응답 | AbortController, hiraVersion, activeMemberRef 검사. 가족 변경은 파일·화면·선택 초기화. A→B→A여도 generation이 달라 이전 응답 거부. 파일 교체와 취소도 pending request 무효화 |
| 실패·반복·필수값 | 실패는 review_results에 남고 전체 gate가 D 호출 차단. 반복은 양쪽 전체 검사 후 차단하여 greedy 소비 순서의 비대칭 방지. 미확인 성분/함량을 SAME_INGREDIENT_SAME_STRENGTH로 바꾸지 않음. NEEDS_CONFIRMATION 의미와 engine reason_code는 변경 없음 |

schemas.py/api.ts/타입·화면·계약 문서가 같은 executed/held/null 의미를 사용한다.
이 체크는 실제 코드 읽기와 ad3713c 실행 증거를 대조한 것이며 이번 전체 재실행을 뜻하지 않는다.

## 3. 과도한 보류 여부

`_comparable`은 계약에 기재한 성분/함량/단위, 제품 식별 가능성, 1회량/1일횟수를
검사한다. duration_days·기관·약효분류·confidence·user_confirmed·공식 성분 ID는
검사하지 않는다. mfds ID·약품코드·정규화 제품명 중 하나의 식별 수단은 필요하나
셋을 모두 요구하지 않는다. 0은 알려진 수치다. 상이한 신뢰 제품 ID의 같은 성분
기록을 성분만으로 묶지 않는다.

추가 API 회귀는 행 번호/기관/분류/기간 칸을 동시에 비우고도 알려진 성분·함량을
B LOCAL_MOCK으로 정규화한 쌍이 MAINTAINED로 비교되는지 확인한다. null confidence,
false user_confirmed, null official_ingredient_id도 함께 확인한다.
**선택 필드 누락으로 보류되는 구현 오류는 발견하지 않았다. 조건을 완화하지 않는다.**

성분명이 있으나 함량이 없는 일반 HIRA 자료는 필수값 미확인이므로 보류가 맞다.
현재 B service는 성분 배열이 이미 있으면 Mock 공식 성분으로 무조건 덮어쓰거나
함량을 자동 보완하지 않는다. 정상 demo는 명시된 Mock 공식 제품·알려진 함량으로
정규화 가능한 가상 입력을 쓴다. 실제 HIRA export의 정상 처리율/필드 호환성은
미검증이며, 이 한계를 숨기기 위해 null을 동일 함량으로 간주하지 않는다.
향후 B의 공식 근거 보완·정규화 정책은 별도 협의 대상이다.

## 4. 이번 검사와 재사용 증거

이번 실행:

- `/tmp/yakeum-review/venv/bin/python -m pytest backend/tests/test_hira_hold_v2.py -q`:
  **16 passed**. 기존 15개와 선택 필드 누락 회귀 1개. 수정한 테스트와 관련 범위만 실행.
- MVP_DEMO.md의 fixture 생성 명령을 프로젝트 Python으로 직접 실행했다.
  생성한 previous/current/failure/unknown/repeat/empty 파일을 기존 pipeline v2에 넣어
  정상 DOSE_CHANGED+NEEDS_CONFIRMATION, 세 보류 사유, 정상 0건을 확인했다.
  이는 직접 로컬 pipeline 검사이며 새 브라우저 검사나 실제 외부 호출이 아니다.
- 문서 내부 상대 링크, `git diff --check`, push 대상 비밀값/불필요한 생성물 점검.

ad3713c의 기존 증거를 재사용하며 반복하지 않은 검사:

- 백엔드 전체 229 collected items passed + 그 내부 subtest 5 passed (독립 234개가 아님).
- 프론트 7개 테스트 스크립트·타입·Vite build 통과.
- 사진/HIRA 브라우저 12개 그룹과 이미지 검토 4개 시나리오 통과.
  HIRA 정상/보류/정상 재처리/empty/취소/가족·늦은 응답, 사진 전체 경로 포함.
- 네 viewport, runtime 오류 0, 외부 의약품 API 시도 0.

앱 구현이 동일하므로 이번에는 전체/프론트/브라우저를 다시 실행하지 않았다.
[LOCAL_PHOTO_VALIDATION.md](LOCAL_PHOTO_VALIDATION.md)의 실행 기록과 일치한다.
새 테스트 추가 후 전체 통과 수를 새로 측정했다고 주장하지 않는다.
3분 순서는 검증된 흐름의 시연 시간 배분이며 사람의 실제 3분 조작 시간을 계측한 것은 아니다.

## 5. 마감 변경과 남은 정책

- README의 초기 미구현 안내를 현재 Mock MVP 범위와 문서 링크로 정정.
- MVP_DEMO.md: 준비/실행, 변수 이름, 가상 파일 생성, 2분45초 순서, 메모리 초기화,
  저장 없음·실제 호출 없음·미검증 범위.
- LOCAL_PHOTO_MOCK.md: 과거 HIRA 변경 없음 기록과 현재 v2 문서의 관계 명시.
- test_hira_hold_v2.py: 선택 필드 누락 정상 비교 회귀만 추가.

대표 선택·부분 그룹 보류·재업로드/출처 간 중복·운영 사진 계약은 미결정이다.
실제 Gemini/MFDS·실제 HIRA export·DB·인증/권한·배포 검증을 완료로 표현하지 않는다.
HIRA v2는 사용자 승인 범위의 TASK D 통합안이며 팀 전체 합의가 끝났다는 의미가 아니다.
