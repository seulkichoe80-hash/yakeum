// Only GitHub metadata is read; no teammate code, installs or medical APIs run.
const WATCHED = {
 A: { branch: 'feature/ai-extraction', initial: 'fa475cf76bbd8d0dd09721dcb694dfa6409fdfb4' },
 B: { branch: 'feature/data-backend', initial: '0721848aab2c4e41765ebd8e529e02d20613fe55' },
 C: { branch: 'feature/frontend', initial: 'd797bc89de5e0fad001d9d152a81f1ff8df9875e' },
};
const INTEGRATION = 'codex/task-d-weekly-integration';
const TITLE = '[TASK D] A/B/C 브랜치 변경 알림';
const MARKER = '<!-- task-d-team-watch:v1 -->';
const STATE = /<!-- task-d-team-watch-state:([^\n]+) -->/;
const SHA = /^[0-9a-f]{40}$/;
const initialState = () => Object.fromEntries(Object.entries(WATCHED).map(([k,v]) => [k,v.initial]));

function readState(body) {
 const match = STATE.exec(body || '');
 if (!match) throw new Error('Monitor Issue state is missing. Restore the last valid state; do not silently reset.');
 const state = JSON.parse(match[1]);
 if (Object.keys(state).sort().join() !== 'A,B,C' || Object.values(state).some(s => !SHA.test(s))) throw new Error('Invalid monitor Issue state');
 return state;
}
function stateBody(state, recipient) {
 return `${MARKER}\n# TASK D 팀원 변경 감시\n\n@${recipient} A/B/C 원격 브랜치를 약 30분 간격으로 확인합니다. 새 push가 감지되면 이 Issue에 댓글을 남깁니다. 이 Issue를 **Subscribe**하고 GitHub 알림 설정에서 이메일/웹 수신을 선택하세요.\n\n커밋 포함 관계는 선별 반영 여부와 다릅니다. 실제 diff·계약·테스트를 검토하기 전에는 통합 완료로 판단하지 않습니다. 자동 merge/push/코드 실행은 하지 않습니다.\n\n아래 상태 표식을 수정하지 마세요. Issue를 닫아도 기존 기록을 재사용하므로 중복 감시 Issue를 만들지 않습니다. 감시를 중단하려면 Actions에서 workflow를 Disable하세요.\n\n<!-- task-d-team-watch-state:${JSON.stringify(state)} -->`;
}
function eventMarker(changes) {
 return `<!-- task-d-team-watch-event:${changes.map(c => `${c.team}:${c.before}:${c.after}`).join('|')} -->`;
}
function inline(value) { return '`' + String(value).replace(/[`\r\n]/g,' ').replace(/</g,'&lt;').replace(/>/g,'&gt;') + '`'; }
function nextSteps(team) {
 return {
  A: '공통 adapter 입력·복수/실패 후보·record:null·수정 후 B 재정규화를 검토하고 사진 Mock 회귀를 확인합니다. 실제 Gemini 호출은 별도 승인 범위입니다.',
  B: 'HIRA parser/adapter·필수값·원본 보존과 v1/v2 계약을 대조하고 정상·실패·함량 미확인·반복 기록 회귀를 확인합니다.',
  C: 'D panel ID namespace·혼합 실패 후보 보존·취소/가족/늦은 응답 보호를 대조하고 접근성·모바일 회귀를 확인합니다. main.tsx를 통째로 복사하지 않습니다.',
 }[team];
}
async function run({github, context, core}, options = {}) {
 const repo = context.repo;
 const dryRun = options.dryRun ?? process.env.WATCH_DRY_RUN === 'true';
 const recipient = options.recipient ?? process.env.TASK_D_NOTIFY_USER ?? repo.owner;
 if (!/^[a-z\d](?:[a-z\d-]{0,38})$/i.test(recipient)) throw new Error('TASK_D_NOTIFY_USER must be one GitHub login');
 // A normal user's matching Issue must not become a bot state store.
 const issues = await github.paginate(github.rest.issues.listForRepo, {...repo,state:'all',per_page:100});
 const monitors = issues.filter(i => !i.pull_request && i.title === TITLE && i.body?.startsWith(MARKER) && i.user?.login === 'github-actions[bot]');
 if (monitors.length > 1) throw new Error('Multiple monitor Issues found; resolve manually before notification.');
 let issue = monitors[0];
 const before = issue ? readState(issue.body) : initialState();
 const after = {};
 // Abort before any write if a ref cannot be read; failed reads never advance state.
 for (const [team, {branch}] of Object.entries(WATCHED)) {
  const result = await github.rest.repos.getBranch({...repo,branch});
  if (!SHA.test(result.data.commit.sha)) throw new Error('Invalid branch SHA');
  after[team] = result.data.commit.sha;
 }
 const changes = Object.keys(WATCHED).filter(k => before[k] !== after[k]).map(team => ({team,before:before[team],after:after[team]}));
 const integration = (await github.rest.repos.getBranch({...repo,branch:INTEGRATION})).data.commit.sha;
 if (!SHA.test(integration)) throw new Error('Invalid integration SHA');
 const sections = [];
 for (const change of changes) {
  const {team} = change;
  const diff = (await github.rest.repos.compareCommitsWithBasehead({...repo,basehead:`${change.before}...${change.after}`})).data;
  const relation = (await github.rest.repos.compareCommitsWithBasehead({...repo,basehead:`${change.after}...${integration}`})).data.status;
  const included = ['identical','ahead'].includes(relation);
  const files = diff.files || [];
  sections.push(`## ${team}: ${inline(WATCHED[team].branch)}\n\n- 이전 ${inline(change.before)} → 현재 ${inline(change.after)}\n- 이전 tip 대비 GitHub 비교 상태: ${inline(diff.status)} (force/reset도 자동 반영하지 않음)\n- D ${inline(integration.slice(0,12))}에 tip 커밋 포함: **${included?'예':'아니오'}**. 선별 반영 여부는 실제 diff로 별도 확인.\n- [GitHub 비교](https://github.com/${repo.owner}/${repo.repo}/compare/${change.before}...${change.after})\n- 변경 파일(최대 12개): ${files.slice(0,12).map(f=>inline(f.filename)).join(', ') || '목록 없음'}\n- 파일 목록/비교는 GitHub API 상한이 있어 전체 변경은 비교 링크에서 확인.\n\n**D 다음 작업:** ${nextSteps(team)}`);
 }
 const body = changes.length ? `${eventMarker(changes)}\n@${recipient} 팀원 변경이 감지됐습니다.\n\n${sections.join('\n\n')}\n\n이 알림은 GitHub 메타데이터 기반입니다. 코드 의미·테스트 통과·팀원 PC 미푸시 작업은 확인하지 않습니다. 자동 통합하지 않습니다.` : '';
 if (dryRun) {
  core.info(`Dry run: ${changes.length} changed branch(es); no Issue writes.`);
  if (body) core.info(body);
  return {dryRun:true,changes};
 }
 if (!issue) {
  issue = (await github.rest.issues.create({...repo,title:TITLE,body:stateBody(before,recipient)})).data;
 }
 if (changes.length) {
  const comments = await github.paginate(github.rest.issues.listComments,{...repo,issue_number:issue.number,per_page:100});
  // Recover from a previous run that posted successfully but failed to save state.
  if (!comments.some(c => c.user?.login === 'github-actions[bot]' && c.body?.startsWith(eventMarker(changes)))) {
   await github.rest.issues.createComment({...repo,issue_number:issue.number,body});
  }
  await github.rest.issues.update({...repo,issue_number:issue.number,body:stateBody(after,recipient)});
 }
 core.info(`Monitor Issue #${issue.number}: ${changes.length} changed branch(es).`);
 return {dryRun:false,changes,issueNumber:issue.number};
}
module.exports = {run, WATCHED, INTEGRATION, TITLE, MARKER, initialState, readState, stateBody, eventMarker};
