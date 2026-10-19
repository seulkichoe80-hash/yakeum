# TASK D 1차 MVP — Mock 기반 3분 시연

판정: **Mock 기반 1차 통합 시연 가능**. TASK D 통합안이며 팀 전체 합의나
실제 Gemini/MFDS 연동·운영 준비 완료를 뜻하지 않는다.
시연은 아래 사전 준비를 끝낸 뒤 시작한다.

## 사전 준비와 실행

기존 checkout에서 실행한다. 검증 환경은 Python 3.12.14, Node 24.19.0,
pnpm 11.25.0이다. 아래는 Bash 예시이며 Windows에서는 가상환경 활성화와
환경 변수 설정을 PowerShell 문법으로 바꾼다. 실제 환자 자료는 사용하지 않는다.

```bash
# 저장소 루트, 최초 설치 때
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements.txt
pnpm --dir frontend install --frozen-lockfile

# 백엔드 터미널: 활성화한 프로젝트 Python 사용
python -m uvicorn backend.api.main:app --host 127.0.0.1 --port 8000
```

다른 터미널에서:

```bash
cd frontend
pnpm dev --port 4192
```

브라우저에서 로컬 Vite 4192 포트를 연다. Vite의 `/api` 프록시는 로컬 8000
백엔드로 연결된다 (`frontend/vite.config.ts`). 두 프로세스가 모두 필요하다.
컨테이너/포트 외부 공개/배포는 이번 시연 범위가 아니다.

**필수 API 키·설정 변수는 없다.** 이 경로에는 live provider 선택이나 fallback이 없다.
`GEMINI_API_KEY`, MFDS 키를 넣을 필요가 없으며 넣어도 이 Mock 경로는 실제 API를 쓰지 않는다.
선택적인 브라우저 검사 변수는 다음뿐이다. 앱 설정과 구분한다.

| 변수 | 용도 |
| --- | --- |
| YAKEUM_TEST_URL | Vite 기준 URL, 기본 로컬 4192 |
| YAKEUM_TEST_PYTHON | 가상 XLSX 생성용 프로젝트 Python 실행 파일 |
| YAKEUM_BROWSER_EXECUTABLE | 설치된 Chromium 실행 파일 경로 |
| YAKEUM_PLAYWRIGHT_MODULE | 별도로 설치된 Playwright 모듈 선택 |
| YAKEUM_SCREENSHOT_DIR | 단독 이미지 검토 검사의 선택적 캡처 경로, 민감 자료 사용 금지 |

## 가상 HIRA 파일 준비

저장소 루트에서 프로젝트 Python으로 실행한다. 기존 테스트 도구를 재사용하므로
실제 HIRA 파일을 다운로드하거나 업로드할 필요가 없다. 출력은 OS 임시 폴더이며
Git에 넣지 않는다. 표시되는 제품명은 로컬 MFDS Mock의 정규화 결과다.

```bash
python - <<'PY'
from pathlib import Path
from tempfile import gettempdir
from backend.tests.test_b_d_c_api import _xlsx, _row
from backend.tests.test_hira_hold_v2 import known

folder = Path(gettempdir()) / 'yakeum-mvp-demo'
folder.mkdir(exist_ok=True)
a = known(date='2026-09-01')
b = known(2, date='2026-09-01', code='198800001')
c = known(date='2026-10-19')
c[9] = '2'
files = {
    'previous.xlsx': [a, b],
    'current.xlsx': [c],
    'failure.xlsx': [c, _row(9, 'invalid', None, None)],
    'unknown.xlsx': [_row(1, '2026-10-19', '가상함량미확인', '000000001')],
    'repeat.xlsx': [c, c],
    'empty.xlsx': [],
}
for name, rows in files.items():
    (folder / name).write_bytes(_xlsx(rows))
print(folder)
PY
```

known()은 성분 칸이 빈 가상 행을 만든다. B는 코드로 매칭된 **로컬 Mock 자료의
알려진 성분·함량**을 채운다. 문자열 제품명에서 함량을 추측하는 것이 아니다.
일반 가상성분만 넣으면 함량이 없어서 정상적으로 보류될 수 있다.

## 3분 이내 순서 (목표 2분 45초)

