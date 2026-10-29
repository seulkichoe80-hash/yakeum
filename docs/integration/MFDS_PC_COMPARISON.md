# 사용자 컴퓨터에서 식약처 1회 조회 — 클라우드와 비교

2026-10-29. 가상 매칭/DB/Render 설정/배포 변경 없음.
이번 준비 작업에서 식약처·Gemini 추가 호출은 하지 않았다.

## 비교 기준

클라우드 기준 코드: `741d1d93d5b7fd46deb54dcfdd15c1cc7392bf9b`의
`backend/services/mfds/probe.py`. 이 파일은 이번 준비에서 변경하지 않았다.
LF 줄바꿈으로 정규화한 SHA-256:
`bc6caa7029c031c577e8999a1ecacd4ab06dc403910d9ab406aa9edc3873d298`.

동일 조건: 의약품 08 경로 / 타이레놀 / pageNo=1 / numOfRows=3 / type=xml.
클라우드 결과: 1회 시도 → HTTP 503, text/plain, server=envoy, 91바이트,
UPSTREAM_CONNECT_ERROR_TEXT. 인증/제품 정보/원인 위치는 미확인.
자세한 안전한 실제 요약은 [MFDS_HTTP503_REVIEW.md](MFDS_HTTP503_REVIEW.md)에 있다.

`local_probe`는 기존 `probe`를 그대로 호출하는 비공개 키 입력용 wrapper다.
--check-key는 키 등록 여부만 검사(요청 0회), --live만 실제 1회 요청이다.
추가 페이지·리다이렉트·자동 재시도는 하지 않는다.
--live 명령을 다시 실행하면 새 호출이므로 **한 번만 실행**하고 결과를 비교한다.

## 1. 공통 준비

- Git과 Python 3.12를 설치한다. GitHub 계정 권한이 필요하면 정상 로그인 기능을 사용하고
  URL에 토큰/비밀번호를 넣지 않는다.
- 기존 개발 폴더를 덮어쓰지 않도록 아래처럼 **새 폴더**로 받는다.
  폴더가 이미 있으면 다른 새 이름을 사용한다. 다른 작업 브랜치를 바꾸거나 reset하지 않는다.
- 포털의 서비스 활용 승인과 해당 서비스 Decoding(일반) 인증키를 확인한다.
- 키는 채팅·파일·명령문·환경변수 설정 명령에 붙여넣지 않는다.
  아래 Python 프로그램의 **숨김 입력 질문이 나타난 때만** 입력한다.
- VS Code라면 실제 통합 터미널을 사용한다. 디버그 콘솔/IDLE/Jupyter는 피한다.
  숨김 입력을 지원하지 않으면 프로그램이 중단하며 보이는 입력으로 전환하지 않는다.
- 기존 프록시/인증서 설정을 끄지 않는다. 조직/학교망의 차단을 우회하지 않는다.
  로컬에 SSL_CERT_FILE/REQUESTS_CA_BUNDLE이 있으면 해당 CA를 사용하며 TLS 검증을 유지한다.

## 2. Windows — PowerShell

```powershell
git clone --single-branch --branch codex/mvp-completion https://github.com/seulkichoe80-hash/yakeum.git yakeum-mfds-check
cd yakeum-mfds-check
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install "PyYAML>=6.0.2,<7"
```

가상환경 활성화가 필요 없으므로 PowerShell 실행 정책을 바꿀 필요도 없다.
실제 호출 없는 확인:

```powershell
.\.venv\Scripts\python.exe -m backend.services.mfds.local_probe --check-key
```

`MFDS Decoding key (hidden input):`가 나오면 키를 붙여넣고 Enter.
글자나 별표가 안 보여도 정상이다. 키 값 대신 key_registered=true와 request_attempts=0을 확인한다.
이 확인이 끝나면 키는 프로세스 환경에서 제거/이전 값으로 복원된다.

**준비 완료 후 PC에서 딱 한 번 실행할 실제 조회 명령:**

```powershell
.\.venv\Scripts\python.exe -m backend.services.mfds.local_probe --live
```

다시 숨김 질문에 Decoding 키를 입력한다. 키를 명령 뒤에 붙이지 않는다.
명령을 재실행하거나 다른 페이지를 요청하지 않는다.

## 3. macOS — 터미널

Python 3.12와 Git 설치 후:

