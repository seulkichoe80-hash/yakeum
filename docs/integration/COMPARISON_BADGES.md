# 비교 결과의 공통 배지와 차이 강조

2026-10-29 한국 시간. 시작 codex/mvp-completion / 929de45b360ade26346edfd91434dade795a603a,
원격 fetch 후 동기화/clean 확인. 비교 로직·DB·권한·실제 복용 상태·API enum을 변경하지 않았다.

## 실제 상태 대조

backend/services/reconciliation/engine.py의 reconcile_records/_has_comparable_dose_change와
PhotoWorkflow의 stage, HIRA v2 comparison.executed를 확인했다.

| 기존 상태/조건 | 표시 | 의미 |
|---|---|---|
| MAINTAINED | 회색 ＝ 기록 동일 | 비교 가능한 동일 제품의 성분 함량·1회량·단위·하루 횟수에 변경이 발견되지 않음 |
| DOSE_CHANGED | 주황 ↔ 복용정보 변경 | 비교 가능한 함량/함량 단위·1회량/단위·횟수 중 차이가 있음 |
| NEW | 파랑 ＋ 새로 확인 | 이전 자료에 대응되지 않은 현재 기록. 새 처방/복용 시작을 자동 판정하지 않음 |
| NEEDS_CONFIRMATION | 보라 － 이전에만 있음 | 현재 자료에서 대응 기록을 확인하지 못함. 복용 중단을 뜻하지 않음 |
| 사진 stage=held / HIRA comparison.executed=false | 노랑 ! 추가 확인 필요 | 비교 미실행. 위 네 비교 상태와 별개이며 보류 사유를 그대로 표시 |

정규화 FAILED/PARTIAL/UNMATCHED를 임의로 NEW/이전에만 있음으로 분류하지 않는다.
알 수 없는 상태는 중립색 '? 비교 상태 확인 필요'로 표시하며 기존 다섯 범주로 추측하지 않는다.
정규화 미리보기(stage=normalized)나 정상 비교 0건은 보류로 표시하지 않는다.
'기록 동일'은 모든 날짜/기간/메모가 같거나 의학적으로 안전하다는 뜻이 아니므로 비교 범위 안내를 함께 표시한다.

## 공통 표시

ComparisonDisplay/비교 표시 helper를 사진 처리/저장, HIRA 처리/저장, 일반 HIRA 결과/상세에 적용했다.
흑백·고대비에서도 기호와 서로 다른 문구가 남는다. 색상은 의학적 안전/위험이 아니라 기록 차이라는 안내와
실제 복용 별도 확인·이전에만 있음≠복용 중단 안내를 결과 영역에 표시한다.
기존 필터/집계의 사용자 표시도 기록 동일/새로 확인/복용정보 변경/이전에만 있음으로 맞췄다.
상태 enum/필터 값은 그대로다.

두 기록이 있을 때 제품 함량·1회 투약량·하루 횟수·기간의 차이를 '이전 → 현재' strong으로 표시한다.
숫자는 float 변환 없이 Decimal 문자열의 불필요한 0만 비교용으로 정리한다. 원본은 변경하지 않는다.
성분 배열 순서만 바뀌어도 허위 함량 변경으로 표시하지 않도록 이름/공식 ID와 값의 비교용 키를 사용한다.
비교 보류/알 수 없는 값은 추측하지 않으며, 한쪽 기록 자체가 없으면 가짜 이전/현재 수치를 만들지 않는다.
기간 차이를 표시하더라도 엔진이 기간을 DOSE_CHANGED 기준으로 쓰지 않으므로 상태 배지를 재분류하지 않는다.

## 실행 검사

- pnpm --dir frontend test: 기존 8 script + 새 comparison-display, 총 9 script 통과.
  다섯 상태 대응/알 수 없는 상태/정밀 문자열·동일 숫자/차이/원본과 상태 불변을 검사.
- pnpm --dir frontend build: strict TypeScript + Vite 51 modules 성공.
- comparison-badges.browser.cjs: 4개 묶음 통과.
  일반 HIRA 가상 화면 네 상태, 사진 처리/저장의 변경·굵은 이전→현재·복용 PENDING,
  HIRA 처리/저장의 변경/유지/보류를 실제 로컬 UI/API로 확인.
  모든 색상의 계산된 전경/배경 대비 4.5:1 이상, forced-colors에서도 기호/문구 표시 확인.
  일반 결과와 계정 결과를 360/390/412/1280 폭에서 수평 넘침/배지 잘림 없이 확인.
- 기존 브라우저: account-hira 10, account-delete 13, photo-hira-integration 13, mobile-hira 7 묶음 통과.
  사진/HIRA 저장·별도 복용·타인/타가족 차단·삭제·보류·0건·취소/늦은 응답/저장 확인 흐름 유지.
  묶음 사이 중복이 있어 독립 테스트 합계로 합산하지 않는다.
- 실제 Gemini/MFDS 호출·실제 건강정보 사용 0회. 브라우저 런타임 오류 0.
- 백엔드/DB/SSL·배포 설정은 수정하지 않아 전체 백엔드 검사를 반복하지 않았다.

가상 계정/자료의 로컬 Chromium 검사이며 실제 Render·Safari/물리적 휴대전화 검사는 미실행이다.
Render 재배포는 하지 않는다. 변경은 현재 통합 브랜치에만 commit/push한다.
