# TASK D — GitHub Issue 기반 팀원 변경 알림

## 구성과 현재 활성화 상태

사용자가 선택한 방식은 **GitHub Issue 알림**이다. 별도 개인 토큰·Slack 웹훅·
SMTP 비밀번호 없이 Actions의 자동 GITHUB_TOKEN을 사용한다.

**TASK D 브랜치에 파일만 올린 상태는 예약 감시 활성화가 아니다.**
원격 기본 브랜치는 `develop`이다. GitHub의 schedule 및 workflow_dispatch 등록을
사용하려면 기본 브랜치에 workflow가 있어야 한다. 기존 지침상 develop 변경과
PR/병합은 금지되어 있으므로, 이 준비 작업에서는 develop을 수정하지 않는다.
알림용 파일만 기본 브랜치에 추가하는 별도 예외 승인이 필요하다.

활성화에 필요한 변경은 아래 3개 파일의 추가뿐이다. TASK D 앱 전체를 develop에
병합할 필요가 없으며 main·팀원 브랜치도 변경할 필요가 없다.

- `.github/workflows/team-branch-watch.yml`
- `.github/scripts/team-branch-watch.cjs`
- `.github/scripts/team-branch-watch.test.cjs` (검증 코드)

이 안내 문서는 TASK D 브랜치에 남긴다.

## 어떤 알림을 받는가

- 감시: A `feature/ai-extraction`, B `feature/data-backend`, C `feature/frontend`.
- 주기: 매시 17분/47분 UTC, 약 30분 간격. GitHub 대기열 때문에 지연되거나
  일부 예약이 누락될 수 있어 실시간·정확한 30분 보장은 아니다.
- 초기 기준: A fa475cf76bbd8d0dd09721dcb694dfa6409fdfb4,
  B 0721848aab2c4e41765ebd8e529e02d20613fe55,
  C d797bc89de5e0fad001d9d152a81f1ff8df9875e.
  활성화 전에 이 기준 이후 push가 있으면 첫 실행에도 감지한다.
- Issue 제목: `[TASK D] A/B/C 브랜치 변경 알림`. 최초 실행 때 bot이 생성한다.
- 새 tip이면 이전/현재 SHA, 비교 링크·파일 일부, D 통합 브랜치에 commit이
  포함됐는지, 담당별 다음 확인 항목을 댓글로 남긴다.
- 사용자 수신처 기본값은 저장소 소유자 `seulkichoe80-hash`다.
  다른 GitHub 개인 계정을 쓰려면 저장소 Actions variable `TASK_D_NOTIFY_USER`를
  그 계정명 하나로 설정한다. @나 이메일 주소·비밀값을 넣지 않는다.
- Issue/댓글에서 수신자를 @mention한다. **이메일 도착 보장은 별개**다.
  본인의 GitHub Notifications 설정에서 웹/이메일을 선택하고 생성된 Issue에서
  Subscribe를 확인한다. 개인 GitHub 알림 설정은 이 코드가 변경하지 않는다.

댓글은 GitHub 메타데이터의 비교이며 코드 의미나 테스트 통과를 평가하지 않는다.
커밋이 조상이 아니라도 cherry-pick/선별 반영돼 있을 수 있으므로 “미반영 확정”으로
표현하지 않는다. D는 실제 diff·계약·테스트를 확인한 후 통합한다. 로컬 미푸시
작업은 감시할 수 없다. 개별 push마다 실행하는 방식이 아니라 주기 중 쌓인 범위를
한 번에 알리며, 확인 사이에 변경 후 원래 SHA로 돌아온 이력은 감지하지 못할 수 있다.

## 활성화 뒤 첫 검증 순서

1. 저장소 Settings에서 Actions가 허용되고 Issues가 켜져 있는지 확인한다.
   권한은 `contents: read`, `issues: write`만 요청한다. 조직 정책이 막으면
   실행이 실패하며 권한을 우회하지 않는다.
