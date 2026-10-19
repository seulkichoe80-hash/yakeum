# TASK D MVP 통합안: HIRA 비교 보류 v2

2026-10-19 사용자가 HIRA_COMPARISON_HOLD_DRAFT.md 권장안을 TASK D MVP 정책으로
승인한 범위를 구현한다. **A/B/C를 포함한 팀 전체 합의 완료를 뜻하지 않는다.**
기존 MedicationRecord, NormalizationResult, Reconciliation 상태와 reason_code는 유지한다.

## 버전과 소비자

- `POST /api/v1/reconciliations/hira`: 기존 응답/동작 그대로. 기존 소비자를 자동 전환하지 않는다.
  실패행 제외와 미확인 함량 비교라는 과거 제한도 그대로이므로 새 화면은 v1을 쓰지 않는다.
- `POST /api/v2/reconciliations/hira`: 동일 multipart 입력
  (`family_member_id`, `previous_file`, `current_file`), `response_version=TASK_D_HIRA_V2`.
  현재 TASK D 화면은 v2만 요청하고 응답 버전을 검사한다.
- 새 응답에 `family_member_id`, `comparison`, `source_rows`를 추가하고
  `reconciliation_result`만 nullable로 한다. 기존 v1 모델과 v2 모델을 분리한다.
- A 추출/B parser·정규화·adapter/공통 MedicationRecord/엔진 자체는 변경하지 않는다.
  D API가 B의 내부 결과와 공통 결과를 연결하고, C 소비 화면에 보류/원본 표시를 더한다.
  사진 local-demo 계약은 변경하지 않는다.

## 실행과 전체 보류

`comparison={executed:boolean, holds:[{kind,message,affected_refs}]}`.
다음 중 하나면 엔진 호출 전에 **양쪽 자료 전체를 보류**한다. 각 사유의 affected_refs는
안전하게 양쪽 전체 원본 참조를 포함한다. 아래 kind는 실행 진단이며 공통 오류 코드나
Reconciliation reason_code가 아니다.

| kind | TASK D MVP 조건 |
| --- | --- |
| UNIDENTIFIED_FAILED_INPUT | 어느 쪽이든 FAILED 또는 record:null 후보 |
| UNKNOWN_COMPARISON_FIELDS | 성분 배열/정규화 성분명/제품 함량/함량 단위/투약 단위/1회 투약량/1일 횟수 미확인 또는 비유한 수치. 제품 식별에 쓸 mfds ID·약품코드·정규화 제품명도 전부 없거나, 대응 제품 성분 집합이 불일치 |
| AMBIGUOUS_REPEATED_RECORDS | 어느 한쪽 안에서 기존 엔진 식별 규칙상 같은 제품으로 대응 가능한 기록이 복수 |

0은 알려진 수치다. duration_days는 복용기간 원문으로 보존하지만 유지/변경 판정의
기존 비교 대상이 아니므로 필수값에 새로 넣지 않는다. 서로 다른 신뢰 제품 ID를 가진
동일 성분 제품을 성분만으로 반복 그룹에 병합하지 않는다. 단위 환산·함량 추정·
최신 대표 자동 선택·정렬을 통한 매칭 우회·원본 삭제를 하지 않는다.

- 미실행: `executed=false`, 사유 1개 이상, `reconciliation_result=null`,
  `current_intake_states=[]`. 최신 자료 미확인/중단/기록상 유지로 바꿔 설명하지 않는다.
- 실행: `executed=true`, `holds=[]`, 기존 Contract D 결과 객체. 정상 0건이면
  그 객체의 `items=[]`이며 null이 아니다. 복용 확인 초기값은 UNKNOWN/PENDING이다.
- accepted_results의 MATCHED/PARTIAL/UNMATCHED와 review_results의 FAILED를 그대로 보존한다.
  보류를 FAILED로 바꾸거나 실패 후보를 삭제하지 않는다.
- 보류는 HTTP 200 도메인 결과다. 기존 파일/가족 오류 400/413/415/422는 유지한다.
- 비교 사전검사는 양쪽 전체를 보고 수행한다. 입력 순서/이전·현재 방향 때문에 반복
  자료가 일부 유지/일부 미확인으로 바뀌지 않는다. 대표 기록 정책은 여전히 미구현이다.

