// Optional real-browser integration against running local FastAPI and Vite.
// All inputs are virtual; no live Gemini/MFDS or production service is used.
const assert=require('node:assert/strict');
const fs=require('node:fs');const os=require('node:os');const path=require('node:path');
const {execFileSync}=require('node:child_process');
const {chromium}=require(process.env.YAKEUM_PLAYWRIGHT_MODULE||'playwright');
const base=process.env.YAKEUM_TEST_URL||'http://127.0.0.1:4192/';
const familyA='00000000-0000-4000-8000-000000000001',familyB='00000000-0000-4000-8000-000000000002';
const fixtureDir=fs.mkdtempSync(path.join(os.tmpdir(),'yakeum-browser-'));
const checked=[];
const recordCheck=checked.push.bind(checked);
checked.push=(message)=>{console.log('passed:',message);return recordCheck(message);};
function bounded(promise,label) {
 let timer;
 return Promise.race([promise,new Promise((_,reject)=>{timer=setTimeout(()=>reject(new Error(`timed out: ${label}`)),10000);})]).finally(()=>clearTimeout(timer));
}

async function openPhoto(page) {
 await page.goto(base);
 await page.getByRole('button',{name:/↥.*자료 등록/}).click();
 await page.getByRole('combobox',{name:'자료 유형',exact:true}).selectOption('약봉투 사진');
 await page.getByRole('button',{name:'로컬 Mock 전체 연결 열기',exact:true}).click();
 return page.getByRole('region',{name:'사진 Mock 전체 연결',exact:true});
}
function side(workflow,name) {return workflow.getByRole('region',{name:`${name} 사진 후보`,exact:true});}
async function start(section,scenario='single') {
 await section.getByRole('combobox').selectOption(scenario);
 await section.getByRole('button',{name:'가상 추출 결과 보기',exact:true}).click();
 if(scenario==='failed') await section.getByRole('heading',{name:'가상 이미지 분석에 실패했습니다'}).waitFor();
 else await section.getByRole('form').first().waitFor();
}
async function confirm(section) {
 const forms=section.getByRole('form');
 for(let i=0;i<await forms.count();i++) {
  const form=forms.nth(i);
  if(await form.getByRole('textbox',{name:'제품명',exact:true}).inputValue()==='') await form.getByRole('textbox',{name:'제품명',exact:true}).fill('가상 보완 입력');
  await form.getByRole('checkbox').check();
  await form.getByRole('button',{name:'추출 내용 확인 완료 (로컬)',exact:true}).click();
 }
}
async function ready(workflow,scenario='single') {
 for(const name of ['이전','현재']) {const section=side(workflow,name);await start(section,scenario);await confirm(section);}
}
async function preview(workflow) {
 await workflow.getByRole('button',{name:'수정 후보 B 정규화 미리보기',exact:true}).click();
 await workflow.getByRole('heading',{name:/사진 처리 결과/}).waitFor();
}
async function compare(workflow) {
 await preview(workflow);
 await workflow.getByRole('heading',{name:'사진 처리 결과 · 정규화 검토'}).waitFor();
 await workflow.getByRole('button',{name:'정규화 결과 확인 후 D 비교',exact:true}).click();
 await workflow.getByRole('heading',{name:'사진 처리 결과 · 비교 완료'}).waitFor();
}
async function delayed(page,pattern) {
 let release,seen,completed;
 const gate=new Promise(r=>release=r),arrived=new Promise(r=>seen=r),done=new Promise(r=>completed=r);
 const handler=async route=>{
  const response=await route.fetch();seen();await gate;
  try {await route.fulfill({response});} catch { /* cancellation can close request */ }
  completed();
 };
 await page.route(pattern,handler,{times:1});
 return {get arrived(){return bounded(arrived,'intercepted request arrival');},release,get done(){return bounded(done,'intercepted response completion');}};
}

