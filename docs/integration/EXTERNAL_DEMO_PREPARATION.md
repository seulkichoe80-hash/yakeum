# 외부 가상 시연 배포 준비 검토

2026-10-27. 시작 codex/mvp-completion / 4a050552d1516df40478a9b045b596152968b06e,
작업 트리 clean, 전체 원격 fetch 후 이후 통합 변경 없음. 팀원/main/develop 브랜치 보존.
외부 공개·호스팅 신청·PR·병합은 하지 않았다. 로컬 컨테이너 검증이며 사용자 접속 URL 생성이 아니다.

## 준비한 구성

- 기존 단일 이미지(React 정적 빌드+FastAPI 같은 Origin) 유지. Compose 예행연습 파일 추가.
- UID/GID 10001, 읽기 전용 루트, /tmp tmpfs, /data 영속 볼륨, capability 제거/no-new-privileges.
- Compose는 loopback만 노출. 실제 Gemini/MFDS 키는 빈 값, Gemini live=0.
- YAKEUM_EXTERNAL_DEMO=1일 때 development/정적 화면/개발 계정/HTTPS Origin/Secure 쿠키/
  Gemini 비활성/소스 밖 절대 DB 경로 조건을 검사하고 모순된 설정이면 시작 거부.
- API 응답 no-store, nosniff/referrer-policy 보강. 데이터 계약·비교 정책 변경 없음.
- 전체 화면과 계정 안내에서 가상 자료 전용, Mock/승인된 합성 Gemini 시험, 개발용 인증·저장 한계 구분.
- 실행 방법과 사용자 준비사항은 deploy/README.md 참고.

외부 flag는 실제 TLS·접근 제한·영속 디스크·운영 보안을 자동 구성하거나 검증하지 않는다.
초대된 시험자 접근 제한은 호스팅/앞단에서 별도 적용해야 한다. 실제 건강정보는 허용하지 않는다.

## 현재 환경에서 실제 검사

- Python `/tmp/yakeum-live-venv/bin/python -m pytest backend -q`: **370 passed**, 내부 5 subtests passed,
  기존 Starlette deprecation 경고 1개. 하위 검사를 별도 테스트 합계에 더하지 않음.
- `pnpm --dir frontend test`: 기존 7개 스크립트 통과.
- `pnpm --dir frontend build`: strict TypeScript/Vite 48 modules 성공.
- 명시적 로컬 Docker socket에서 Compose config --quiet, 이미지 build, up, health, no-store 헤더 확인.
- 외부 flag+HTTP Origin인 실제 컨테이너에서 startup 거부 확인(외부 요청 없음).
- 최종 이미지 `sha256:c1f177fe919ee05ceaedc6e6350c27e38f848705c980551d2e739c336fc3642a`.
- 최종 로컬 Compose 컨테이너에서 사진·HIRA·계정 저장·삭제 브라우저 검사 아래 모두 통과.

| Playwright 스크립트 | 검사 묶음 | 대상 |
|---|---:|---|
| account-delete.browser.cjs | 13 | 최종 Compose/SQLite |
| account-storage.browser.cjs | 7 | 최종 Compose/SQLite |
| account-hira.browser.cjs | 10 | 최종 Compose/SQLite |
| photo-upload.browser.cjs | 10 | 최종 Compose |
| photo-hira-integration.browser.cjs | 13 | 최종 Compose |
| account-gemini.browser.cjs | 13 | 같은 최종 화면 빌드+별도 오프라인 SDK harness |

사진/HIRA 등록·후보 확인·비교·보류·별도 복용·저장·재조회·삭제,
가족/계정 분리, 취소/가족 A→B→A/늦은 응답을 실제 브라우저에서 조작했다.
360/390/768/1280 폭 가로 넘침 없음, 런타임 오류 0. 묶음 사이 중복이 있어 독립 테스트로 합산하지 않음.
첫 안내문이 기존 aside CSS 때문에 버튼을 가리던 오류를 발견했고 일반 div 안내 스타일로 수정했다.
최종 이미지를 다시 빌드하고 새 가상 DB에서 모든 브라우저 스크립트를 재실행해 통과했다.
최종 컨테이너 재시작 전후 DB 내용 집계 해시 일치, 실제 API 비활성·키 빈 값 확인.
실제 행/세션 값/키 값은 출력하지 않았다.

## 실제 연동/미검증 구분

