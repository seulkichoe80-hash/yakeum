# TASK A Extraction Contract PoC

이 폴더가 TASK A의 유일한 런타임 위치다. `task-a/`의 중복 코드와 JPG/MP4
자료는 통합하지 않는다. 공통 provider는 별도 설정·승인 시 사용할 SDK 전송을 포함한다. 현재 사진 화면은
LOCAL_MOCK 경로를 유지하며 실제 이미지 업로드 API·DB 저장을 추가하지 않는다.
이번 D 통합 검증에서는 실제 Gemini 호출·모델 조회를 하지 않는다.

## 책임 분리

- Gemini/가상 응답: 문서에 보이는 raw 후보와 record-level confidence만 제공
- 호출자: `family_member_id`, `source_document_id`, `record_date` 제공
- Adapter: 약품별 `source_record_id`와 deterministic `record_id` 생성
- 사용자: 결과 확인·수정 후 별도 흐름에서 확정
- TASK B: 제품·성분 정규화와 공식 데이터 매칭

`record_id`는 시스템 값이며 AI가 만들지 않는다. `source_record_id`는 호출자가
제공한 문서 ID에 약품 순번을 붙여 만든다. 이 규칙은 DATA_SCHEMA의 최종
재업로드 정책이 아니라 내부 PoC 규칙이다.

## 여러 약품

공통 API Contract의 `ExtractionResult` 한 건은 MedicationRecord 한 건을 가진다.
한 이미지에서 여러 제품이 발견되면 `adapt_gemini_response`는 제품별
`ExtractionResult` 목록을 내부적으로 반환한다. 외부 API 배열 계약은 아직
확정하지 않으며 공통 문서는 변경하지 않는다.

## 모델과 의존성

모델명 기본값은 없다. 실제 계정에서 확인한 값만 `YAKEUM_GEMINI_MODEL` 환경
변수로 지정한다. API Key는 `GEMINI_API_KEY` 환경변수로만 전달한다.

고정 Gemini SDK는 `requirements.txt`에 명시하며 통합 테스트에서는 실제 SDK를
메모리 HTTPX MockTransport로 실행한다. 외부 네트워크로는 요청하지 않는다. 모델 조회 수동 명령은 외부 호출이므로 별도 승인된 상황에서만
실행한다.

```powershell
python -m backend.services.extraction.scripts.check_models
```

## 테스트

모든 Adapter 테스트는 가상 JSON 또는 Fake provider callable만 사용하며 외부
네트워크를 호출하지 않는다.


## A 원격 SDK 선별 통합 (2026-10-26, TASK D)

A 원격 `2787918765e7e9724a1d2f1215b69e6296801a86`의 provider 전송·sdk.py·
고정 의존성·test_extraction_sdk.py를 선별 반영했다. SDK 테스트의 안전한 수동
사전검사 도구 run_image.py도 함께 포함한다. `--allow-live` 실행이나 모델 조회는
이번 검증 범위가 아니다. 이전 extraction.py/schema.py/test.py/task-a 및 미디어는
가져오지 않았다. root backend/requirements.txt가 추출 의존성을 함께 설치한다.

D 공통 adapter/parser/models/config/prompt는 유지한다. 따라서 원격 A의
정상+숫자 오류 제품이 문서 전체 FAILED가 되는 한계도 그대로이며
후속 A 게시 코드 대기 항목이다. A 로컬 d85e537은 반영하지 않는다.
단순히 SDK를 가져왔다고 실제 사진 업로드·인식·앱 전체 live 연동을 완료한 것은 아니다.
공통 결과의 SUCCESS는 사용자 확정/정확도 보장이 아니며 user_confirmed=false다.

구체적 반영 파일·검사·A 수정 요청은
[D 통합 보고서](../../../docs/integration/A_PUBLISHED_SDK_INTEGRATION.md)를 따른다.
