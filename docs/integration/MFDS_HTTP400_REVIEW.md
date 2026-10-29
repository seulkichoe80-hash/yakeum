# 식약처 HTTP 400 오프라인 점검

2026-10-29, codex/mvp-completion, 기존 HEAD 9eb7a9a.
이번 추가 식약처/Gemini 호출 0회. 환경·Render 설정 변경/배포 없음.

## 이전 요청에서 확인한 사실

- 사용한 경로는 **DrugPrdtPrmsnInfoService06/getDrugPrdtPrmsnInq06**였다.
- 사용자가 확인 요청한 경로 **DrugPrdtPrmsnInfoService08/getDrugPrdtPrmsnDtlInq08**과 다르다.
- 요청 인자는 serviceKey, pageNo=1, numOfRows=3, type=xml, item_name=타이레놀의 정확히 5개였다.
- Decoding 키를 그대로 urlencode에 넣어 한 번 인코딩한다. 기존 스크립트에서 추가 인코딩은 없었다.
- 현재 환경의 키는 등록되어 있고 `%XX` 형태가 없다(값/길이 출력 없음).
  이것은 키 유효성/활용 승인이나 Decoding 형식의 완전한 검증은 아니다.
- 과거 400 응답 본문은 읽거나 파일에 저장하지 않았고 프로세스가 종료됐다.
  남은 정보는 HTTP 400과 1회 시도이며 당시 서버 오류 코드/메시지는 복구할 수 없다.
  이를 얻기 위한 재호출은 하지 않았다.

**판정:** 요청 경로 불일치는 확인했으나 이것이 HTTP 400의 유일한 원인인지,
08 경로에서 인증/정상 응답이 가능한지는 아직 미검증이다.

## 변경

- 검증 전용 probe의 HTTPS 주소만 사용자 지정 08 경로로 고정했다.
  공식 문서를 추가 조회하여 확정한 것이 아니다. 앱의 기존 api_config.yaml 06 경로는 보존했다.
  앱은 기존 LOCAL_MOCK이며 live 기능을 켜지 않았다.
- `%XX` 형태의 이미 인코딩된 것으로 보이는 키는 네트워크 시도 전 중단한다.
  임의 unquote/키 변환/대체 키 시도는 없다. Decoding 키의 + / =는 urlencode 한 번으로 처리한다.
- HTTPError 본문은 같은 응답 stream에서 최대 16KB(+초과 검사 1바이트)만 읽는다.
  추가 HTTP 요청이 아니다. XML의 포털 gateway cmmMsgHeader와 일반 header 오류 구조를 검사한다.
- 오류 코드는 2~3자리 숫자만, 메시지는 소스의 고정 SAFE_MESSAGES 목록과 정확히 일치한 것만 출력한다.
  나머지는 REDACTED로 표시한다. 원문 메시지의 정규식 치환만으로 비밀값 제거가 충분하다고 가정하지 않는다.
- 비XML/손상 XML/DTD·ENTITY/큰 오류 응답은 원문 없이 상태만 출력한다. stream은 닫는다.
  키/전체 URL/응답 본문은 파일·로그·commit에 남기지 않는다.
- 전송 실패는 DNS, 프록시 연결, TLS 인증서/협상, 시간 초과, 미분류로 구분한다.
  시간 초과의 구체적인 DNS/연결/읽기 구간은 증거 없이 확정하지 않는다.
- 자동 재시도·리다이렉트·다음 페이지 조회 0회 원칙은 유지한다.
  기본 명령은 네트워크를 호출하지 않으며 --live에 새 승인이 필요하다.

## 오프라인 검증

기존 임시 가상환경이 없어 /tmp에 검사 전용 venv를 새로 만들었다. 배포/클라우드 설정 변경이 아니다.
명령:

```sh
/tmp/yakeum-mfdstest/bin/python -m pytest -q backend/services/mfds/tests backend/tests/test_mfds_single_source_offline.py
```

가짜 opener/transport/HTTPError로만 검사한다. 08 경로·정확히 5개 인자·한 번 인코딩,
encoded 키 사전 차단·오류 코드/메시지 허용 목록·키/URL 반사 응답 정제·큰/빈/HTML 오류,
DNS/프록시/TLS/시간 초과 분류·기존 XML/함량/페이지 검사 포함.
제품명/비교 상태/DB/권한/화면 변경이 없어 전체 앱·브라우저 검사는 반복하지 않는다.

## 다음 실제 확인

추가 호출은 이 작업에서 승인되지 않았다. 이후 별도 승인 시 기존 안내대로
`python -m backend.services.mfds.probe --live --name 타이레놀 --page 1 --rows 3`를 최대 1회 실행한다.
실패 시 수집되는 안전한 코드/메시지로 원인을 좁히고 자동 재실행하지 않는다.

결과: **71 passed**, 기존 Starlette/httpx deprecation warning 1건.
초기 기본 Python에는 pytest가 없어 수집 전 종료됐으며 검사 전용 venv에서 위 명령으로 통과했다.

후속: 08 경로의 별도 승인 1회 조회에서 HTTP 503이 발생했다. 당시 헤더/본문은 미보존이며,
원인 미확인 기록과 향후 비XML 진단 보완은 [MFDS_HTTP503_REVIEW.md](MFDS_HTTP503_REVIEW.md)를 따른다.
