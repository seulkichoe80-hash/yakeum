# TASK C Frontend — Mock UI PoC

초기 안내 문서를 실제 C 작업으로 이어갑니다. React + TypeScript + Vite로 가족 선택, 자료 등록·입력 확인, 네 변경상태, 검색, 상세, 확인함, 가족 동의·승인 UI를 시연합니다. 브랜치는 `feature/frontend`이며 코드 변경은 이 폴더로 한정됩니다.

## 실행

Node.js 22.12 이상에서 저장소 루트 기준:

```sh
cd frontend
npm install
npm run dev
```

pnpm 사용자: `pnpm install --frozen-lockfile`, `pnpm dev`. 검증은 `npm test`, `npm run build`; 배포 빌드 미리보기는 `npm run preview`.

## 공통 계약

- 기준: `../docs/DATA_SCHEMA.md`, `../docs/API_CONTRACT.md`.
- `src/types.ts`는 공통 필드 이름을 사용합니다. Decimal은 문자열, 제품 함량은 `ingredients[].product_strength`, 1회 투약량은 `dose_per_administration`과 `unit`으로 구분합니다.
- `src/mock.ts`는 API_CONTRACT의 5번 가상 예시를 그대로 옮긴 개발용 fixture입니다. Reconciliation 상태/사유는 프론트가 계산하지 않습니다.
- 화면용 `Item.id`와 가족 동의 체크 상태는 로컬 UI 메타데이터이며 서버 계약에 추가한 필드가 아닙니다.
- 원본 제품명과 정규화 제품명, 미확정 후보를 구분합니다. 공식 Evidence 구조가 미확정이므로 근거를 생성하지 않습니다.

## 완료한 범위와 남은 범위

현재는 Mock UI PoC입니다. 등록한 파일은 실제로 읽거나 전송하지 않으며 수동 확인·확정 흐름만 시연합니다. 상태는 메모리 안에 유지되고 새로고침 시 초기화됩니다. 동의 체크는 서버 권한을 부여하지 않습니다.

현재 자료의 비교 목록을 표시하며 실제 Current Intake State는 아직 연결하지 않았습니다. API는 Endpoint/인증부터 팀 합의가 필요합니다. 실제 A/B/D 연동, 원본 이미지 대조, 다중 시점 이력, 서버 저장·동의 검증, loading/error/retry, 모바일 실기기 검증, E2E 및 배포는 남아 있습니다. 이 브랜치 push가 C 전체 최종 완료를 뜻하지 않습니다.

기존 개인 저장소는 준비 단계 버전이며 팀 계약에 맞춘 버전은 이 브랜치입니다. 전체 상태는 `HANDOFF.md`를 확인하세요.
