# 약이음 TASK A 완료 보고

작성일: 2026년 10월 22일 한국 시간

## 1 최종 판정

안내서의 첫 완료 목표인 “가상 이미지 1장 → 실제 Gemini 응답 → 기존 공통
adapter → 제품별 ExtractionResult 목록”을 완료했다. 오프라인 테스트 31개가
통과했고 실제 합성 약봉투 1장에서 가상 제품 2개와 성분 3개를 확인했다.
이 판정은 TASK A의 첫 실호출 연결에 대한 것이며 전체 서비스 개발 완료를
뜻하지 않는다. AI 결과는 모두 사용자 확인 전 상태다.

## 2 브랜치와 정확한 SHA

- 작업 및 게시 대상: `feature/ai-extraction`
- 작업 시작 SHA: `fa475cf76bbd8d0dd09721dcb694dfa6409fdfb4`
- 검증한 구현 커밋 SHA: `67fbc1d7145d579a5650c8129adf2508f9e3e52b`
- 재사용 코드 출처: `codex/task-d-weekly-integration`의 `9302f95f562262ef34e720c8decc3cf1864b9b6f`
- 별도 A 브랜치 `codex/a-gemini-live`는 사용자 요청에 따라 삭제했고 원격에 게시하지 않았다.
- 구현과 이 보고서는 현재 A 브랜치에서만 저장한다. main/develop/통합 브랜치에 merge하지 않는다.
- 이 보고서를 추가한 최종 전달 커밋은 구현 SHA의 후속 커밋이다. 정확한 최종
  SHA는 전달 메시지와 `git rev-parse HEAD`로 확인하며 구현 SHA와 구분한다.
- Git 작성자 설정이 없어 이번 커밋 작성자는 `Codex <codex@openai.com>`으로 기록했다.

## 3 변경 파일과 재사용 함수

공통 adapter·parser·config·models·prompt·공통 추출 테스트는 위 통합 SHA의
코드를 재사용했다. 복수 제품과 성분, Decimal 문자열, 알 수 없는 값,
공식 ID 미생성, `user_confirmed=false` 처리를 별도 Schema로 다시 만들지 않았다.

- `backend/api/extraction_provider.py`
- `backend/services/extraction/README.md`
- `backend/services/extraction/extraction.py`
- `backend/services/extraction/prompt.py`
- `backend/services/extraction/__init__.py`
- `backend/services/extraction/adapter.py`
- `backend/services/extraction/config.py`
- `backend/services/extraction/models.py`
- `backend/services/extraction/parser.py`
- `backend/services/extraction/requirements.txt`
- `backend/services/extraction/scripts/__init__.py`
- `backend/services/extraction/scripts/run_image.py`
- `backend/services/extraction/scripts/make_synthetic_image.ps1`
- `backend/services/extraction/sdk.py`
- `backend/services/extraction/test_offline.py`
- `backend/tests/test_extraction_contract.py`
- `backend/tests/test_extraction_provider.py`
- `backend/tests/test_extraction_sdk.py`

보고서 파일은 `docs/reports/TASK_A_COMPLETION_2026_10_22.md`이다.

공개 진입 함수는 `backend.api.extraction_provider.extract_image_candidates`다.
이 함수의 인자와 반환 계약은 통합본과 같다. 공급자 호출 부분은
`backend.services.extraction.sdk.request_image`로 위임했다. 단일 모델·SDK
재시도 0회·HTTP 요청 예산 1회·타임아웃 60초·JSON 응답 설정을 적용했다.
기존 A 전용 `extract_medicine_info`는 호환용으로 보존하되 동일 SDK를 사용한다.
팀 연결에는 공통 provider만 사용한다. 이전 `task-a/` 코드는 수정하거나
실행 기준으로 혼합하지 않았다.

## 4 구현 내용과 발견 문제

- import 때 dotenv나 SDK가 필요해 발생하던 실행 오류를 제거했다. 패키지
  방식으로 공통 기능을 import하며 import 시 외부 요청은 없다.
- 고정된 이전 모델 목록과 실패 시 자동 모델 전환을 제거했다. 키·모델을
  명시적으로 설정하고, 설정 누락·공급자 실패·잘못된 JSON을 실패 결과로 반환한다.
- 공급자 오류 원문과 비밀값을 출력하지 않는다. 프롬프트에서 환자 식별정보와
  문서 전체 원문 수집을 제외하고 제품 후보만 요청한다.
- 제품 함량과 1회 투약량을 별도로 보존한다. 모르는 값은 추측하지 않는다.
- 실제 SDK가 503에 재시도하지 않음을 메모리 내 HTTP 전송으로 확인했다.
- 수동 실행 도구는 `--allow-live` 없이는 이미지를 전송하지 않는다.
  `--synthetic-input`과 유효한 가족 UUID·문서 ID·기준일이 필요하다.
