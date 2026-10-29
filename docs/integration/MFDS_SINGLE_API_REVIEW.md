# 식약처 의약품 단일 API 대조 기록 — 공식 명세 확보 전 보류

확인일: 2026-10-29 (한국 시간). TASK D/MVP 통합 작업 기록이다.
**공식 명세 대조·오프라인 연결 확정은 미완료**다. 인증 API 실호출 0회,
Gemini 호출 0회, Render 재배포 없음. 기존 가상 매칭·저장 자료·DB는 유지한다.

## 1. 대상 선정과 조사 한계

우선 대상으로 **식품의약품안전처 의약품 제품/품목허가정보 서비스** 1개를 선정한다.
제품 식별과 성분·함량의 근거를 찾는 목적에 맞으며 기존 B 클라이언트를 재사용할 수 있다.
서비스 최신 정식 명칭·버전·제공 필드는 아직 확정하지 않는다.

| 후보 | 검토 판단 | 이번 공식 확인 |
|---|---|---|
| 의약품 제품/품목허가정보 | 단일 우선 대상. 품목 식별·성분 자료 확인 목적 | 본문 접근 불가, 잠정 선정 |
| 의약품개요정보(e약은요) | 복약 안내 후보. 성분별 정량 함량을 제공한다고 가정하지 않음 | 본문 접근 불가 |
| 건강기능식품 품목제조신고 | 의약품과 코드 체계가 달라 이번 단일 의약품 범위에서 제외 | 이번 조사 대상 아님 |

다음 **공개 문서 GET** 모두 프록시 CONNECT 403이었다. 페이지 자체의 403이나
공식 서버의 오류라고 단정할 수 없다. 현재 네트워크 허용 목록에 문서 도메인이 없다.
허용 우회·환경 설정 변경·키 사용·API 호출은 하지 않았다.

- 기존 저장소의 의약품 문서 후보: https://www.data.go.kr/data/15095677/openapi.do
- e약은요 문서 후보: https://www.data.go.kr/data/15075057/openapi.do
- 포털 검색: https://www.data.go.kr/tcs/dss/selectDataSetList.do?keyword=의약품%20품목허가정보
- 의약품안전나라 공개 페이지: https://nedrug.mfds.go.kr/pbp/CCBGA01

위 상세 페이지 ID와 서비스 대응도 이번에 본문으로 재확인하지 못했다.
필요 문서는 포털에서 **식품의약품안전처 의약품 제품/품목허가정보의 OpenAPI 활용가이드**와
**상세기능·요청/응답 항목표·오류코드표·응답 예시**다.
이 문서의 공개 PDF/HWP/DOCX 또는 내려받은 가이드를 확보해야 다음 대조를 완료할 수 있다.
키·계정 정보·실제 의약품 이용 기록을 문서에 넣지 않는다.

## 2. 필드별 대조표

아래는 공식 필드 확인표가 아니라 **기존 설정과 확인 필요 사항의 대조표**다.
문서 미확인을 '서비스가 미제공'한다고 단정하지 않는다.

| 필요 정보 | 기존 코드의 필드 가정 | 공식 제공 여부 | 현재 어댑터 처리 |
|---|---|---|---|
| 제품 ID | ITEM_SEQ | 미확인 | 문자열 보존. 보험코드와 별개 |
| 제품명 | ITEM_NAME | 미확인 | 단일 후보 제품명·ID 연결만 수행 |
| 성분명 | MAIN_ITEM_INGR | 미확인 | `\|` 구분·`[코드]이름`은 기존 미검증 가정 |
| 성분 ID | 위 문자열의 대괄호 접두 | 미확인 | 공식 코드 의미 확인 필요 |
| 성분별 함량 | 확정 필드 없음 | 미확인 | 매핑 미제공, amount=None |
| 함량 단위·기준량 | 확정 필드 없음 | 미확인 | 매핑 미제공, unit=None |
| 보험코드 | 요청·응답 필드 null | 미확인 | 조회/매핑 미제공. HIRA drug_code≠ITEM_SEQ |
| 제형 | CHART | 미확인 | 외형 설명일 수 있어 제형 검증 근거로 사용 금지 |

요청 URL `DrugPrdtPrmsnInfoService06/getDrugPrdtPrmsnInq06`, `item_name`, `serviceKey`,
`type=json`, `pageNo`, `numOfRows`, `header.resultCode`, `body.items`, `totalCount`도
기존 설정값이며 이번에 공식 확인한 값이 아니다. 오류 03의 무자료 의미도 재확인 필요하다.
**이번에는 이 가정값이나 응답 파싱을 추가·확정하지 않았다.**

## 3. 오프라인 연결과 의미

현재 사진/HIRA 앱의 매칭은 LOCAL_MOCK다. RealMfdsClient는 주입 가능한 별도 클라이언트다.
실제 연결 전에는 의약품 단일 소스·재시도 0·추가 페이지 조회 없음 등 호출 예산을 별도로 준비해야 한다.
기존 기본 이름 검색은 의약품과 건강기능식품 둘 다 조회하며 기본 재시도도 있어,
그대로 '최대 1회' 실제 시험에 쓰면 안 된다.

