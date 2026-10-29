# 식약처 실조회 검증 준비 — 이번에는 호출하지 않음

2026-10-29, 기준 codex/mvp-completion / 9eb7a9a.
추가 명령은 `python -m backend.services.mfds.probe`다.
기존 앱·LOCAL_MOCK·저장/DB·공통 계약·Render 설정은 변경하지 않았다.
이는 공식 최신 명세 확정이나 실제 연결 성공 기록이 아니다.

## 최초 준비 기록 (이후 상태는 HTTP 400 검토 기록 참고)

- 현재 실행 환경의 `MFDS_API_KEY`: 미등록(값 출력 없이 bool만 확인).
- 실제 식약처/Gemini 요청: 0회. 환경 설정 변경·배포: 없음.
- 오프라인/가짜 연결 관련 61개 검사 통과(신규 probe 16개 포함).
- 실행: `/tmp/yakeum-mfdstest/bin/python -m pytest -q backend/services/mfds/tests backend/tests/test_mfds_single_source_offline.py`.
- 기본 실행 출력: mode=configuration_only, request_attempts=0, key_registered=false.
- 기존 Starlette/httpx deprecation warning 1건. 프론트·브라우저/DB 검사는 이번 독립 CLI 변경에서 재실행하지 않았다.

## 사용자가 준비할 순서 (지금 자동으로 적용하지 않음)

1. 공공데이터포털에서 활용 승인된 의약품 품목허가정보 서비스가 사용자가 지정한 검증용 endpoint의
   `DrugPrdtPrmsnInfoService08/getDrugPrdtPrmsnDtlInq08`에 해당하는지 확인한다.
   이 08 경로는 사용자 지시에 따른 검증 대상이며 공식 최신 명세의 독립 확인은 아니다. 검색 인자/`type=xml`은 기존 요청 형식으로 시험하기 위한 값이며 공식 최신 명세 전체와 대조 완료한 것은 아니다.
   승인 상태·일일 할당량·이용 조건도 확인한다. 서비스가 다르면 실행하지 않고 명세를 먼저 대조한다.
2. Codex의 해당 클라우드 환경 비공개 네트워크 시크릿에 **MFDS_API_KEY**를 등록한다.
   허용 대상은 `apis.data.go.kr`. 기존 GEMINI_API_KEY를 재사용하지 않는다.
   키는 포털의 **Decoding(일반) 인증키**를 사용한다. 스크립트가 URL 인코딩을 한 번 수행한다.
   포털 안내가 다르거나 encoded 키만 있다면 먼저 확인하며 임의 변환하지 않는다.
   채팅·명령행 인자·소스·.env 커밋·로그에는 키를 넣지 않는다.
3. 네트워크에서 `apis.data.go.kr`의 HTTPS 접근을 허용하고 설정을 저장/게시한다.
   적용 절차상 새 실행 환경이 필요하면 새 세션에서 같은 작업 브랜치를 연다.
   이 문서는 설정을 실제 적용하거나 네트워크 허용 상태를 새로 검증하지 않았다.
4. 저장소 루트에서 **호출하지 않는 확인 명령**을 실행한다.

   ```sh
   python -m backend.services.mfds.probe
   ```

   현재 환경에서는 다음 명령을 쓸 수 있다.

   ```sh
   /tmp/yakeum-mfdstest/bin/python -m backend.services.mfds.probe
   ```

   key_registered=true만 확인한다. 이는 키의 유효성·활용 승인·네트워크 성공을 뜻하지 않는다.
   `printenv`, `env`, `echo $MFDS_API_KEY`, 디버그 HTTP 로깅을 사용하지 않는다.
5. 준비 후 사용자가 **공개 제품명 검색, 첫 페이지 3건, 최대 1회** 호출을 별도 승인한다.
   그 전에는 아래 live 명령을 실행하지 않는다. Render에 키를 넣거나 재배포할 필요 없이
   이 클라우드 환경에서 먼저 단독 검증할 수 있다.

## 실행 명령

Python 3.12와 기존 backend 의존성이 필요하다(PyYAML 포함).
기존 환경을 사용하거나 프로젝트의 requirements로 환경을 준비한다.

### 오프라인 파일 검증 — 외부 요청 없음

```sh
python -m backend.services.mfds.probe --xml /절대경로/인증키없는원본응답.xml --page 1 --rows 3
```