```sh
git clone --single-branch --branch codex/mvp-completion https://github.com/seulkichoe80-hash/yakeum.git yakeum-mfds-check
cd yakeum-mfds-check
python3.12 -m venv .venv
.venv/bin/python -m pip install 'PyYAML>=6.0.2,<7'
.venv/bin/python -m backend.services.mfds.local_probe --check-key
```

숨김 질문에 키를 넣고 request_attempts=0을 확인한다.
준비 완료 후 아래 명령을 **딱 한 번** 실행하고 숨김 질문에 키를 입력한다.

```sh
.venv/bin/python -m backend.services.mfds.local_probe --live
```

## 4. Linux — 터미널

Git·Python 3.12·venv 지원 패키지가 필요하다. 배포판 패키지 관리자로 설치한다.
이후 macOS와 같은 명령을 사용한다. python3.12가 없으면 설치를 먼저 하고,
시스템 Python/기존 프로젝트 환경을 임의로 교체하지 않는다.

## 5. 출력과 비교 방법

- 첫 JSON 줄의 probe_sha256이 위 값과 같은지 본다. Windows CRLF는 LF로 정규화해 비교한다.
  값이 다르면 기존 코드와 달라진 것이므로 재조회하지 말고 알려준다.
- 두 번째 JSON 줄이 실제 결과다. 출력에는 키·전체 URL·원문·제품명이 없다.
  이 **안전한 JSON 두 줄만** 전달한다. 터미널 전체/환경변수/포털 키 화면은 캡처하지 않는다.
- 결과를 파일로 저장하려면 출력된 안전한 JSON만 별도 메모장에 복사하고 저장소 밖에 둔다.
  원문 응답·HTTP 디버그 로그·키·브라우저 주소는 저장하지 않는다.

| PC 결과 | 판단 가능한 범위 |
|---|---|
| api_success=true / xml_valid=true | PC에서 정상 API 응답을 확인. 동일 시점/동일 경로라는 추가 근거 없이 클라우드 원인을 확정하지 않음 |
| total_count > received_count | 일부 페이지만 받은 것. 단일 후보로 확정하지 않고 추가 페이지를 조회하지 않음 |
| 동일 503/envoy/upstream 신호 | 두 환경에서 유사 증상. 공통 서비스/중간 경로 가능성은 있으나 같은 서버가 원인이라고 단정하지 않음 |
| HTTP 400/인증 관련 허용 메시지 | 키/승인/요청 조건 대조 필요. 키를 보내거나 임의 재조회하지 않음 |
| DNS/프록시/TLS/시간 초과 | 표시된 단계까지만 기록. 인증서 검증을 끄거나 프록시를 우회하지 않음 |

키 등록 true는 인증 성공을 뜻하지 않는다. 제품 단일 후보도 공식 성분·함량 검증 완료가 아니다.
성공하더라도 기존 앱은 LOCAL_MOCK이며 배포본 실제 매칭으로 자동 전환되지 않는다.

## 비밀값 처리의 한계와 중단

숨김 입력은 화면·셸 명령 기록에 키를 넣지 않으며 파일에도 저장하지 않는다.
wrapper는 현재 프로세스의 MFDS_API_KEY를 잠시 설정해 기존 스크립트를 호출하고 finally에서 복원한다.
운영체제 관리자/프로세스 메모리 접근이나 Python 문자열의 안전한 메모리 소거까지 보장하지 않는다.
신뢰할 수 있는 개인 PC에서 실행하고 종료 후 키가 든 클립보드를 비운다.
Ctrl+C로 중단할 수 있으나 요청이 이미 출발했다면 호출됐을 수 있다. 자동 재실행하지 않는다.

## 준비 검증

테스트는 키 입력/네트워크 모두 가짜로 주입했다. 실제 Windows/macOS/Linux PC 검사는 미실행이다.
임시 환경에서 실행한 명령:

```sh
/tmp/yakeum-mfdstest/bin/python -m pytest -q backend/services/mfds/tests backend/tests/test_mfds_single_source_offline.py
```

결과: **84 passed**(비공개 입력 도우미 신규 7개 포함), 기존 Starlette/httpx deprecation warning 1건.
실제 PC에서의 1회 실행과 OS별 실제 터미널 동작은 사용자가 확인해야 한다.

## 이후 사용자 지시

PC 설치·실행 안내는 중단했다. 위 절차는 이전 기록으로만 보존한다.
현재 준비 대상은 [Render 관리자 검증](RENDER_MFDS_ADMIN_PROBE.md)이며 PC 실행을 요구하지 않는다.
