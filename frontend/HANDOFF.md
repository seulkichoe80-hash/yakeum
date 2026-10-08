# TASK C 전달 및 완료 상태

2026-10-08 / 브랜치 `feature/frontend` / 경로 `frontend/`

## 최종 판정

C 작업 브랜치에 팀 공통 규격을 따르는 Mock UI PoC를 전달합니다. C 전체 기능의 최종 완료는 아닙니다. 실제 API 연동·E2E·배포가 남아 있습니다.

## 변경 파일과 구현

`src/main.tsx`, `src/style.css`: 기존에 준비한 가족 대시보드, 네 변경 상태 필터, 검색, 타임라인 자료 선택, 상세, 자료 등록·확정 시연, 확인함, 가족 동의 화면.

`src/types.ts`, `src/mock.ts`, `src/domain.ts`: 팀의 MedicationRecord/Ingredient 필드 및 API_CONTRACT 가상 예시. Decimal 문자열, 복수 성분, null·false·약품코드 선행 0을 보존합니다. 사용자 미확정 후보를 별도로 표시합니다. 로컬 화면 키는 API 필드에 포함하지 않습니다.

`package.json`, 잠금 파일, TypeScript 설정, HTML 진입점, `.gitignore`, `tests/contract.cjs`: 실행 및 검증 설정.

## 검증

검증 완료 후 실제 결과를 `VALIDATION.md`에 기록합니다. 테스트 실패 상태를 완료로 보고하지 않습니다.

## 발견·잔여 문제

개인 준비 버전의 축약 타입은 팀 스키마와 달랐으므로, 이 브랜치에서는 팀의 필드로 교체했습니다. 팀의 공통 Schema/API 파일은 수정하지 않았습니다.

실제 Current Intake State/Evidence/Endpoint/인증 정책은 미확정 또는 미연결입니다. A/B/D 담당자가 반환하는 확정 데이터로 adapter를 연결해야 합니다. 현재 자료 비교 목록과 확인된 현재 복용목록을 혼동하지 않아야 합니다.

파일 업로드는 서버 전송이나 AI 추출이 아닌 시연입니다. 사용자 수정 범위 확장, 원본 이미지 대조, loading/error/retry, 포커스 트랩, 모바일 실기기/E2E/권한 검증 및 배포가 남아 있습니다.

## 영향범위

변경은 `frontend/`로 한정됩니다. A/B/D 로직과 공통 Schema/API 변경은 없습니다. 실제 개인정보·건강기록·.env·node_modules·dist는 commit하지 않습니다. develop 병합은 팀 검토 후 진행합니다.
