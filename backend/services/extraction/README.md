# TASK A Extraction Contract PoC

이 폴더가 TASK A의 유일한 런타임 위치다. `task-a/`의 중복 코드와 JPG/MP4
자료는 통합하지 않는다. 이 PoC는 실제 Gemini API, 이미지 업로드, Endpoint,
DB 저장 또는 TASK B 연결을 수행하지 않는다.

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

라이브 Gemini SDK는 `requirements.txt`에 명시하지만 이번 PoC 테스트에서는
사용하지 않는다. 모델 조회 수동 명령은 외부 호출이므로 별도 승인된 상황에서만
실행한다.

```powershell
python -m backend.services.extraction.scripts.check_models
```

## 테스트

모든 Adapter 테스트는 가상 JSON 또는 Fake provider callable만 사용하며 외부
네트워크를 호출하지 않는다.
