# 식약처 연결 준비 — 가짜 전송 검증, 실제 조회 미실시

2026-10-27, codex/mvp-completion. 현재 앱의 공식 약품 매칭은 LOCAL_MOCK다.
이 문서는 TASK D 통합 준비 기록이며 공식 명세 확인 완료나 운영 연동 완료 선언이 아니다.

## 공식 문서 대조 상태

공공데이터포털 공개 설명 페이지 https://www.data.go.kr/data/15095677/openapi.do 에 접속을 시도했으나
현재 프록시 CONNECT 403으로 차단됐다(페이지 HTTP 응답도 받지 못함).
따라서 아래 값은 **저장소 api_config.yaml에 있는 미검증 설정**이며 이번에 공식 최신 명세와
일치한다고 확인하지 않았다. 서비스 이름/버전·operation·출력 명세를 확보하기 전 실제 API를 호출하지 않는다.
www.data.go.kr 문서 허용 또는 사용자가 제공하는 공개 활용 가이드가 필요하다.
API 키/건강정보는 가이드에 첨부하지 않는다.

| 항목 | 기존 설정(공식 최신 확인 필요) |
|---|---|
| 의약품 API | https://apis.data.go.kr/1471000/DrugPrdtPrmsnInfoService06/getDrugPrdtPrmsnInq06 |
| 건강기능식품 API | https://apis.data.go.kr/1471000/HtfsInfoService03/getHtfsItem01 |
| 키 | 서버 비밀 환경변수 MFDS_API_KEY → 요청 serviceKey |
| 공통 요청 | type=json, pageNo=1, numOfRows=50 |
| 제품명 검색 | 의약품 item_name / 건강기능식품 Prduct |
| 응답 | header.resultCode, body.items, 제공되면 body.totalCount |
| 제품 번호·이름 | 의약품 ITEM_SEQ / ITEM_NAME, 건강기능식품 PRDLST_REPORT_NO / PRDUCT |
| 성분 | MAIN_ITEM_INGR, 구분자와 코드 접두 해석은 아직 미검증 가정 |
| 제품 함량·단위 | 현재 확정 매핑 없음. 제품명 숫자를 함량으로 파싱하지 않음 |
| 보험코드 | 요청/응답 매핑 모두 비활성. ITEM_SEQ와 HIRA drug_code를 같다고 취급하지 않음 |

CHART는 기존에 form으로 매핑하지만 외형 설명인지 제형인지 명세 확인이 필요하다.
MAIN_ITEM_INGR의 성분명/코드만으로 1정당 함량·복합제 성분별 단위를 확정할 수 없다.
현재 RealMfdsClient는 성분 amount/unit을 None으로 보존한다. 건강기능식품 성분 매핑도 미확정이다.
공식 응답 모델을 MedicationRecord에 직접 복사하지 않고 기존 B 정규화·공통 계약을 거친다.

## 이번에 연결·보완한 부분

- 기존 RealMfdsClient에 가짜 transport를 주입해 OfficialItem → B normalize_structured_record 경로 검사.
- 결과 없음과 조회 실패 구분. header/필수 구조/제품 ID·이름이 잘못되면 실패로 표시하고 성공 캐시 금지.
- totalCount가 현재 받은 행 수와 다르면 첫 페이지로 단일 후보를 확정하지 않고 실패 안내.
  자동 추가 페이지 조회는 이번에 구현하지 않음. 부분 목록을 전체라고 간주하지 않음.
- 의약품 후보가 있어도 다른 공식 소스 조회가 실패하면 B는 UNMATCHED와 원본·경고를 보존.
- 정확한 이름 후보 여러 개는 PARTIAL, 선택된 official_id 없음. 이름 유사도만으로 사용자 확정하지 않음.
- 함량 미확인은 None 유지. 비교 필수값이 없으면 기존 전체 비교 보류 정책 적용.
- 테스트가 의약품 payload를 건강기능식품 API에도 반환하던 부분은 해당 API의 명시적 빈 응답으로 수정.
  기존 재시도/캐시/오류 검사 조건은 유지했다.
- 기존 API/MedicationRecord/NormalizationResult 상태 의미는 변경하지 않음. 기본 앱은 계속 Mock.

주의: MATCHED는 제품 후보 매칭일 뿐 공식 함량 검증 완료가 아니다. 현재 B는 입력의 읽힌 성분/함량을
보존하며 공식 성분과 대조·충돌 검증 또는 공식 함량 보충을 새로 구현하지 않았다.
실제 앱 활성화 전에 출처 표시, 성분/함량의 공식 근거, 유사 이름 충돌, 불완전 응답 정책을 함께 검토해야 한다.

## 실제 호출 전 준비

1. 포털에서 정확한 API 데이터셋·최신 활용 가이드·응답 샘플 확인(두 소스 각각).
2. 사용자 프로젝트의 활용 승인과 해당 서비스의 개발/운영키 사용 조건 확인.
3. MFDS_API_KEY를 비공개로 주입, apis.data.go.kr HTTPS 도메인에만 연결. 코드·URL 로그에 저장 금지.
4. 인코딩/디코딩 키 중 어떤 값을 URL 인코딩할지 명세로 확인. 이중 인코딩하지 않기.
5. 제공 모델의 코드·문자열·날짜·복합 성분·함량 단위와 보험코드 제공 여부를 대조.
6. 무료 여부/일일 할당량/요청 제한/출처 표시·재배포·캐시 이용 조건 확인. 현재 확정하지 않음.
7. 목적·요청 수·재시도 수·비용을 먼저 안내하고 별도 실제 호출 지시 후에만 실행.
   현재 RealMfdsClient 기본 retries=3은 소스별 최대 4시도, 이름 조회가 두 소스를 사용함에 유의.
   1회 승인 시험이라면 단일 소스+retries=0+전체 예산을 먼저 강제해야 함.
8. 오류/빈 결과/여러 후보/함량 미확인은 그대로 보류·원본 보존. Mock으로 조용히 대체하지 않음.

운영 DB/로그인·암호화·개인정보 처리·운영 배포 완료를 의미하지 않는다.
