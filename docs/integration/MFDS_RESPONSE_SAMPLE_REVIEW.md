# 제공된 식약처 응답 표본의 오프라인 매핑

확인일: 2026-10-29. 제공 파일: `붙여넣은 텍스트(1)(5).txt`.
파일 SHA-256: `f63bef59970dfc8b418a8def318f044dd96f15d6b54a49824e47df1d5fceb4da`.
사용자가 실제 API 응답이라고 제공한 **단일 응답의 복사본**이다.
전체 공식 명세·최신 operation·보험코드 검색 인자·이용 조건을 확정한 것이 아니다.
추가 식약처/Gemini 호출·설정 변경·Render 재배포 없음.

## 원본과 진단용 파생본

- 첨부 파일 전체는 XML 파싱 실패: 첫 줄에 브라우저의 스타일 안내 문장이 있다.
- 안내 문구만 제거한 사본도 실패: XML 기준 323행 37열의 회사명 텍스트에
  이스케이프되지 않은 `&`가 있다. 서버에서 내려받은 원본 자체가 손상됐다고 단정할 수 없다.
- 로컬 메모리의 **진단용 파생본에만** 안내 문구 제거 + bare `&` 세 곳을 `&amp;`로 바꾸면
  XML 파싱 성공, items 3개/totalCount 7/pageNo 1/numOfRows 3을 확인했다.
- 원본 파일은 수정하지 않았다. 이 파생본을 정상 원본 응답이나 실호출 성공 증거로 사용하지 않는다.
- 제품 필드 분석은 이 진단용 파생본에서 수행했으며, 파생본·첨부 원문은 Git에 넣지 않는다.
- 새 `parse_sample_xml`은 오프라인 전용 strict XML 파서다. 안내문·bare ampersand·손상 XML을
  자동 복구하지 않고 정제된 ValueError로 거절한다. DTD/ENTITY·큰 입력·중첩/중복 필드도 거절한다.
  기존 HTTP transport는 JSON 그대로이며 실제 XML 전송 경로를 활성화하지 않았다.

## 필드 대조 (이 표본에서 관측한 범위)

| 응답 필드 | 기존 내부 모델/처리 | 경계 |
|---|---|---|
| ITEM_SEQ | OfficialItem.official_id | 문자열. HIRA 보험코드와 동일하지 않음 |
| ITEM_NAME | OfficialItem.name | 제품명 후보. 성분·함량 검증 증거가 아님 |
| MAIN_ITEM_INGR | OfficialIngredient.name / ingredient_id | 이 표본에서 `[코드]이름`과 `\|` 분리를 관측. 함량 없음 |
| MATERIAL_NAME | 별도 MaterialComponent + 제한된 OfficialIngredient.amount/unit | 아래의 총량·성분별 분량·환산 구분 적용 |
| EDI_CODE | OfficialItem.insurance_code | 표본 3건 모두 빈 태그. 빈 값·공백은 None. 비어 있지 않은 실제 코드의 형식/다중코드 의미는 미검증 |
| TOTAL_CONTENT | 매핑하지 않음 | 유효성분 함량이나 1회 복용량으로 쓰지 않음 |
| PACK_UNIT | 매핑하지 않음 | 포장수량과 성분 함량을 혼동하지 않음 |

`insurance_code_param`은 여전히 null이므로 보험코드 API 조회는 실행하지 않는다.
코드 필드의 존재만으로 ITEM_SEQ나 바코드에서 보험코드를 추정하지 않는다.
CHART가 정확한 제형 enum이라고 확정하지 않으며 기존 매핑은 이번에 바꾸지 않았다.

## MATERIAL_NAME에서 분리하는 값

`총량`, `성분명`, `분량`, `단위`, `규격`, `성분정보`를 개별 문자열로 보존하는 내부
MaterialComponent를 추가했다. 이는 공통 MedicationRecord/외부 API의 새 필드가 아니다.
입력 row를 수정하지 않는다. 알 수 없는 필드·중복 키·깨진 구분·이름 대응 실패는
함량 보충을 하지 않는다. 제품명 숫자·TOTAL_CONTENT·PACK_UNIT로 대체하지 않는다.

관측 결과:

1. 산제: 총량 `1포304.000밀리그램`, 성분은 과립, 분량 `177.778밀리그램`,
   성분정보는 해당 유효성분으로서 `160밀리그램`이다.
   총량·과립량·환산 유효성분량은 다른 값이다. OfficialIngredient의 비교용 amount/unit은
   **둘 다 None**으로 유지한다. 환산식/대표 성분명/단위를 자동 생성하지 않는다.
