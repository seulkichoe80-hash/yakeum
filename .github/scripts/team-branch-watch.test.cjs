const assert = require('node:assert/strict');
const {test} = require('node:test');
const watch = require('./team-branch-watch.cjs');
const bot = {login:'github-actions[bot]'};
const changed = 'f'.repeat(40);
const integration = '3dd751e6f6b40c11eea113faac50494f38b3c405';
function fixture(options={}) {
 const state={issues:options.issues??[],comments:[],writes:[],heads:{...watch.initialState(),...options.heads},failUpdate:false,failBranch:options.failBranch};
 const issues={
  listForRepo:async()=>({data:state.issues}),
  listComments:async()=>({data:state.comments}),
  create:async args=>{state.writes.push(['create',args]);const issue={...args,number:1,user:bot};state.issues.push(issue);return {data:issue};},
  createComment:async args=>{state.writes.push(['comment',args]);state.comments.push({...args,user:bot});return {data:{}};},
  update:async args=>{if(state.failUpdate) throw Error('update failed');state.writes.push(['update',args]);state.issues[0].body=args.body;return {data:state.issues[0]};},
 };
 const github={rest:{issues,repos:{
  getBranch:async({branch})=>{
   if(state.failBranch===branch) throw Error('ref missing');
   const entry=Object.entries(watch.WATCHED).find(([,v])=>v.branch===branch);
   return {data:{commit:{sha:entry?state.heads[entry[0]]:integration}}};
  },
  compareCommitsWithBasehead:async({basehead})=>({data:{status:basehead.endsWith(integration)?(options.included?'ahead':'diverged'):(options.compareStatus??'ahead'),files:[{filename:'sample/code.py'}]}}),
 }},paginate:async(fn,args)=>(await fn(args)).data};
 const run=(opts={})=>watch.run({github,context:{repo:{owner:'example-owner',repo:'demo'}},core:{info(){}}},{dryRun:false,recipient:'example-owner',...opts});
 return {state,run};
}
function monitor(state=watch.initialState()) {return {number:1,title:watch.TITLE,body:watch.stateBody(state,'example-owner'),user:bot};}

test('first run without changes creates one subscribed monitor baseline only',async()=>{
 const f=fixture();await f.run();assert.equal(f.state.issues.length,1);assert.equal(f.state.comments.length,0);
 assert.deepEqual(watch.readState(f.state.issues[0].body),watch.initialState());
 await f.run();assert.equal(f.state.writes.length,1);
});
test('new A tip comments SHA, files, integration caveat and next work; next run quiet',async()=>{
 const f=fixture({issues:[monitor()],heads:{A:changed}});await f.run();
 assert.equal(f.state.comments.length,1);const body=f.state.comments[0].body;
 assert.match(body,/@example-owner/);assert.match(body,/sample\/code.py/);assert.match(body,/공통 adapter/);assert.match(body,/선별 반영/);
 assert.equal(watch.readState(f.state.issues[0].body).A,changed);
 await f.run();assert.equal(f.state.comments.length,1);
});
test('comment succeeded but state failed: retry does not duplicate notification',async()=>{
 const f=fixture({issues:[monitor()],heads:{B:changed}});f.state.failUpdate=true;
 await assert.rejects(f.run(),/update failed/);assert.equal(f.state.comments.length,1);
 f.state.failUpdate=false;await f.run();assert.equal(f.state.comments.length,1);
 assert.equal(watch.readState(f.state.issues[0].body).B,changed);
});
test('dry run reports changes without Issue creation, comments or state writes',async()=>{
 const f=fixture({heads:{C:changed}});const result=await f.run({dryRun:true});
 assert.equal(result.changes.length,1);assert.deepEqual(f.state.writes,[]);
});
test('missing branch aborts before all writes and retains baseline',async()=>{
 const issue=monitor();const before=issue.body;
 const f=fixture({issues:[issue],heads:{A:changed},failBranch:watch.WATCHED.B.branch});
 await assert.rejects(f.run(),/ref missing/);assert.deepEqual(f.state.writes,[]);assert.equal(issue.body,before);
});
test('malformed baseline fails instead of silently losing changes',async()=>{
 const issue=monitor();issue.body=watch.MARKER;
 const f=fixture({issues:[issue]});await assert.rejects(f.run(),/state is missing/);assert.deepEqual(f.state.writes,[]);
 assert.throws(()=>watch.readState('<!-- task-d-team-watch-state:{"A":"bad"} -->'),/Invalid/);
});
test('human matching Issue is not treated as bot monitor state',async()=>{
 const issue=monitor();issue.user={login:'human'};const f=fixture({issues:[issue]});await f.run();
 assert.equal(f.state.issues.length,2);assert.equal(f.state.writes[0][0],'create');
});
test('reset/behind branch is notified, never merged; already-included tip is explicit',async()=>{
 const f=fixture({issues:[monitor()],heads:{A:changed},compareStatus:'behind',included:true});await f.run();
 assert.match(f.state.comments[0].body,/`behind`/);assert.match(f.state.comments[0].body,/\*\*예\*\*/);
 assert.equal(f.state.writes.length,2);
});
test('duplicate bot monitors stop rather than post into arbitrary Issue',async()=>{
 const f=fixture({issues:[monitor(),{...monitor(),number:2}]});await assert.rejects(f.run(),/Multiple/);
 assert.deepEqual(f.state.writes,[]);
});
test('invalid recipient cannot inject arbitrary mentions or content',async()=>{
 const f=fixture();await assert.rejects(f.run({recipient:'user @other'}),/one GitHub login/);assert.deepEqual(f.state.writes,[]);
});
