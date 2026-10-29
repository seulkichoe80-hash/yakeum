# 식약처 08 경로 HTTP 503 증거와 안전한 진단 요약

2026-10-29, codex/mvp-completion / 기존 HEAD 923236b.
이번 작업의 추가 식약처/Gemini 호출 0회, 설정 변경/배포 없음.

## 기존 실제 요청에서 남은 증거

사용자가 승인한 08 경로의 타이레놀 첫 페이지/3건 조회를 기존 스크립트로 1회 시도했다.
그때 남은 안전한 출력은 다음과 같다.

```json
{
  "mode": "live",
  "request_attempts": 1,
  "automatic_retries": 0,
  "key_registered": true,
  "error": "HTTP_FAILURE",
  "http_status": 503,
  "failure_stage": "HTTP_RESPONSE",
  "error_body_status": "UNREADABLE_OR_NON_XML_REDACTED"
}
```

- Content-Type: **미보존/미확인**.
- Server, Via, Retry-After, Proxy-Status 등 진단 헤더: **미보존/미확인**.
- 본문: 이전 코드가 메모리에서 읽고 stream을 닫았다. 원문을 파일로 보존하지 않았고 프로세스도 종료됐다.
  원문 복구나 당시 헤더 재확인을 할 수 없다. 이를 위해 재호출하지 않았다.
- 위 본문 분류는 읽기/디코딩/XML 해석 실패를 묶은 상태다. **HTML이었다거나 확실히 XML이 아니었다고 단정하지 않는다.**
- 인증 성공 여부·XML 제품 필드·전체/반환 건수: **미확인**.
- 503을 돌려준 위치: **미확인**. 식약처 원 서버, 공공데이터 게이트웨이, 환경의 중간 프록시 중 하나로 확정하지 않는다.
- 503은 일시적 처리 불가 가능성을 나타내지만 키 오류/경로 오류/서버 장애의 확정 증거가 아니다.

## 다음 실패 때 수집하는 안전한 요약

`probe.safe_http_error`가 동일한 실패 응답의 stream을 한 번 읽는다.
추가 HTTP 요청·리다이렉트·자동 재시도·다음 페이지 조회는 없다.

헤더는 허용 목록에 있는 것만 검사하고 값도 제한한다.

| 헤더 | 출력 범위 |
|---|---|
| Content-Type | xml/json/html/plain/problem+json 등 고정 미디어 타입, 그 외 OTHER_REDACTED |
| Server | nginx/envoy/cloudflare/squid/apache/istio-envoy 고정 종류, 그 외 OTHER_REDACTED |
| Via | 존재 여부만. 내부 주소·프록시 이름은 출력하지 않음 |
| X-Request-ID/X-Correlation-ID/CF-Ray | 존재 여부만. 식별값은 출력하지 않음 |
| Retry-After | 존재 여부와 제한 범위의 숫자 초(0~86400)만. 날짜/임의 문구는 출력하지 않음 |
| X-Cache | HIT/MISS/BYPASS/ERROR만 |
| Proxy-Status | 존재 여부와 고정 error 분류만. proxy 식별자/상세 문구는 출력하지 않음 |
| X-Squid-Error | 고정 DNS/접속/권한/TLS/읽기 시간초과 분류만 |

Set-Cookie, Location, Authorization, WWW-Authenticate 등 나머지 값은 출력하지 않는다.
헤더 전체 dump나 실제 비밀값 정규식 치환을 통한 원문 노출 방식은 사용하지 않는다.
허용된 신호가 있어도 원 서버 장애를 증명하는 것은 아니므로 origin_attribution=UNCONFIRMED를 유지한다.

본문은 16KB(+초과 검사 1바이트)만 읽고 읽은 byte 수·형식 힌트·고정 신호를 남긴다.
형식 힌트는 HTML/JSON_LIKE/XML_LIKE/TEXT이며 Content-Type과 별개로 취급한다.
고정 신호는 upstream connect error, no healthy upstream, service unavailable,
gateway timeout, access denied의 **존재 분류**이며 원문을 복사하지 않는다.
이들 신호도 사용자/서버가 넣은 문구일 수 있어 발생 위치의 확정 근거가 아니다.

- JSON은 code/errorCode와 message/error만 검사해 기존 고정 코드/메시지 규칙으로 출력한다.
- XML은 기존 공공데이터 오류 envelope와 일반 header 경로를 검사한다.
- HTML/일반 텍스트라도 안전한 헤더·본문 형식·고정 신호·크기 요약은 남는다.
- 알 수 없는 JSON/XML 코드·메시지, URL·키·개인정보는 REDACTED 처리한다.
- 큰/읽기 실패/손상 응답도 원문 없이 상태를 남긴다. 원문 파일·DB 저장은 하지 않는다.

## 오프라인 검사와 변경 범위

```sh
/tmp/yakeum-mfdstest/bin/python -m pytest -q backend/services/mfds/tests backend/tests/test_mfds_single_source_offline.py
```

**77 passed**, 기존 Starlette/httpx deprecation warning 1건.
추가 6개는 가상 HTML/JSON/text 503, 허용/비허용 헤더, 본문에 반사된 가상 키/URL,
정확히 한 번의 가상 transport 호출을 검사한다. 실제 API 호출은 없다.
기존 TLS·키 인코딩·페이지/함량 검사를 유지했다.
앱·공통 계약·DB·저장 자료·계정 권한·프론트 변경이 없어 전체 앱/브라우저 검사를 반복하지 않았다.
다음 실제 시도는 별도 승인 전까지 하지 않는다.
