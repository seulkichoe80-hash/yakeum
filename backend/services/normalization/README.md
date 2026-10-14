# 약이음 B파트 — HIRA 파서 · 식약처 매칭 · 정규화 (1~3주차)

HIRA 진료내역 Excel → `MedicationRecord` → (식약처 공식 데이터와 매칭) → `NormalizationResult`.
파서에는 LLM/AI를 쓰지 않으며 같은 입력은 항상 같은 출력을 낸다.

## 실행 방법
```bash
pip install -r backend/services/normalization/requirements.txt
python -m pytest backend/services -q          # 저장소 루트에서 실행
```
```python
from backend.services.normalization.service import normalize_hira_file
results = normalize_hira_file("진료내역.xlsx")   # 기본: MockMfdsClient
print([r.to_dict() for r in results])
```
구조: `hira/`(파서 + `column_mapping.yaml`) · `mfds/`(MfdsClient / Mock / Real 스텁) · `normalization/`(models, 매처, 서비스, `config.yaml`).
API 키는 환경변수 `MFDS_API_KEY`로만 읽는다. `.env`는 커밋 금지(`normalization/.gitignore`).

## 실제 API 사용 / CLI
```bash
export MFDS_API_KEY=발급받은키              # 공공데이터포털 인증키 (코드·로그·경고에 남기지 않음)
python -m backend.services.normalization.cli 진료내역.xlsx --real --out result.json -v   # 기본(--real 없음)은 Mock
```
```python
from backend.services.mfds.real_client import RealMfdsClient
results = normalize_hira_file("진료내역.xlsx", client=RealMfdsClient(timeout=5, retries=3))
```
- `RealMfdsClient`: 타임아웃·5xx·429는 지수 백오프로 재시도, 4xx/API 오류코드는 재시도 안 함. 끝내 실패하면 예외 대신 `warnings`(`공식 데이터 조회 실패…`)로 남기고 해당 행은 UNMATCHED(원본 보존). "없음"과 "조회 실패"는 경고 문구로 구분한다.
- 성공한 조회는 메모리 캐시(실패는 캐시 안 함). 엔드포인트/필드 매핑은 `mfds/api_config.yaml`.
- 로깅: 표준 `logging` 사용(`-v`로 DEBUG), 요청 키는 로그에 출력하지 않음. 실행 끝에 상태별 개수 요약을 출력.

## 입출력 예시 (1행)
입력 행: `2024-03-05 | 가나다의원 | 타이레놀정500밀리그램 | 000123456 | 아세트아미노펜 | 500mg | 1 | 3 | 5`
```json
{
  "status": "MATCHED",
  "record": {
    "source": "HIRA", "date": "2024-03-05", "date_raw": "2024-03-05 00:00:00",
    "drug_code": "000123456",
    "product_name": {"raw": "타이레놀정500밀리그램", "normalized": "타이레놀"},
    "ingredients": [{"name": {"raw": "아세트아미노펜", "normalized": "아세트아미노펜"},
                     "amount": 500, "unit": "mg", "amount_raw": "500mg", "source": "HIRA"}],
    "dosage": {"dose_per_time": 1, "times_per_day": 3, "total_days": 5, "raw": {}},
    "institution": "가나다의원"
  },
  "match": {"source": "MFDS_DRUG", "official_id": "000123456", "match_method": "CODE_EXACT"},
  "warnings": [], "errors": []
}
```
(전체 기대 결과: `normalization/tests/expected_sample.json`, 일부 필드 생략. 수량은 Decimal 보존을 위해 실제 JSON 에서는 `"500"` 처럼 문자열이며, `match.official_id` 는 Mock 의 가상 ID `OFFICIAL-0001`.)

## 가정 사항 / 팀장 확인 필요
1. B 내부 모델(`models.py`)은 공통 `docs/DATA_SCHEMA.md`와 다른 구조다. 팀 전달용 변환은 `adapter.py`가 전담한다(아래 "공통 규격 변환"). 내부 모델은 처음부터 다시 쓰지 않았다.
2. 실제 HIRA 샘플이 없어 컬럼을 가정함 (`hira/column_mapping.yaml`, 별칭만 고치면 됨):
   진료일자/조제일자…(날짜), 요양기관명(기관), 약품명/약품명칭/처방약품명(제품명), 약품코드/보험코드/주성분코드(코드),
   성분명, 함량, 1회 투약량, 1일 투여횟수, 총 투약일수. 헤더 행은 별칭 일치가 가장 많은 행(상위 30행)으로 자동 탐지.
