# 기록 없음과 값 미확인 표시 구분

2026-10-29 한국 시간. 시작 codex/mvp-completion / 02cb0b20fbbee08fad80213dfaf44b022afb575c.
전체 원격 fetch 후 origin과 일치/clean 확인. 기존 데이터/브랜치/작업 기록 보존.

## 표시 기준

- 실행된 비교 항목의 previous_record가 명시적 null: **이전: 기록 없음**.
- 실행된 비교 항목의 current_record가 명시적 null: **현재: 기록 없음**.
- 기록 객체가 존재하고 값만 null/빈 값: 기존 표시처럼 해당 필드만 미확인. 0으로 바꾸지 않음.
- 기록 필드 자체가 누락(undefined)된 불확실 구조: 기록 확인 필요. null처럼 추측하지 않음.
- 보류/오류는 비교 항목의 null과 다름. 비교 미실행의 reconciliation_result=null을 빈 이전/현재 기록으로 만들지 않음.
- 사진/HIRA 저장 목록도 최초 조회 성공 전/조회 실패를 빈 목록으로 단정하지 않도록 조회 확인 상태를 분리.

MedicationSnapshot에 화면 전용 presence 메타데이터를 추가하고 공통 RecordSummary로 사진 처리/저장,
HIRA 처리/저장에 적용했다. 일반 HIRA 상세의 이전/현재 타임라인도 같은 기준을 사용한다.
이 presence는 서버 MedicationRecord/API나 저장 JSON에 추가하지 않는다. 원본 비교 기록/상태는 수정하지 않는다.
이전/현재 자료에 다른 약이 있더라도 **해당 비교 항목**의 대응 기록이 null이면 기록 없음으로 표시한다.
전체 DB 자료가 삭제됐다는 뜻이 아니며 실제 복용 상태와 별개다.

## 실제 검사

- pnpm --dir frontend test: 기존 9 script + 새 record-presence, 총 10 script 통과.
- 기존 timeline 검사는 새 화면 메타데이터가 absent임을 명시적으로 확인하며 기존 각 값 미확인/0 미추정 검사는 유지.
- 새 단위 검사: 이전/현재 null, 필드 누락 undefined, 기록이 있는 1회량 null, 데이터 불변을 확인.
- pnpm --dir frontend build: strict TypeScript + Vite 51 modules 성공.
- record-presence.browser.cjs: 5개 묶음 통과.
  - 일반 HIRA 가상 상세의 새로 확인/이전에만 있음 타임라인.
  - 기존 docs/testing/hira-badges 5종 XLSX를 실제 업로드해 HIRA 처리/저장 결과 모두 검사.
  - 비교 보류 배지/미실행/필수값 미확인 사유 유지 및 기록 없음 표시가 생기지 않음을 확인.
  - 저장 상세/최초 사진·HIRA 목록 조회 실패를 가상 503으로 유도, 기록 없음/빈 목록으로 바뀌지 않음을 확인.
  - 사진 Mock single→multiple와 multiple→single로 신규/이전에만 있음의 처리·저장 표시를 확인.
  - HIRA/사진을 360/390/412/1280 폭에서 가로 넘침 없이 확인.
- 기존 관련 브라우저: account-hira 10, account-delete 13, comparison-badges 4, mobile-hira 7 묶음 통과.
  - 가족/계정 접근 제한, 실제 복용 별도 확인, 보류/0건, 삭제, 취소/늦은 응답/불명확 저장의 GET 확인 유지.
  - mobile-hira의 clock.pauseAt(new Date())가 실행 시각 차이로 가끔 과거 시간이 되는 테스트 오류를 발견해,
    설치/정지 시간을 고정된 합성 시각으로 지정하고 동일한 지연/시간 초과 검사를 다시 통과시켰다.
  - 새 사진 저장 검사도 목록 새로고침 완료를 기다린 뒤 최신 결과를 선택하도록 했다. 검사를 약화하지 않음.

묶음 간 중복이 있어 독립 테스트 합계로 합산하지 않는다. 모든 자료/계정은 가상 데이터다.
로컬 SQLite/ASGI API를 쓰는 Chromium 검사이며 실제 DB/Render/Safari·실제 기기 검사는 미실행.
실제 Gemini/MFDS 호출 0회, 브라우저 런타임 오류 0.
백엔드/DB·SSL·권한·비교 엔진·저장 데이터는 수정하지 않아 전체 백엔드 검사는 반복하지 않았다.
실제 Render 재배포는 하지 않는다.
