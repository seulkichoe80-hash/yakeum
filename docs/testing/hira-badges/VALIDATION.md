# 가상 XLSX 5종 검증 기록

2026-10-29 한국 시간. 기준 codex/mvp-completion / 4423a96cebbb4a12dd1680ea52783cc26ef769a9.
시작 clean, 원격 fetch 후 origin과 일치. 기존 앱/비교 로직/DB는 수정하지 않았다.

| 사례 | 실제 파일/파서 행 수(이전/현재) | 업로드 HTTP | 실행 여부 | 실제 비교 상태 또는 보류 |
|---|---|---|---|---|
| 01_same | 1 / 1 | 200 | 실행 | MAINTAINED / SAME_INGREDIENT_SAME_STRENGTH |
| 02_changed | 1 / 1 | 200 | 실행 | DOSE_CHANGED / STRENGTH_OR_DOSAGE_CHANGED, 1정→2정 |
| 03_new | 0 / 1 | 200 | 실행 | NEW / NEW_RECORD |
| 04_previous_only | 1 / 0 | 200 | 실행 | NEEDS_CONFIRMATION / NOT_FOUND_IN_LATEST_SOURCE |
| 05_hold | 1 / 1 | 200 | 미실행 | UNKNOWN_COMPARISON_FIELDS, 1회량 미확인 |

검증은 파일로 저장된 XLSX 10개를 직접 읽어 수행했다. 다음 경로를 실제 실행했다.

1. openpyxl로 가상 자료 제목/creator/수식 없음/코드 선행 0 확인.
2. 실제 parse_hira_excel에서 각 파일의 예상 행 수 확인.
3. ASGI multipart POST /api/v2/reconciliations/hira에서 실제 업로드 검증 → 파서 → B LOCAL_MOCK → D 비교 실행.
4. 상태·reason_code·출처·미확인 값·원본 보존·복용 UNKNOWN/PENDING 확인.
5. 보류는 엔진 호출 자체를 차단한 상태에서 재검사. 정상화된 원본 후보 이전/현재 각 1개와 source_rows 2개 보존.
6. 03 이전 빈 파일 + 04 현재 빈 파일로 음성 대조: 정상 비교 0건은 executed=true/items=[], 보류 null과 다름.
7. SHA256SUMS와 각 XLSX 파일의 실제 SHA-256 일치 확인.

`python -m pytest backend/tests/test_hira_badge_demo.py backend/tests/test_hira_hold_v2.py -q`:
**23 passed**, 기존 Starlette 경고 1개. 새 키트 검사 7개와 기존 HIRA v2 회귀 16개.
외부 Gemini/MFDS 공급자/DB 접근은 금지하는 패치를 적용했다. DB 호출/외부 API 호출 0회.
출처가 LOCAL_MOCK이고 persisted=false임을 확인했다. 실제 Supabase/기존 SQLite 계정 DB를 열지 않았다.

모든 사례가 HIRA로 재현되어 사진 Mock 대체 경로는 필요하지 않았다.
파일 원본/검증 코드/기록은 Git에 보관하고 ZIP은 다운로드용 산출물로 별도 제공한다.
ZIP 압축 해제/CRC/10개 XLSX 내용의 SHA-256도 패키징 후 확인한다.
실제 Render 화면의 업로드 시연과 실제 사용자의 결과 확인은 아직 별도다. Render 재배포는 하지 않는다.