(async()=>{
 const browser=await chromium.launch({headless:true,...(process.env.YAKEUM_BROWSER_EXECUTABLE?{executablePath:process.env.YAKEUM_BROWSER_EXECUTABLE}:{})});
 const context=await browser.newContext({viewport:{width:390,height:844}});
 const page=await context.newPage();page.setDefaultTimeout(10000);
 const errors=[],external=[];page.on('pageerror',e=>errors.push(e.message));
 // The inherited HTML requests a Google font. Block all non-local resources so
 // the browser test stays offline; unexpected API destinations still fail below.
 await context.route('**/*',route=>{
  const url=route.request().url();
  if(!url.startsWith(base)&&!url.startsWith('data:')&&!url.startsWith('blob:')) {
   external.push(url);return route.abort();
  }
  return route.continue();
 });
 try {
  let workflow=await openPhoto(page);await ready(workflow);
  const current=side(workflow,'현재');
  await current.getByRole('textbox',{name:'1회 투약량',exact:true}).fill('2');await confirm(current);
  await compare(workflow);
  const item=workflow.getByRole('article',{name:'사진 비교 항목 1'});
  assert.match(await item.innerText(),/복용정보 변경/);
  assert.match(await item.innerText(),/현재 복용: 잘 모르겠음 · 확인 전/);
  await item.getByRole('button',{name:'먹고 있음',exact:true}).click();
  assert.match(await item.innerText(),/현재 복용: 먹고 있음 · 사용자 확인 완료/);
  await item.getByText('사진 변경 이력',{exact:true}).click();
  assert.match(await item.innerText(),/2026-09-01.*100 mg.*1 정/);
  assert.match(await item.innerText(),/2026-10-19|현재:/);
  await current.getByRole('textbox',{name:'1회 투약량',exact:true}).fill('3');
  await workflow.getByRole('region',{name:'사진 처리 결과'}).waitFor({state:'detached'});
  await confirm(current);await compare(workflow);
  assert.match(await workflow.getByRole('article').innerText(),/현재 복용: 잘 모르겠음 · 확인 전/);
  checked.push('photo edit -> B preview -> D -> independent intake -> timeline -> edit invalidation');

  workflow=await openPhoto(page);await ready(workflow,'multiple');await compare(workflow);
  assert.equal(await workflow.getByRole('article').count(),2);
  const ids=await workflow.locator('[id]').evaluateAll(elements=>elements.map(el=>el.id));
  assert.equal(ids.length,new Set(ids).size,'previous/current candidate error IDs must be unique');
  checked.push('multiple products and compound ingredients');
  const layouts=[];
  for(const width of [360,390,768,1280]) {
   await page.setViewportSize({width,height:900});
   const size=await page.evaluate(()=>({width:document.documentElement.clientWidth,scroll:document.documentElement.scrollWidth}));
   assert.ok(size.scroll<=size.width+1,JSON.stringify(size));layouts.push(size);
  }
  await page.setViewportSize({width:390,height:844});

  workflow=await openPhoto(page);
  await page.route('**/api/local-demo/photos/extract',async route=>{
   const response=await route.fetch();const value=await response.json();
   value.results.push({status:'FAILED',record:null,warnings:[],errors:[{code:'AI_EXTRACTION_FAILED',message:'가상 혼합 응답의 실패 후보',field:null}]});
   await route.fulfill({response,json:value});
  },{times:1});
  const mixed=side(workflow,'현재');await start(mixed);
  assert.equal(await mixed.getByRole('form').count(),2);
  const successful=mixed.getByRole('form',{name:'약품 후보 1',exact:true});
  const failed=mixed.getByRole('form',{name:'약품 후보 2',exact:true});
  assert.match(await failed.innerText(),/가상 혼합 응답의 실패 후보/);
  assert.equal(await failed.getByRole('button',{name:'추출 내용 확인 완료 (로컬)',exact:true}).isDisabled(),true);
  await successful.getByRole('checkbox').check();
  await successful.getByRole('button',{name:'추출 내용 확인 완료 (로컬)',exact:true}).click();
  assert.match(await successful.locator('.confirmation-state').innerText(),/로컬 user_confirmed=true/);
  assert.match(await failed.locator('.confirmation-state').innerText(),/user_confirmed=false/);
  checked.push('mixed extraction keeps successful and failed candidates; failure cannot be confirmed');

  for(const policy of ['repeat','unknown']) {
   workflow=await openPhoto(page);
   await workflow.getByRole('combobox',{name:'정책 보류 검사',exact:true}).selectOption(policy);
   await ready(workflow);await preview(workflow);
   await workflow.getByRole('heading',{name:'사진 처리 결과 · 비교 보류'}).waitFor();
   assert.equal(await workflow.getByRole('article').count(),0);
   assert.match(await workflow.getByRole('region',{name:'사진 처리 결과'}).innerText(),policy==='repeat'?/대표 선택 정책이 미합의/:/성분·함량·단위가 미확인/);
  }
  checked.push('repeat/unknown held without fabricated comparison');
  workflow=await openPhoto(page);await ready(workflow,'missing');await preview(workflow);
  await workflow.getByRole('heading',{name:'사진 처리 결과 · 비교 보류'}).waitFor();
  assert.match(await workflow.getByRole('region',{name:'사진 처리 결과'}).innerText(),/원본 기록이 없거나 추출이 실패/);
  workflow=await openPhoto(page);await start(side(workflow,'현재'),'failed');
  await side(workflow,'현재').getByRole('button',{name:'같은 사례 재시도',exact:true}).click();
  await side(workflow,'현재').getByRole('heading',{name:'가상 이미지 분석에 실패했습니다'}).waitFor();
  assert.equal(await workflow.getByRole('button',{name:'수정 후보 B 정규화 미리보기'}).isDisabled(),true);
  await start(side(workflow,'현재'),'single');
  checked.push('null record held; failed response and retry');

  workflow=await openPhoto(page);
  let delay=await delayed(page,'**/api/local-demo/photos/extract');
  await side(workflow,'현재').getByRole('button',{name:'가상 추출 결과 보기',exact:true}).click();await delay.arrived;
  await side(workflow,'현재').getByRole('button',{name:'가상 분석 취소',exact:true}).click();
  delay.release();await delay.done;
  assert.equal(await side(workflow,'현재').getByRole('form').count(),0);
  delay=await delayed(page,'**/api/local-demo/photos/extract');
  await side(workflow,'현재').getByRole('button',{name:'가상 추출 결과 보기',exact:true}).click();await delay.arrived;
  await page.getByRole('combobox',{name:'가족 구성원',exact:true}).selectOption(familyB);
  await page.getByRole('heading',{name:'화면 시연용 동의와 승인이 필요해요'}).waitFor();
  await page.getByRole('combobox',{name:'가족 구성원',exact:true}).selectOption(familyA);
  delay.release();await delay.done;
  assert.equal(await side(workflow,'현재').getByRole('form').count(),0);
  checked.push('cancelled extraction and A->B->A family late-response rejection');

  await ready(workflow);
  delay=await delayed(page,'**/api/local-demo/photos/process');
  await workflow.getByRole('button',{name:'수정 후보 B 정규화 미리보기'}).click();await delay.arrived;
  await side(workflow,'현재').getByRole('textbox',{name:'1회 투약량',exact:true}).fill('0');
  delay.release();await delay.done;
  assert.equal(await workflow.getByRole('region',{name:'사진 처리 결과'}).count(),0);
  await confirm(side(workflow,'현재'));await compare(workflow);
  checked.push('late normalization after edit rejected; retry and zero preserved');

  // Connection failures must not leave a previously verified result on screen.
  await workflow.getByRole('article').getByRole('button',{name:'먹고 있음',exact:true}).click();
  await page.route('**/api/local-demo/photos/process',route=>route.fulfill({
   status:503,json:{detail:'가상 로컬 처리 실패'},
  }),{times:1});
  await workflow.getByRole('button',{name:'수정 후보 B 정규화 미리보기',exact:true}).click();
  await workflow.getByRole('alert').filter({hasText:'로컬 Mock 처리 실패'}).waitFor();
  assert.equal(await workflow.getByRole('article').count(),0,'failed request must clear previous comparison and verified intake');
  assert.equal(await workflow.getByRole('region',{name:'사진 처리 결과',exact:true}).count(),0);
  await compare(workflow);
  assert.match(await workflow.getByRole('article').innerText(),/현재 복용: 잘 모르겠음 · 확인 전/);
  checked.push('photo request failure removes previous result and verified intake; retry starts unverified');


  // Real virtual XLSX upload, real parser and D engine; official lookup stays Mock.
  execFileSync(process.env.YAKEUM_TEST_PYTHON||'python3',['-c',
   'import sys\nfrom pathlib import Path\nfrom backend.tests.test_b_d_c_api import _xlsx,_row\nfrom backend.tests.test_hira_hold_v2 import known\np=Path(sys.argv[1])\na=known(date="2026-09-01")\nb=known(2,date="2026-09-01",code="198800001")\nc=known(date="2026-10-19")\nc[9]="2"\np.joinpath("previous.xlsx").write_bytes(_xlsx([a,b]))\np.joinpath("current.xlsx").write_bytes(_xlsx([c]))\np.joinpath("failure.xlsx").write_bytes(_xlsx([c,_row(9,"invalid",None,None)]))\np.joinpath("unknown.xlsx").write_bytes(_xlsx([_row(1,"2026-10-19","가상함량미확인","000000001")]))\nr=known(2,date="2026-10-01")\np.joinpath("repeat.xlsx").write_bytes(_xlsx([c,r]))\np.joinpath("repeat-reversed.xlsx").write_bytes(_xlsx([r,c]))\np.joinpath("empty.xlsx").write_bytes(_xlsx([]))',fixtureDir],{cwd:path.resolve(__dirname,'../..')});
  await page.goto(base);await page.getByRole('button',{name:/↥.*자료 등록/}).click();
  const inputs=page.locator('input[type=file]');
  await inputs.nth(0).setInputFiles(path.join(fixtureDir,'previous.xlsx'));
  await inputs.nth(1).setInputFiles(path.join(fixtureDir,'current.xlsx'));
  await page.getByRole('button',{name:'가상 XLSX 분석 요청',exact:true}).click();
  await page.getByRole('heading',{name:'우리 가족 복용정보',exact:true}).waitFor();
  assert.match(await page.locator('main').innerText(),/타이레놀정500밀리그램/);
  assert.match(await page.locator('main').innerText(),/BACKEND.*가상 XLSX/);
  await page.getByRole('button',{name:/타이레놀정500밀리그램/}).first().click();
  await page.getByRole('button',{name:'변경 이력',exact:true}).click();
  assert.match(await page.getByRole('dialog').innerText(),/2026-09-01/);
  assert.match(await page.getByRole('dialog').innerText(),/2026-10-19/);
  await page.getByRole('button',{name:'상세 닫기',exact:true}).click();
  await page.getByRole('button',{name:/✓.*확인함/}).click();
  assert.match(await page.locator('.pending').innerText(),/현재 응답: 잘 모르겠음 · 확인 전/);
  await page.locator('.pending').getByRole('button',{name:'먹고 있음',exact:true}).click();
  assert.match(await page.locator('.pending').innerText(),/현재 응답: 먹고 있음 · 사용자 확인 완료/);
  assert.match(await page.locator('.pending').innerText(),/현재 자료에서 확인되지 않았습니다/);
  checked.push('HIRA XLSX -> real parser -> B/D -> result, intake confirmation and timeline');

  async function uploadCurrent(filename) {
   await page.getByRole('button',{name:/↥.*자료 등록/}).click();
   await page.locator('input[type=file]').nth(1).setInputFiles(path.join(fixtureDir,filename));
   await page.getByRole('button',{name:'가상 XLSX 분석 요청',exact:true}).click();
   await page.getByRole('heading',{name:'우리 가족 복용정보',exact:true}).waitFor();
  }
  for(const filename of ['failure.xlsx','unknown.xlsx','repeat.xlsx','repeat-reversed.xlsx']) {
   await uploadCurrent(filename);
   await page.getByRole('heading',{name:'HIRA 전체 비교 보류',exact:true}).waitFor();
   assert.equal(await page.locator('.pending').count(),0,'prior verified intake must not survive a held result');
   assert.equal(await page.getByRole('dialog').count(),0);
   assert.equal(await page.locator('button.record').count(),0);
   assert.match(await page.locator('main').innerText(),/비교를 실행하지 않았습니다/);
   const sources=page.locator('main details').filter({has:page.locator('summary', {hasText:/후보/})});
   assert.ok(await sources.count()>=3);
   await sources.last().locator('summary').click();
   assert.match(await sources.last().innerText(),/normalization_result/);
   assert.match(await sources.last().innerText(),/raw_fields/);
  }
  checked.push('HIRA failure/unknown/repeat/permuted input held; original and normalization shown; old intake cleared');
  await uploadCurrent('current.xlsx');
  assert.equal(await page.getByRole('heading',{name:'HIRA 전체 비교 보류',exact:true}).count(),0);
  await page.getByRole('button',{name:/✓.*확인함/}).click();
  assert.match(await page.locator('.pending').innerText(),/현재 응답: 잘 모르겠음 · 확인 전/);
  checked.push('HIRA held -> normal reprocess resets intake to UNKNOWN/PENDING');
  await page.getByRole('button',{name:/↥.*자료 등록/}).click();
  await page.locator('input[type=file]').nth(0).setInputFiles(path.join(fixtureDir,'empty.xlsx'));
  await page.locator('input[type=file]').nth(1).setInputFiles(path.join(fixtureDir,'empty.xlsx'));
  await page.getByRole('button',{name:'가상 XLSX 분석 요청',exact:true}).click();
  await page.getByRole('heading',{name:'우리 가족 복용정보',exact:true}).waitFor();
  assert.match(await page.locator('main').innerText(),/정상 비교 결과 0건/);
  assert.equal(await page.getByRole('heading',{name:'HIRA 전체 비교 보류',exact:true}).count(),0);
  checked.push('HIRA executed empty result distinguished from not executed');


  await page.getByRole('button',{name:/↥.*자료 등록/}).click();
  delay=await delayed(page,'**/api/v2/reconciliations/hira');
  await page.getByRole('button',{name:'가상 XLSX 분석 요청',exact:true}).click();await delay.arrived;
  await page.getByRole('button',{name:'HIRA 요청 취소',exact:true}).click();
  delay.release();await delay.done;
  assert.equal(await page.getByRole('heading',{name:'새 자료 등록',exact:true}).count(),1);
  delay=await delayed(page,'**/api/v2/reconciliations/hira');
  await page.getByRole('button',{name:'가상 XLSX 분석 요청',exact:true}).click();await delay.arrived;
  await page.getByRole('combobox',{name:'가족 구성원',exact:true}).selectOption(familyB);
  await page.getByRole('combobox',{name:'가족 구성원',exact:true}).selectOption(familyA);
  delay.release();await delay.done;
  assert.equal(await page.getByRole('heading',{name:'새 자료 등록',exact:true}).count(),1);
  checked.push('HIRA cancellation and A->B->A family late-response rejection');
  assert.deepEqual(errors,[]);
  assert.ok(external.every(url=>new URL(url).hostname==='fonts.googleapis.com'),'unexpected external API attempt');
  console.log(JSON.stringify({result:'passed',checked,layouts,runtimeErrors:errors.length,externalApiRequests:0,blockedFontRequests:external.length},null,2));
 } finally {await browser.close();fs.rmSync(fixtureDir,{recursive:true,force:true});}
})().catch(error=>{console.error(error);process.exitCode=1;});
