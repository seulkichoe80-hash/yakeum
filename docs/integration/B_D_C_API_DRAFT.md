# B→D→C Vertical Slice API Draft

이 문서는 `codex/b-d-c-integration` 브랜치의 로컬 통합 검토용 초안이다. `docs/API_CONTRACT.md`를 변경하거나 팀 공통 계약으로 자동 확정하지 않는다.

## 범위와 제한

- 가상의 HIRA XLSX 두 파일을 deterministic parser로 처리한다.
- previous/current는 호출자가 파일 필드로 명시하며 날짜로 역할을 추론하지 않는다.
- 식약처 조회는 외부 API가 아닌 `MockMfdsClient`의 로컬 샘플만 사용한다.
- 업로드 원본과 결과를 영구 저장하지 않는다.
- 인증·가족 접근권한·DB·사용자 확인 PATCH API는 구현하지 않는다.
- `family_member_id` 일치 확인은 데이터 무결성 검사이며 접근 권한 인증이 아니다.

## Endpoint

```http
POST /api/v1/reconciliations/hira
Content-Type: multipart/form-data
```

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `family_member_id` | UUID 문자열 | 예 | 가상 가족 식별자. 인증 정보가 아님 |
| `previous_file` | XLSX | 예 | 사용자가 이전 자료로 명시한 파일 |
| `current_file` | XLSX | 예 | 사용자가 현재 자료로 명시한 파일 |

각 파일은 `.xlsx`만 허용하며 최대 10MB다. 빈 파일, 손상된 ZIP/XLSX 구조, 50MB를 넘는 압축 해제 크기, 2,048개를 넘는 ZIP 항목, 총 10,000행 또는 시트당 128열을 넘는 파일은 거부한다.

## 로컬 실행

통합 worktree 루트에서 Backend를 로컬 전용으로 실행한다.

```powershell
.venv\Scripts\python -m uvicorn backend.api.main:app --host 127.0.0.1 --port 8000
```

별도 터미널에서 Frontend를 실행한다. Vite의 `/api` 프록시는 위 Backend로 연결된다.

```powershell
Set-Location frontend
pnpm dev
```

외부 식약처 API는 호출하지 않으며 업로드 자료는 요청 처리 후 임시 저장소에서 제거된다.

## 성공 응답

```json
{
  "processing": {
    "parser": "DETERMINISTIC",
    "file_processing": "EXECUTED",
    "official_data_mode": "LOCAL_MOCK",
    "persisted": false
  },
  "accepted_results": {"previous": [], "current": []},
  "review_results": {"previous": [], "current": []},
  "reconciliation_result": {
    "family_member_id": "00000000-0000-4000-8000-000000000001",
    "generated_at": "2026-10-14T00:00:00Z",
    "items": []
  },
  "current_intake_states": []
}
```

- `accepted_results`: `MATCHED`, `PARTIAL`, `UNMATCHED` 원본 NormalizationResult envelope를 보존한다.
- `review_results`: `FAILED` 결과와 원본 warnings/errors를 보존한다.
- `reconciliation_result`: 공통 `ReconciliationResult`를 변경하지 않는다.
- `current_intake_states`: 모두 `UNKNOWN` + `PENDING`에서 시작하며 `verified_by`와 `last_verified_at`은 `null`이다.

## 오류 응답

| HTTP | 조건 |
| --- | --- |
| `400` | 빈 파일, 손상된 XLSX, 구조·압축·행/열 한도 초과 |
| `413` | 파일 크기 10MB 초과 |
| `415` | `.xlsx` 이외 확장자 |
| `422` | UUID 또는 가족/계약 필드 오류 |

## 의료안전 표시 원칙

- `FAILED`는 자료 처리 오류이며 `NEEDS_CONFIRMATION`과 다르다.
- `NEEDS_CONFIRMATION`은 최신 자료에서 확인되지 않았다는 뜻이며 복용 중단을 의미하지 않는다.
- `MAINTAINED`는 비교 가능한 기록상 변화가 발견되지 않았다는 뜻이며 현재 복용 중을 의미하지 않는다.
- `DOSE_CHANGED`는 제품 함량 또는 투약정보 변화이며 복용량 변경 권고가 아니다.
- 사용자 확인 버튼은 저장되지 않는 로컬 데모임을 표시하며 ReconciliationResult를 변경하지 않는다.