`MATCHED`는 공통 계약상 단일 제품 후보 매칭이며 성분/함량 검증 완료 상태가 아니다.
이름 정규화는 함량 문자열도 제거하므로 NAME_EXACT가 문자 전체 일치나 동일 함량을 보증하지 않는다.
이번 최소 변경은 MFDS_DRUG 이름 기반 매칭에 기존 ErrorDetail 형식의 경고를 더한다.
성분·함량·단위 공식 검증을 수행하지 않았음을 알리고 원본을 유지한다.
기존 상태·reason_code·Schema/API·출처·비교 로직·DB는 바꾸지 않는다.
LOCAL_MOCK 경로에는 이 경고를 추가하지 않는다.

**남은 제한:** 원본에 비교 값이 모두 있으면 현 비교는 원본값 기준으로 가능하며,
이를 식약처가 검증했다고 표현해서는 안 된다. 실제 응답의 다른 성분/함량과 원본의
충돌을 검증하는 기능은 미완료다. 공식 함량·기준량 의미를 확보하기 전 제품명 숫자로 보완하지 않는다.
함량 공백은 보류하지만 '원본에 숫자가 있다'는 것이 공식 검증을 뜻하지 않는다.

## 4. 가상 응답 검사

`backend/tests/test_mfds_single_source_offline.py`는 기존 미검증 설정을 복사한
**의약품 단일 소스 테스트 프로필**만 사용한다. 공식 응답 샘플이나 공식 명세 적합성 검사가 아니다.
실제 사진 coordinator → B 정규화 → 비교 gate를 실행하며 transport는 가짜다.

- 결과 없음: UNMATCHED + 원본 보존 + 사진 전체 비교 보류.
- 복수 후보: PARTIAL + 자동 선택 없음 + 비교 보류.
- 제품명 단일 후보이나 원본 함량 미확인: MATCHED와 별개로 비교 보류.
- 시간 초과: UNMATCHED + 조회 실패 구분 + 비교 보류, 자동 재시도 없음.
- 원본 100mg/후보명 200mg: NAME_EXACT가 가능함을 고정 재현. 원본 100을 덮어쓰지 않고
  공식 성분·함량 미검증 경고. 이 테스트는 공식 매칭 성공/안전성 증거가 아니다.

보류에서 reconciliation_result는 null, intake는 []이며 정상 비교 0건으로 대체하지 않는다.
원본 후보·수정 기록·정규화 기록을 유지하고 미확인/미복용을 자동 확인하지 않는다.

## 5. 신청·연결 전 절차 (현재 화면/조건 미확인)

1. 공공데이터포털 로그인 후 위 서비스명과 제공기관을 확인한다.
2. 상세기능·활용가이드에서 최신 operation/필드/오류/라이선스·출처표시·요금·할당량을 확인한다.
3. 필요한 기능에 개발계정 활용 신청한다. 자동/심의 승인 여부와 승인 대기·일일 한도는 실제 화면에서 확인한다.
4. 승인 후 키는 서버 비공개 MFDS_API_KEY에만 설정한다. 키의 인코딩/디코딩 방식도 가이드와 맞춘다.
5. 이번에는 신청·키 발급·설정·인증 API 호출을 진행하지 않았다.

다음 완료 조건: 공식 가이드 버전·문서 URL·확인일과 함께 위 필드표 확정 →
해당 명세의 개인정보 없는 가상 응답으로 매핑/오류/누락/복합제 단위 테스트 →
출처와 모드가 분리된 실제 연결 준비 → 별도 승인된 제한 호출.
문서 확보 전 10월31일 시연은 가상 매칭임을 유지한다.

## 6. 실행 기록

Python: `/tmp/yakeum-live-venv/bin/python` (Python 3.12).

```sh
python -m pytest -q backend/tests/test_mfds_single_source_offline.py backend/services/mfds/tests backend/services/normalization/tests/test_structured_input_design.py backend/tests/test_photo_demo.py backend/tests/test_hira_hold_v2.py
# 86 passed (신규 안전 검사 5개 포함)
python -m pytest -q backend/services/normalization/tests backend/tests/test_dev_account.py backend/tests/test_account_hira.py backend/tests/test_saved_deletion.py backend/tests/test_hira_badge_demo.py backend/tests/test_photo_upload.py backend/tests/test_gemini_account.py
# 177 passed
```

두 묶음에는 구조화 정규화 검사가 겹치므로 합계를 독립 테스트 수로 표시하지 않는다.
각 실행에 기존 Starlette/httpx deprecation warning 1건이 있었다.
초기 신규 테스트의 fixture를 수정했다(함량과 단위는 함께 비워야 하는 기존 입력 계약,
정규화된 성분명과 raw 성분명 분리). 기존 검사의 성공 조건은 바꾸지 않았다.
추가 회귀 명령의 첫 시도는 파일명 오기로 수집 전에 종료됐으며 위 실제 파일명으로 재실행해 통과했다.
프론트 코드·화면은 변경하지 않아 프론트/브라우저 검사는 재실행하지 않았다.
외부 HTTP는 공개 문서 시도만 했고 모든 약품 조회는 주입한 가상 응답이다.
비밀값·개인정보·실제 응답·DB·생성 이미지/워크북은 변경 목록에 없다.