| 시간 | 조작 | 확인할 결과 |
| --- | --- | --- |
| 0:00–0:15 | 새로고침 → 기본 가상 가족 1 → 자료 등록 → 약봉투 사진 → **로컬 Mock 전체 연결 열기** | LOCAL_MOCK 안내. 이미지 선택 없이 실행 가능 |
| 0:15–0:55 | 이전/현재 패널 각각 기본 단일 사례로 **가상 추출 결과 보기** → 각 후보의 원본 대조 체크 → **추출 내용 확인 완료 (로컬)**. 현재의 1회 투약량을 2로 고치고 다시 체크·확인 | 원본과 사용자 수정이 구분됨. 이 확인은 복용 여부 확인이 아님 |
| 0:55–1:15 | **수정 후보 B 정규화 미리보기** → 정규화 결과 확인 → **정규화 결과 확인 후 D 비교** → 결과의 **먹고 있음** → 사진 변경 이력 열기 | B/D 실행, 복용정보 변경, UNKNOWN/PENDING에서 별도 사용자 확인, 이전/현재 이력 |
| 1:15–1:50 | 자료 등록 → 심평원 Excel → 이전 previous.xlsx / 현재 current.xlsx → **가상 XLSX 분석 요청**. 타이레놀 결과 상세·변경 이력 확인. 확인함에서 이전 자료에만 있는 항목의 복용 여부를 별도 확인 | BACKEND·MFDS LOCAL MOCK 표시. 실제 XLSX parser/B/D, 결과·타임라인. 최신 미확인은 중단 판정이 아님 |
| 1:50–2:15 | 자료 등록 → 이전 파일은 유지, 현재만 failure.xlsx → 분석 요청. **HIRA 전체 비교 보류**와 원본 후보 상세 열기 | 비교 결과 null, 이전 비교·복용 확인 표시 없음. FAILED record:null에도 raw_fields·정규화 결과·출처 참조 보존 |
| 2:15–2:35 | 현재만 current.xlsx로 교체 → 다시 분석 → 확인함 | 정상 재처리. 보류 해제, 복용 확인은 UNKNOWN/PENDING에서 새로 시작 |
| 2:35–2:45 | 가족 2로 전환했다가 가족 1로 돌아오거나 새로고침 | 이전 결과가 복구되지 않음. 새 분석 필요, 영구 저장 없음 |

선택 검사: unknown.xlsx는 필수값 미확인 보류, repeat.xlsx는 반복 기록 보류다.
양쪽에 empty.xlsx를 선택하면 **정상 비교 결과 0건**이며 보류/null과 다르다.
잘못된 원본은 수정된 가상 파일로 교체해 재처리한다. null 후보를 UI에서 임의로
MedicationRecord로 생성하거나 비교 보류를 복용 중단으로 처리하지 않는다.

## 실행 범위와 초기화

- 사진: 가상 A JSON → 공통 adapter → 후보 수정/확인 → B 정식 함수 → D 비교.
  이미지를 읽거나 외부로 전송하지 않는다. 단독 C Mock과 전체 연결을 구분한다.
- HIRA: XLSX 파싱과 B/D는 실제 로컬 코드, 공식 데이터 조회는 LOCAL_MOCK이다.
  새 화면은 명시적 `/api/v2/reconciliations/hira`만 소비한다. v1은 기존 소비자용으로 남는다.
- 브라우저 결과/복용 확인은 메모리만 사용한다. 새로고침·새 분석·가족 변경 시
  해당 표시/세션이 초기화된다. DB 저장/복구 기능은 없다.
- 서버 업로드 파일은 요청 동안 임시 디렉터리에 두고 종료 시 삭제한다.
  위에서 직접 생성한 시연 XLSX는 임시 폴더에 남으므로 시연 후 직접 삭제한다.
- 기존 HTML은 외부 Google 폰트를 요청할 수 있다. 외부 **의약품 API** 호출과 다르며,
  자동 브라우저 검사는 해당 폰트 요청을 차단한다.

## 검증과 남은 일

ad3713c에서 백엔드 전체 229개 + 내부 subtest 5개, 프론트 테스트·타입·빌드,
통합 브라우저 12개 그룹/단독 이미지 검토 4개 시나리오가 통과했다.
마감 검토에서는 구현을 바꾸지 않고 선택 필드 누락 회귀 1개를 더해
HIRA v2 관련 16개만 통과 확인했다. 전체 검사는 불필요하게 반복하지 않았다.
상세 근거는 [MVP_CLOSEOUT_REVIEW.md](MVP_CLOSEOUT_REVIEW.md)를 참고한다.

실제 Gemini·MFDS 통신, 실제 HIRA 내보내기 파일 호환성, 로그인·권한·DB 영구 저장·
운영 배포는 이번 검증 근거가 없다. Mock 시연 성공으로 실제 연동 성공을 주장하지 않는다.
대표 기록 자동 선택·부분 그룹 보류·재업로드/출처 간 중복·운영 사진 계약은 남은 정책이다.
HIRA 보류 정책은 [TASK D v2 통합안](HIRA_COMPARISON_HOLD_V2.md)이며 팀 전체 합의 완료가 아니다.