- 기존 .venv/venv는 다른 계정 `DiCiA`의 Python 설치를 가리켜 실행되지 않았다.
  기존 폴더를 보존하고 Git 제외 경로 `venv/task-a-runtime`에 Python 3.15.0
  환경을 만들었다. 지정 SDK 버전은 임의로 변경하지 않았다.
- Windows 실행 정책이 이미지 생성 스크립트를 차단했다. 정책을 변경하지 않고
  동일 System.Drawing 명령을 콘솔에서 직접 실행해 합성 PNG를 만들었다.

## 5 실행 명령과 테스트 결과

저장소 루트 `D:\2\yakeum`에서 다음 검사를 수행했다.

```powershell
.\venv\task-a-runtime\Scripts\python.exe -m pip install -r backend/services/extraction/requirements.txt
.\venv\task-a-runtime\Scripts\python.exe -m unittest -v backend.tests.test_extraction_contract backend.tests.test_extraction_provider backend.tests.test_extraction_sdk backend.services.extraction.test_offline
.\venv\task-a-runtime\Scripts\python.exe -m pip check
git diff --check
```

| 검사 | 실제 결과 |
| --- | --- |
| 공통 contract | 15개 통과 |
| 공통 provider | 5개 통과 |
| 고정 SDK 및 수동 도구 | 5개 통과 |
| 기존 A 함수 회귀 검사 | 6개 통과 |
| 최종 unittest 전체 | 31개 통과, 실패 0, 오류 0, 종료 코드 0 |
| pip check | No broken requirements found |
| Git 공백 검사 | 통과 |

subTest는 독립 테스트 수에 더하지 않았다. 초기에는 한글 이스케이프로 인해
잘못된 유형의 테스트 입력이 생성되지 않았고, SDK 가짜 전송 테스트가
Windows TLS에 필요한 환경변수까지 지워 실패했다. 테스트 입력과 환경 설정을
바로잡은 뒤 위 최종 검사를 통과했다. 테스트를 삭제하거나 성공 조건을 낮추지 않았다.

설치 버전: `google-genai==2.30.1`, 명시적 로컬 dotenv 로딩용
`python-dotenv==1.2.4`. 설치 범위는 해당 프로젝트 가상환경뿐이다.

## 6 실제 Gemini 요청 수와 결과

| 항목 | 실제 기록 |
| --- | --- |
| 계정 모델 목록 조회 | 1회 성공, 다음 페이지 조회·재시도 없음 |
| 이미지 분석 | 1회 성공, HTTP 요청 시작 횟수 1회 |
| 모델 | gemini-3.5-flash-lite |
| 자동 재시도 및 자동 모델 전환 | 0회 |
| 입력 | 개인정보 없는 합성 약봉투 PNG 1장 |
| 이미지 크기 | 1400 × 1100, 40,398바이트 |
| 제품 후보 | 2개, 모두 SUCCESS |
| 성분 후보 | 3개 |
| 누락 경고와 오류 | 빈 배열 |
| user_confirmed | 두 제품 모두 false |
| 공식 제품 및 성분 ID | 생성하지 않음, null 유지 |

이미지 SHA256: `c9b3a9682eb1cf4dda8b8b9767b151fd43debec95e66352c4c12488cc6474702`

| 제품 | 성분과 제품 함량 | 1회 투약량 | 하루 횟수 | 일수 | 원본과 대조 |
| --- | --- | --- | --- | --- | --- |
| 가상제품A 100mg | 가상성분A 100mg | 1정 | 2 | 3 | 일치 |
| 가상제품B 복합정 | 가상성분B 25mg + 가상성분C 50mg | 2정 | 1 | 7 | 일치 |

모델은 두 제품의 confidence를 0.99로 반환했다. 이는 모델의 자체 반환값이며
이미지 인식 정확도 통계나 의학적 확신도로 해석하지 않는다. 이 합성 자료에서
제품·성분·함량·투약량·횟수·일수 누락 또는 오인식은 관찰되지 않았다.

## 7 환경변수와 실행 방법

키는 기존 Git 제외 `.env`에서 읽었고 값은 출력하지 않았다.
config는 환경변수만 읽는다. 수동 도구에 `--env-file .env`를 명시할 때만
dotenv를 로딩하며 기존 프로세스 환경변수를 덮어쓰지 않는다.
`GEMINI_API_KEY`와 `YAKEUM_GEMINI_MODEL`이 필수이고 모델 기본값은 없다.