2. 단일 정제: 총량 `1정615.04밀리그램`, 성분 분량 `500밀리그램`, 성분정보 비어 있음.
   이름 대응이 정확하고 유일하면 amount=Decimal('500'), unit='밀리그램'으로 연결한다.
   총중량 615.04나 TOTAL_CONTENT 1615.04를 쓰지 않는다.
3. 복합 정제: 총량 `1정473.00밀리그램`이 성분마다 반복된다.
   MATERIAL_NAME 순서는 분량 325/30/15/2, MAIN_ITEM_INGR 순서는 325/15/30/2에 대응한다.
   **순번 대신 성분명 정확 일치**로 연결한다. 중복 성분명이나 이름 집합 불일치면 함량 보충 전체를 건너뛴다.

현재 직접 수량을 연결하는 범위는 `1정<숫자>밀리그램` 기준, 단위 `밀리그램`,
비음수 Decimal 형식, 성분정보 공백, 성분명에 과립이 없음, 두 목록의 이름이 유일·정확히 대응할 때다.
다른 기준량·염/수화물·추출물·환산·단위 변환은 지원 완료로 간주하지 않는다.
단위는 표본의 '밀리그램' 그대로 남기며 'mg'로 바꾸거나 기존 저장 자료를 바꾸지 않는다.
단위 동등성/환산 정책은 후속 과제다.

## 후보 수와 비교 경계

응답의 전체 검색 결과는 7건이며 받은 것은 3건이다. 기존 totalCount 검사를 통과하지 못하므로
조회 실패 경고, 성공 캐시 없음, 단일 후보 매칭 없음으로 유지한다. 자동 후속 페이지 조회도 없다.
부분 표본의 세 제품 필드는 오프라인으로 분석할 수 있지만 전체 검색의 유일성은 입증하지 못한다.

제품명 기반 MATCHED는 단일 제품 후보라는 기존 의미를 유지한다.
제품명 정규화가 함량 문자열을 제거할 수 있다는 경고도 유지한다.
B structured 입력은 공식 성분·함량을 자동 덮어쓰지 않는다. 이 매핑으로 모든 추출값이 검증됐다고
표시하지 않으며 실제 사진/HIRA 앱의 공식 매칭은 여전히 LOCAL_MOCK다.
공식 필드와 원본 성분·함량의 충돌 검사, 환산값 처리와 live 모드 연결은 미완료다.

## 검사

외부 호출 없이 가상 transport와 표본 구조를 본뜬 **가상 제품/성분**만 사용한다.
원문 파일·인증키·원문 요청 URL·환자 자료는 fixture에 넣지 않는다.

```sh
/tmp/yakeum-live-venv/bin/python -m pytest -q backend/services/mfds/tests backend/tests/test_mfds_single_source_offline.py
# 45 passed (새 sample_mapping 검사 19개 포함)
/tmp/yakeum-live-venv/bin/python -m pytest -q backend/services/normalization/tests backend/tests/test_photo_demo.py backend/tests/test_hira_hold_v2.py backend/tests/test_hira_badge_demo.py backend/tests/test_dev_account.py backend/tests/test_account_hira.py backend/tests/test_saved_deletion.py backend/tests/test_photo_upload.py backend/tests/test_gemini_account.py
# 220 passed
```

검사: 직접 함량·복합제 성분 순서·과립/환산 보류·알 수 없는 단위/기준량·중복/손상 필드·
빈 보험코드·누락 MATERIAL_NAME·포장/총량 미사용·XML 거절·7건 중 3건의 후보 확정 차단.
기존 네 가지 사진 보류와 HIRA 보류/null 대 정상 0건, 계정·가족 접근, 저장/재조회/삭제도 회귀 통과했다.
첫 검사에서 공백 EDI_CODE가 빈 문자열로 남는 오류를 발견해 None으로 수정 후 재검사했다.
기존 성공 조건을 낮추거나 검사를 삭제하지 않았다. 각 실행에 기존 Starlette/httpx deprecation warning 1건.
프론트 코드를 바꾸지 않아 프론트·브라우저 검사는 재실행하지 않았다.
공통 Schema/상태/reason_code/API·DB·배포 설정은 변경하지 않았다.

## 남은 근거

공식 활용가이드 URL·버전·접근 조건과 단위/기준량/성분 환산 정의는 이전
[단일 API 대조 기록](MFDS_SINGLE_API_REVIEW.md)의 미확인 항목으로 남는다.
사용자 제공 응답 표본을 확보했다고 이 문서 전체를 공식 명세로 승격하지 않는다.