2. 기본 브랜치에 위 파일을 승인된 방식으로 추가한다.
3. Actions → **TASK D team branch notifications** → Run workflow에서 기본 브랜치를
   선택하고 `dry_run=true`로 실행한다. 이 모드는 Issue 생성/댓글/상태 저장을 하지 않는다.
4. 로그가 정상일 때 `dry_run=false`로 한 번 실행하여 감시 Issue 생성과 @mention을
   확인하고 Subscribe한다. 이후 schedule 실행은 자동으로 쓰기 모드다.
5. 다음 실제 팀원 push 후 비교 댓글과 마지막 SHA 갱신을 확인한다.
   검증 때문에 팀원 브랜치에 가짜 commit/push를 만들지 않는다.

수동 dry-run과 예약 실행이 겹치지 않게 첫 설치 직후 순서대로 확인하는 것이 좋다.
예약 실행은 기본 브랜치의 파일을 사용한다. 공용 저장소는 장기 비활동 시 GitHub가
예약 실행을 비활성화할 수 있으므로 Actions 상태도 확인한다.

## 상태·중복·실패 처리

상태는 감시 Issue 본문의 HTML comment에 A/B/C SHA만 저장한다. 앱 DB나 파일
영구 저장 기능을 추가하지 않는다. Issue는 알림 메타데이터 저장소다.

- 변화 없으면 댓글/본문 수정 없이 종료한다.
- 댓글 성공 후 상태 저장이 실패하면 bot 댓글 표식을 확인해 재시도 중복을 막는다.
- branch/API 조회 실패나 잘못된 상태 표식이면 실패로 종료하고 SHA를 넘겨 쓰지 않는다.
- bot이 만든 감시 Issue만 사용하며 같은 제목의 사람 Issue는 상태로 신뢰하지 않는다.
- 감시 Issue를 닫아도 재사용한다. 중단은 Actions의 **Disable workflow**를 사용한다.
  Issue를 삭제하면 초기 기준으로 돌아가 과거 변경을 다시 알릴 수 있다.
- API 파일 목록은 상한이 있어 일부만 표시한다. 전체 diff는 비교 링크에서 본다.
- 팀원 브랜치가 force/reset돼도 자동 merge/push하지 않는다. 비교 API가 구간을
  읽을 수 없으면 실행 실패로 남고, 수동으로 원인을 해결해야 한다.

코드 checkout은 workflow 소스만 사용하며 팀원 브랜치를 checkout/실행하거나
설치하지 않는다. 외부 의약품 API·DB·인증·배포·자동 PR/병합은 수행하지 않는다.
GitHub Token은 Actions가 발급하며 로그에 출력하거나 저장하지 않는다.

## 이번 준비 단계의 검증 근거

- `node --test .github/scripts/team-branch-watch.test.cjs`: 10개 Mock 검사 통과.
  최초 baseline/변경 없음, 새 tip 알림, 재실행 중복 방지, 댓글 성공 후 상태 실패 복구,
  dry-run 무쓰기, branch 조회 실패, 손상 상태, 사람 Issue와 구분, reset/포함 관계,
  중복 bot Issue와 잘못된 수신자 거부를 검사했다.
- workflow YAML과 pinned action ref 확인. Node 표준 도구만 사용하며 앱 의존성 변경 없음.
- 기존 앱/의약품 API 코드에는 변경이 없어 앱 전체/브라우저 검사는 반복하지 않는다.
- 이 클라우드의 `gh api repos/seulkichoe80-hash/yakeum`은 **Forbidden**이었다.
  Git은 접근 가능하지만 GitHub REST 권한은 확인되지 않았다. 실제 Actions 실행,
  Issue 생성·알림 도착은 **아직 검증하지 않았다**. API 인증 비밀값을 추출하거나
  개인 토큰을 임의 생성하지 않았다.