`--rows`는 원본의 요청 numOfRows와 맞춘다. 브라우저 안내 문장이나 bare `&`가 들어 있는
첨부 복사본은 실패하는 것이 정상이다. 자동 복구하지 않는다. 정상 원본 XML이 필요하다.
원본 파일은 Git에 넣지 않는다. 출력에는 키·원문·제품명·성분명·전체 URL을 포함하지 않는다.

### 승인 후에만 실행 — 이번 작업에서는 미실행

```sh
python -m backend.services.mfds.probe --live --name 타이레놀 --page 1 --rows 3
```

공개 제품명만 쓴다. 환자/가족/복용 기록이나 실제 건강정보를 검색 인자에 넣지 않는다.
`--live`가 없으면 파일 지정이 없는 모든 기본 실행은 설정 등록 여부만 확인한다.
키 인자는 제공하지 않는다. TLS 인증서 검증과 환경의 프록시 경로를 유지한다.

## 검증 내용과 한도

- 성공 코드 00인 정상 XML만 제품/페이지 검사. 다른 코드·비정상 문서는 정제된 오류로 중단한다.
  기존 설정의 코드 03은 의미 미확인으로 이 도구에서 무자료 성공으로 취급하지 않는다.
- ITEM_SEQ/ITEM_NAME 필수, 중복 제품 ID 거절. MAIN_ITEM_INGR/MATERIAL_NAME 유무,
  성분 개수·직접 매핑된/미확인 함량 개수·보험코드 확인 여부만 출력한다.
- MATERIAL_NAME의 총량/성분 분량/단위/환산은 기존 보수적 매핑을 사용한다.
  과립/환산 함량, 빈 EDI_CODE는 미확인 유지. 제품명 후보가 성분 검증을 뜻하지 않는다.
- pageNo/numOfRows가 요청과 같은지, totalCount와 받은 행 수가 해당 페이지에 맞는지 검사한다.
- 7건 중 첫 3건은 page_valid=true지만 all_candidates_received=false,
  unique_candidate_evidence=false다. 마지막 1건 페이지도 전체 후보 수신으로 표시하지 않는다.
- 전체 0건 성공과 파싱/서버 오류는 구분한다. 전체 1건이어도 사용자 기록의 성분·함량 검증은 false다.
- 앱 수준 요청 시도 최대 1회. 자동 재시도 0회, 리다이렉트 거절, 다음 페이지 자동 조회 0회.
  request_attempts는 시도 수이며 서버 도달/과금 횟수의 확정값이 아니다.
- HTTP 오류 본문은 최대 16KB를 메모리에서만 검사하고 숫자 오류 코드와 고정 허용 메시지만 출력한다.
  알 수 없는 메시지/HTML/URL/키는 원문 대신 REDACTED로 표시한다.
- 타임아웃 15초는 소켓 동작 기준이며 전체 실행시간의 엄격한 상한은 아니다. 응답 크기는 2MB 제한.
- 실패 시 오류 분류/HTTP 숫자 상태만 출력하며 원문 예외/URL/응답 본문은 출력하지 않는다.
  응답/키/캐시를 파일에 저장하지 않고 DB에도 기록하지 않는다.
- 중단하려면 Ctrl+C. 중단/오류 후 같은 명령을 다시 실행하면 새 호출이므로 **자동 또는 임의 재실행 금지**.
  이 CLI는 프로세스 사이의 총 호출 승인 예산을 영구 보존하지 않는다.
- 다른 페이지/추가 시도가 필요하면 앞선 결과를 보고 다시 승인받는다.

## 미완료

실제 endpoint/키/네트워크/원본 XML 성공은 미검증이다. 공식 가이드·한도·요금/이용 조건 확인도 남아 있다.
앱의 live 매칭 활성화, 사용자 원본과 공식 성분/함량의 충돌 판정, 환산/단위 동등성은 이번 범위가 아니다.
이 명령을 준비한 것이 현재 배포본의 Mock 표시를 실제 매칭으로 바꾸지는 않는다.

후속 경로/인코딩/오류 수집 검토: [MFDS_HTTP400_REVIEW.md](MFDS_HTTP400_REVIEW.md).
503 및 비XML 오류의 안전한 헤더/본문 요약: [MFDS_HTTP503_REVIEW.md](MFDS_HTTP503_REVIEW.md).