## 원본 참조와 화면

`source_rows[]`:

```json
{
  "ref": {"side":"current","document_id":"10000000-0000-4000-8000-000000000002","input_index":0},
  "locator": {"sheet_index":null,"row":3},
  "raw_fields": {"product_name":null,"dispensing_date":"가상 오류값"},
  "normalization_ref":"/review_results/current/0"
}
```

문서 UUID는 API가 요청마다 생성하며 인증/DB/재업로드 중복 식별자가 아니다.
input_index는 accepted/review 분류 전 0-based 순번, row는 B가 제공한 실제 1-based 행이다.
B가 시트 index를 제공하지 않으므로 null로 둔다. 실제 행이 없는 파일 수준 실패는
locator=null이다. 두 파일 모두 정상 헤더만 있으면 source_rows=[]이고 정상 비교 0건이다.

adapter 전 B raw_row에서 약품·날짜·성분·함량·단위·수량 필드만 허용한다:
`product_name, drug_code, date, dispensing_date, ingredient, strength, unit,
dose_per_time, times_per_day, total_days`.
기관/환자 열, 파일명/내부 경로/시트명은 이 snapshot에 추가하지 않는다.
기존 공통 정규화 결과는 바꾸지 않으며 원본 snapshot과 함께 요청 메모리에서만 다룬다.
영구 저장·자동 로그·DB는 추가하지 않는다.

normalization_ref는 같은 응답의 accepted_results/review_results에 대한 JSON Pointer다.
FAILED record:null에도 원본 참조가 남는다. 화면은 모든 원본 후보를 접힌 상세로 표시하며
원본 필드와 정규화 결과 전체를 열어 볼 수 있다. 잘못된 버전, 참조 누락/중복,
미실행인데 결과/복용 상태가 있는 응답은 화면에서 거부한다.

새 요청 시작 시 기존 결과 표시와 상세 선택, 해당 가족의 이전 복용 확인 상태를 비운다.
보류 응답에서는 과거 결과/확인을 다시 보여주지 않는다. 정상 재처리 시 UNKNOWN/PENDING으로
시작한다. 이는 서버 기록 삭제가 아니라 저장하지 않는 시연 화면의 로컬 결과 초기화다.
취소·가족 변경·A→B→A·늦은 응답 version/abort guard는 유지한다.
추출 내용 확인과 현재 복용 여부 확인은 별도 단계다.

## 가상 출력 차이

공통 processing/accepted_results/review_results/source_rows는 모두 그대로 반환하며,
다음은 실행 정보와 결과만 발췌한 예다. 완전한 원본 예시는 승인된 초안 §4를 참고한다.

```json
{
  "response_version":"TASK_D_HIRA_V2",
  "comparison":{"executed":false,"holds":[{
    "kind":"UNIDENTIFIED_FAILED_INPUT",
    "message":"실패 후보가 있어 양쪽 자료 전체 비교를 실행하지 않았습니다.",
    "affected_refs":[
      {"side":"previous","document_id":"10000000-0000-4000-8000-000000000001","input_index":0},
      {"side":"current","document_id":"10000000-0000-4000-8000-000000000002","input_index":0}
    ]
  }]},
  "reconciliation_result":null,
  "current_intake_states":[]
}
```

```json
{
  "response_version":"TASK_D_HIRA_V2",
  "comparison":{"executed":true,"holds":[]},
  "reconciliation_result":{
    "family_member_id":"00000000-0000-4000-8000-000000000001",
    "generated_at":"2026-10-19T00:00:00Z","items":[]
  },
  "current_intake_states":[]
}
```

## 범위와 남은 일

부분 그룹 보류·대표 선택・재업로드/출처 간 중복 정책은 별도 결정이다.
전체 보류로 정상 후보도 비교하지 않지만 원본 검토와 재처리는 가능하다.
실제 Gemini/MFDS 호출, DB/인증/권한/배포는 추가하지 않는다.
테스트는 가상 XLSX, 로컬 MFDS Mock, 실제 B/D 함수와 로컬 브라우저로 검증한다.
