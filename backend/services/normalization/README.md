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
(전체 기대 결과: `normalization/tests/expected_sample.json`, 일부 필드 생략)

## 가정 사항 / 팀장 확인 필요
1. `docs/DATA_SCHEMA.md`가 저장소에 없어 `normalization/models.py`에 **임시 모델**을 둠 (필드명·중첩 구조는 가정). 스키마 확정 시 이 파일만 수정.
2. 실제 HIRA 샘플이 없어 컬럼을 가정함 (`hira/column_mapping.yaml`, 별칭만 고치면 됨):
   진료일자/조제일자…(날짜), 요양기관명(기관), 약품명/약품명칭/처방약품명(제품명), 약품코드/보험코드/주성분코드(코드),
   성분명, 함량, 1회 투약량, 1일 투여횟수, 총 투약일수. 헤더 행은 별칭 일치가 가장 많은 행(상위 30행)으로 자동 탐지.
3. `주성분코드`를 drug_code 별칭에 포함했으나, 품목기준코드/보험코드와 다른 체계일 수 있음 → 확인 필요.
4. 병합 셀은 값을 채워 쓰고 warning을 남김. 숫자 셀로 저장된 코드는 앞자리 0 복구 불가라 warning.
5. 날짜 허용 범위 1990–2100, 형식 `YYYY-MM-DD`; 해석 불가/범위 밖은 `null` + warning.
6. FAILED 행도 `record`에 원본(raw_row, source_ref)을 담아 반환 (record가 null이 아님).
7. 후보 2건 이상(PARTIAL)은 `match.official_id=null`, 후보 ID는 warnings에 기록. 단일 매칭이어도 성분 정보가 끝내 없으면 PARTIAL.
8. 식약처 응답 형식을 몰라 `OfficialItem`(mfds/models.py)은 가정. `RealMfdsClient`는 2주차 스텁(재시도·캐싱 포함 예정).
9. **식약처 API 응답 형식은 실제 호출로 검증하지 못했다**(개발 환경에서 data.go.kr 접속 불가, 키 없음). `mfds/api_config.yaml`의 URL·파라미터명·필드명(ITEM_SEQ, ITEM_NAME, MAIN_ITEM_INGR, PRDLST_REPORT_NO 등)은 공공데이터포털 명세 기억에 기반한 가정이며, 가짜 응답으로만 테스트했다. 실제 키로 1회 호출해 필드를 확인해야 한다.
10. 의약품 응답에는 성분 함량이 없다고 가정 → 공식 성분은 이름만 채우고 `amount=null`. 건강기능식품 응답에는 성분 목록이 없다고 가정 → 매칭돼도 HIRA에 성분이 없으면 PARTIAL.
11. 이름 조회는 정규화한 이름(제형·함량 제거)으로 요청한 뒤 로컬에서 NAME_EXACT/NAME_FUZZY를 판정한다.
12. 3주차 보강: 다중 시트 헤더 탐색, 날짜 문자열의 시각 제거, 분수 용량("1/2"→0.5), 중복 행 경고, 정규화 중 예외도 행 단위 FAILED 처리. 합계/소계 행은 별도 처리하지 않음(실제 파일 확인 후 필요하면 추가).
13. 테스트/README를 각 담당 폴더 안에 두었고 패키지 import 경로는 `backend.services.*`(저장소 루트 기준, `__init__.py` 없는 namespace 패키지)로 가정.