```powershell
git check-ignore .env
$env:YAKEUM_GEMINI_MODEL = 'gemini-3.5-flash-lite'
.\venv\task-a-runtime\Scripts\python.exe -m backend.services.extraction.scripts.run_image --image venv/task-a-artifacts/synthetic_medicine_bag.png --env-file .env --family-member-id 00000000-0000-4000-8000-000000000001 --source-document-id synthetic-medicine-bag-20261022 --record-date 2026-10-22 --synthetic-input
```

위 명령은 외부 요청 없는 사전 검사다. 실제 분석 때에는 별도로 승인한
실행 1회에만 `--allow-live`를 추가했다. 이 보고서를 확인하는 과정에서
다시 호출할 필요는 없다. 이미지·실행 마커·정제된 결과 JSON은
`venv/task-a-artifacts/`에만 있으며 Git 제외다. 비밀 설정·이미지·동영상·캐시를
이번 commit에 포함하지 않는다.

## 8 B C D 연결 함수와 가상 입출력

```python
from backend.api.extraction_provider import extract_image_candidates
from backend.services.extraction import ExtractionContext

context = ExtractionContext(
    family_member_id="00000000-0000-4000-8000-000000000001",
    source_document_id="synthetic-medicine-bag-20261022",
    record_date="2026-10-22",
)
# 호출자가 제공한 합성 이미지 bytes와 MIME을 사용한다.
results = extract_image_candidates(image_bytes, "image/png", context)
```

실제 입력은 합성 PNG bytes였고 출력은 제품별 ExtractionResult 2건의
내부 목록이었다. 각 결과는 `status`, `record`, `warnings`, `errors`를 갖고,
record는 공통 MedicationRecord 구조를 따른다. A는 raw 값을 전달하고
정규화 필드와 공식 ID는 null로 둔다. B는 이 record를 정규화 입력으로,
C는 후보 확인·수정 화면 입력으로 사용할 수 있다. D와는 사용자 확인 상태와
정규화 절차를 거쳐 연동한다. 외부 HTTP 배열 계약을 새로 확정한 것은 아니다.

호출자는 가족 ID·문서 ID·기준일의 유효성과 권한을 관리한다. 반환된
SUCCESS는 자동 확정이 아니며 사용자 확인 전 저장·현재 복용상태 확정으로
취급하지 않는다. 함량 변화와 투약량 변화를 혼합하지 않는다.

## 9 API Schema 변경 여부와 다른 팀 영향

`AGENTS.md`, `docs/DATA_SCHEMA.md`, `docs/API_CONTRACT.md`, B/C/D 핵심 구현은
변경하지 않았다. 업로드 Endpoint·인증·DB·배포를 새로 구현하지 않았다.
`backend/api/extraction_provider.py`는 통합본의 같은 공개 함수로 추가했고
전송 위임 부분이 A의 SDK를 참조한다. 팀장 통합 시 이 파일과 A SDK를 함께
검토해야 한다. 이번 A 브랜치에는 B/C/D 전체 구현을 가져오지 않았으므로
전체 서비스 E2E 통과를 주장하지 않는다.

## 10 남은 문제와 팀장 결정 사항

첫 실호출 목표에 남은 차단 문제는 없다. 다만 처방전·건강기능식품·흐린 이미지·
부분 누락 입력의 실제 인식 성능은 검증하지 않았다. 가상 JSON 검사와 실제
이미지 인식 검증은 구분했다. 다양한 입력, 다른 계정·모델, 화면 업로드,
인증·가족 권한·DB·전체 E2E·배포는 후속 범위다.

팀장은 통합 시점과 B/C/D 연결 검증, 재업로드 ID 정책, 실제 호출 비용 범위를
확인하면 된다. 공통 계약에 남아 있는 TODO를 이번 A 작업에서 임의 확정하지 않았다.
추가 Gemini 분석이나 모델 조회는 이번 완료 확인을 위해 자동 실행하지 않는다.

## 11 근거와 게시 확인 방법

- [이미지 입력 지원 모델 공식 문서](https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash-lite)
- [SDK HTTP 및 재시도 옵션 공식 문서](https://googleapis.github.io/python-genai/genai.html)
- [python dotenv 패키지 버전](https://pypi.org/project/python-dotenv/1.2.4/)

일반 push의 대상은 `origin feature/ai-extraction`뿐이다. force push·PR·merge는
하지 않는다. 최종 전달 때 아래 명령의 로컬 SHA와 원격 SHA 일치 및 깨끗한
작업 트리를 확인한다.

```powershell
git rev-parse HEAD
git ls-remote origin refs/heads/feature/ai-extraction
git status --short --branch
```