3. `주성분코드`를 drug_code 별칭에 포함했으나, 품목기준코드/보험코드와 다른 체계일 수 있음 → 확인 필요. **HIRA 약품코드(drug_code)와 식약처 제품 ID(`official_id`/`mfds_product_id`)는 별개 체계**라서 서로 비교하지 않는다. 코드 매칭(`CODE_EXACT`)은 공식 응답에 보험코드 필드(`OfficialItem.insurance_code`)가 확인된 경우에만 동작하며, 실제 API 설정(`insurance_code_param`)은 명세 확인 전까지 비어 있다(= 이름 매칭만 사용).
4. 병합 셀은 값을 채워 쓰고 warning을 남김. 숫자 셀로 저장된 코드는 앞자리 0 복구 불가라 warning.
5. 날짜 허용 범위 1990–2100, 형식 `YYYY-MM-DD`; 해석 불가/범위 밖은 `null` + warning.
6. B 내부 결과의 FAILED 행은 원본(raw_row, source_ref)을 담아 두지만, **공통 규격 출력에서는 계약대로 `record: null`** 이다.
7. 후보 2건 이상(PARTIAL)은 `match.official_id=null`, 후보 ID는 warnings에 기록. 단일 매칭이어도 성분 정보가 끝내 없으면 PARTIAL.
8. 식약처 응답 형식을 몰라 `OfficialItem`(mfds/models.py)은 가정. `RealMfdsClient`는 2주차 스텁(재시도·캐싱 포함 예정).
9. **식약처 API 응답 형식은 실제 호출로 검증하지 못했다**(개발 환경에서 data.go.kr 접속 불가, 키 없음). `mfds/api_config.yaml`의 URL·파라미터명·필드명(ITEM_SEQ, ITEM_NAME, MAIN_ITEM_INGR, PRDLST_REPORT_NO 등)은 공공데이터포털 명세 기억에 기반한 가정이며, 가짜 응답으로만 테스트했다. 실제 키로 1회 호출해 필드를 확인해야 한다.
10. 의약품 응답에는 성분 함량이 없다고 가정 → 공식 성분은 이름만 채우고 `amount=null`. 건강기능식품 응답에는 성분 목록이 없다고 가정 → 매칭돼도 HIRA에 성분이 없으면 PARTIAL.
11. 이름 조회는 정규화한 이름(제형·함량 제거)으로 요청한 뒤 로컬에서 NAME_EXACT/NAME_FUZZY를 판정한다.
12. 3주차 보강: 다중 시트 헤더 탐색, 날짜 문자열의 시각 제거, 분수 용량("1/2"→0.5), 중복 행 경고, 정규화 중 예외도 행 단위 FAILED 처리. 합계/소계 행은 별도 처리하지 않음(실제 파일 확인 후 필요하면 추가).
13. 테스트/README를 각 담당 폴더 안에 두었고 패키지 import 경로는 `backend.services.*`(저장소 루트 기준, `__init__.py` 없는 namespace 패키지)로 가정.


## 공통 규격 변환 (adapter.py)
B 내부 `NormalizationResult` → `docs/DATA_SCHEMA.md`의 `MedicationRecord`/`Ingredient` + `docs/API_CONTRACT.md` Contract B 형태.
```bash
python -m backend.services.normalization.cli 투약이력.xlsx --common --family-member-id <가족UUID> --out common.json
```
```python
from backend.services.normalization.adapter import to_common_results, validate_common_result
common = to_common_results(results, family_member_id)   # family_member_id 는 호출자가 제공 (B 는 만들지 않음)
```
- 가상 입출력 예시: `tests/expected_common_sample.json` (입력: `hira/tests/make_fixtures.py::make_common_sample_xlsx`)
- Decimal 필드(`dose_per_administration`, `administrations_per_day`, `duration_days`, `product_strength`)는 `"1"`, `"0.5"` 같은 문자열. float 를 쓰지 않는다.
- FAILED 는 `record: null`, `warnings`/`errors` 는 `{code, message, field}` (공통 오류 코드 5종만 사용).
- `validate_common_result()` 로 키·타입·필수값을 점검할 수 있다.

### 필드 생성 주체 (잠정 — DATA_SCHEMA TODO, 팀장 확인 필요)
| 필드 | B 의 처리 |
| --- | --- |
| `family_member_id` | 호출자가 전달. 없거나 UUID 아니면 `ValueError` (추측 금지) |
| `record_id` | uuid5(family_member_id, source_type, source_record_id). `record_id_factory` 로 교체 가능 |
| `source_record_id` | `hira:` + 행 내용(조제일자·약품코드·제품명·기관·성분·투약량) SHA-256 앞 20자, 동일 행 반복 시 `-2`… (행 번호·파일명 무관) |
| `record_date` | HIRA 는 `dispensing_date`(조제일자). 없으면 FAILED(`REQUIRED_FIELD_MISSING`) |
| `prescribing/dispensing_institution` | `처방기관`/`조제기관` 컬럼이 있을 때만. 단일 `요양기관명` 컬럼은 어느 쪽인지 알 수 없어 null |
| `product_name_normalized` | 공식 데이터에 단일 매칭되면 공식 제품명, 아니면 B 규칙 정규화 값 |
| `mfds_product_id` | 단일 매칭된 `official_id` 만. 후보 여러 건/미매칭은 null |
| `ingredients` | HIRA 성분은 raw/normalized 모두, 공식 데이터에서 보완한 성분은 raw=null |
| `confidence` / `user_confirmed` | null / false |

## 검증 상태
- 단위 테스트(`python -m pytest backend/services -q`)는 가상 데이터·Mock 으로만 검증한다.
- **실제 HIRA 파일 헤더, 식약처 API URL·필드·코드 체계는 검증되지 않았다.** 확인 절차는 `VERIFICATION_PLAN.md`.