- 이번 실제 Gemini 분석/모델 목록/MFDS 요청 모두 0회. 오프라인 Gemini 전송 9회는 가짜 SDK 요청이다.
- 이전 승인 합성 Gemini 시험 1회 성공은 유지. 실제 일반 약봉투 정확도 검증이 아니다.
- 앱 공식 약품 매칭은 Mock. 코드 있는 RealMfdsClient의 존재가 운영 연결 성공을 뜻하지 않는다.
- 식약처 포털 문서는 프록시 CONNECT 403으로 차단. 공식 최신 API 주소/신청 승인 조건/응답/요금·할당량
  확인은 미완료. MFDS_CONNECTION_PREPARATION.md에 기존 미검증 설정과 확인할 항목을 구분했다.
- 서비스 신청, 실제 건강정보, 실제 HTTPS/도메인/호스팅·앞단 접근 제한·공개 URL·운영 배포 미실행.
- 실제 사용자가 참여한 사용자 시험과 GitHub CI 원격 성공은 이번 로컬 검사에 포함하지 않음.
- 운영 인증·DB 암호화·자동 백업·운영 복원/삭제 정책·의존성 보안 감사는 완료하지 않았다.

## 사용자 준비와 다음 단계

1. 단일 컨테이너+영속 디스크+HTTPS+초대 대상 접근 제한이 가능한 호스팅/VM 계정과 예산 결정.
2. 공개 범위(초대된 가상 자료 시험자), 보관 기간, HTTPS 주소/도메인 결정.
3. 별도 외부 게시 지시 후 배포 설정 적용 및 실제 주소에서 브라우저/접근 권한/재시작 검증.
4. 식약처 공개 가이드 확보 또는 www.data.go.kr 문서 도메인 허용.
5. 공식 데이터셋 확인 후 사용자가 활용 승인/키·요금/할당량을 확인. 신청·실조회는 별도 지시 전 미실행.
6. 키는 채팅/Git가 아니라 해당 호스팅의 비밀 설정에만 입력. Mock 시연에는 Gemini/MFDS 키가 필요 없다.

## 호스팅 추천·공유 입구 후속

시작 SHA 463acd53c494a0b159baff57e03134242c8371db 이후의 배포 직전 준비는
[Render 전용 안내](../../deploy/RENDER_PREDEPLOY.md)를 따른다.
이제 외부 flag=1에서는 공유 입구 아이디·최소 20자 비밀번호도 필수다.
화면/API/문서 전부 입구로 보호하고 최소 health만 예외로 둔다. 앱 계정/가족 권한은 별도 유지한다.
위 초기 검토의 '접근 제한은 별도 준비' 중 작은 초대 시연용 입구 부분을 구현했으며,
호스팅 WAF/개별 초대/시도 제한·실제 TLS 설정 완료를 뜻하지 않는다.

### 후속 실제 검사 결과

- 백엔드 전체 **374 passed + 5 subtests passed**, 기존 Starlette 경고 1개.
- 프론트 기존 7개 script와 strict TypeScript/Vite build 통과(48 modules).
- Render YAML은 로컬 YAML 파싱/단일 인스턴스/디스크/키 비움/수동 배포 의도 검사만 통과.
  공식 Blueprint schema 검증·계정 적용은 미실행이라 적용 가능한 파일이라고 확정하지 않는다.
- 새 demo-gate.browser.cjs: 익명 /·/docs·/openapi.json·가족 API 401, 잘못된 입구 비밀번호 401,
  올바른 입구 후 화면/계정 로그인 폼 표시, 입구 통과 후에도 앱 세션 없으면 401 확인.
  로컬 HTTP 검사이며 실제 HTTPS 인증서 검증을 대신하지 않음.
- 별도 HTTPS base_url TestClient에서 입구 + 앱 로그인 + Secure/HttpOnly/SameSite 쿠키 + CSRF 확인.
  base_url을 이용한 의미 검사이지 실제 TLS handshake가 아님.
- 최종 Docker 이미지 build 및 로컬 Compose의 기존 브라우저 5개 스크립트 모두 통과:
  account-delete 13, account-storage 7, account-hira 10, photo-upload 10, photo-hira-integration 13개 묶음.
  정상/보류/별도 복용/저장/재조회/삭제/타인·타가족 거부/취소/늦은 응답·모바일 폭 검사 포함.
- 같은 최종 컨테이너 재시작 전후 DB 내용 집계 해시 일치. 실제 API 키 없음/실호출 꺼짐 확인.
- 실제 외부 배포/공개, 결제/서비스 생성, Gemini 분석/모델 목록/MFDS 호출 모두 미실행(각 0회).
  기존 Gemini 합성 1회 성공 기록과 현재 Mock 시연 범위는 구분한다.
- 실제 TLS·호스팅 디스크 권한·요금/현행 플랜·공식 스키마·외부 주소 권한/로그는 배포 승인 후 검증.
- 현재 SQLite/계정은 가상 자료 개발용이며 실제 건강정보의 운영 서비스가 아님.
