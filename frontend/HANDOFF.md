# TASK C 전달 및 완료 상태

최초 전달 2026-10-08 · 갱신 2026-10-19 / 브랜치 `feature/frontend` / 경로 `frontend/`

## 최종 판정

C 작업 브랜치에 팀 공통 규격을 따르는 Mock UI PoC를 전달합니다. C 전체 기능의 최종 완료는 아닙니다. 실제 API 연동·E2E·배포가 남아 있습니다.

2026-10-19에는 새 TASK C 범위에 맞춰 이미지 추출 후보별 원본 대조·수정·확인 Mock을 추가했습니다. 정상·복수·누락·실패, 원본 보존, 확인 보류와 되돌리기, 취소·재시도, 390px 키보드 동작을 검증했습니다. 자세한 내용은 `IMAGE_REVIEW_HANDOFF.md`에 있습니다.

## 변경 파일과 구현

`src/main.tsx`, `src/style.css`: 기존에 준비한 가족 대시보드, 네 변경 상태 필터, 검색, 타임라인 자료 선택, 상세, 자료 등록·확정 시연, 확인함, 가족 동의 화면.

`src/types.ts`, `src/mock.ts`, `src/domain.ts`: 팀의 MedicationRecord/Ingredient 필드 및 API_CONTRACT 가상 예시. Decimal 문자열, 복수 성분, null·false·약품코드 선행 0을 보존합니다. 사용자 미확정 후보를 별도로 표시합니다. 로컬 화면 키는 API 필드에 포함하지 않습니다.

`package.json`, 잠금 파일, TypeScript 설정, HTML 진입점, `.gitignore`, `tests/contract.cjs`: 실행 및 검증 설정.

## 검증

검증 완료 후 실제 결과를 `VALIDATION.md`에 기록합니다. 테스트 실패 상태를 완료로 보고하지 않습니다.

## 발견·잔여 문제

개인 준비 버전의 축약 타입은 팀 스키마와 달랐으므로, 이 브랜치에서는 팀의 필드로 교체했습니다. 팀의 공통 Schema/API 파일은 수정하지 않았습니다.

실제 Current Intake State/Evidence/Endpoint/인증 정책은 미확정 또는 미연결입니다. A/B/D 담당자가 반환하는 확정 데이터로 adapter를 연결해야 합니다. 현재 자료 비교 목록과 확인된 현재 복용목록을 혼동하지 않아야 합니다.

파일 업로드는 서버 전송이나 AI 추출이 아닌 시연입니다. 사용자 수정 범위 확장, 원본 이미지 대조, loading/error/retry, 모바일 실기기/E2E/권한 검증 및 배포가 남아 있습니다.

위 문단은 초기 전달 당시 범위입니다. 새 사진 Mock에서는 원본 이미지 미리보기, 다중 성분/투약정보 수정, 로딩·실패·취소·재시도를 보완했습니다. 실제 API 저장·권한·E2E·배포는 계속 남아 있습니다. 팀장 통합본의 HIRA·Current Intake 구현 여부는 C 원본의 미연결 상태와 구분합니다.

## 영향범위

변경은 `frontend/`로 한정됩니다. A/B/D 로직과 공통 Schema/API 변경은 없습니다. 실제 개인정보·건강기록·.env·node_modules·dist는 commit하지 않습니다. develop 병합은 팀 검토 후 진행합니다.
