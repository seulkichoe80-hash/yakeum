// Actual protected multipart/SQLite flow with synthetic users and XLSX only.
const assert=require('node:assert/strict');const {execFileSync}=require('node:child_process');const path=require('node:path');
const {chromium}=require(process.env.YAKEUM_PLAYWRIGHT_MODULE||'playwright');
const base=process.env.YAKEUM_TEST_URL||'http://127.0.0.1:4199/';
const data=JSON.parse(execFileSync(process.env.YAKEUM_TEST_PYTHON||'python3',['-c',"import json,base64;from backend.tests.test_b_d_c_api import _xlsx,_row;from backend.tests.test_hira_hold_v2 import known;from backend.tests.test_photo_upload import image;print(json.dumps({k:base64.b64encode(v).decode() for k,v in {'previous':_xlsx([known()]),'current':_xlsx([known(date='2026-10-01')]),'held':_xlsx([known(),_row(9,'invalid',None,None)]),'empty':_xlsx([]),'photo':image()}.items()}))"],{cwd:path.resolve(__dirname,'../..'),encoding:'utf8'}));
const files=Object.fromEntries(Object.entries(data).map(([k,v])=>[k,Buffer.from(v,'base64')]));
const username='presence_'+Date.now(),password='SYNTHETIC-hira-pass-123';let browser,groups=0;const errors=[],external=[];const pass=s=>{groups++;console.log('passed:',s);};
async function open(page){await page.goto(base);await page.getByRole('button',{name:'개발용 로그인·저장 열기',exact:true}).click();}
async function register(page,name){await open(page);await page.getByLabel('가상 계정 아이디').fill(name);await page.getByLabel('비밀번호',{exact:true}).fill(password);await page.getByRole('button',{name:'가상 계정 가입 후 로그인',exact:true}).click();await page.getByRole('heading',{name:'내 가족 자료',exact:true}).waitFor();}
async function family(page,name){await page.getByLabel('가족 표시 이름').fill(name);await page.getByRole('button',{name:'내 가족 추가',exact:true}).click();await page.getByRole('heading',{name:`${name} · 사진 연결과 저장`,exact:true}).waitFor();return page.getByRole('combobox',{name:'저장할 가족',exact:true}).inputValue();}
const panel=p=>p.getByRole('region',{name:'계정 HIRA 저장',exact:true});const result=p=>panel(p).getByRole('region',{name:'계정 HIRA 결과',exact:true});
async function upload(page,kind='current'){const p=panel(page);await p.getByLabel('이전 HIRA 파일',{exact:true}).setInputFiles({name:'virtual-previous.xlsx',mimeType:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',buffer:files[kind==='empty'?'empty':'previous']});await p.getByLabel('현재 HIRA 파일',{exact:true}).setInputFiles({name:'virtual-current.xlsx',mimeType:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',buffer:files[kind]});}
async function analyze(page){await panel(page).getByRole('button',{name:'HIRA 파일 처리',exact:true}).click();await result(page).getByRole('heading',{name:'HIRA 처리 결과',exact:true}).waitFor();}
async function save(page){await result(page).getByRole('button',{name:'이 HIRA 결과 저장 (보류 포함)',exact:true}).click();await result(page).getByRole('heading',{name:'저장된 HIRA 결과',exact:true}).waitFor();}
async function delayed(page,pattern){let release,seen,done;const gate=new Promise(r=>release=r),arrived=new Promise(r=>seen=r),complete=new Promise(r=>done=r);await page.route(pattern,async r=>{const response=await r.fetch();seen();await gate;try{await r.fulfill({response});}catch{}done();},{times:1});return {arrived:Promise.race([arrived,new Promise((_,rej)=>setTimeout(()=>rej(new Error('interception timeout')),10000).unref())]),release:async()=>{release();await complete;}};}
const fs=require('node:fs');
const kit=path.resolve(__dirname,'../../docs/testing/hira-badges');
const cases=JSON.parse(fs.readFileSync(path.join(kit,'cases.json'),'utf8')).cases;
(async()=>{
 browser=await chromium.launch({headless:true,executablePath:process.env.YAKEUM_BROWSER_EXECUTABLE||'/usr/bin/chromium'});const ctx=await browser.newContext();await ctx.route('**/*',r=>r.request().url().startsWith(base)?r.continue():r.abort());const page=await ctx.newPage();page.setDefaultTimeout(10000);page.on('pageerror',e=>errors.push(e.message));
 await page.goto(base);await page.getByRole('button',{name:'가상 Mock 보기',exact:true}).click();
 for(const [badge,missing] of [['＋ 새로 확인','이전: 기록 없음'],['－ 이전에만 있음','현재: 기록 없음']]){await page.locator('button.record').filter({hasText:badge}).click();await page.getByRole('button',{name:'변경 이력',exact:true}).click();await page.getByText(missing,{exact:true}).waitFor();await page.getByRole('button',{name:'상세 닫기',exact:true}).click();}
 pass('general HIRA detail timeline distinguishes absent previous/current records');
 await register(page,username);await family(page,'기록 구분 가상 가족');
 const inspect=async(region,key)=>{
  const absent=region.getByText(/^(이전|현재): 기록 없음$/);
  if(key==='03_new'){await region.getByText('이전: 기록 없음',{exact:true}).waitFor();assert.equal(await region.getByText('현재: 기록 없음',{exact:true}).count(),0);}
  else if(key==='04_previous_only'){await region.getByText('현재: 기록 없음',{exact:true}).waitFor();assert.equal(await region.getByText('이전: 기록 없음',{exact:true}).count(),0);}
  else assert.equal(await absent.count(),0);
  if(key==='05_hold'){await region.getByText('! 추가 확인 필요',{exact:true}).waitFor();await region.getByText('비교 보류 · 비교 미실행',{exact:true}).waitFor();assert.match(await region.innerText(),/미확인이라 전체 비교를 보류/);}
  for(const width of [360,390,412,1280]){await page.setViewportSize({width,height:900});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));if(key==='03_new')assert(await region.getByText('이전: 기록 없음',{exact:true}).isVisible());if(key==='04_previous_only')assert(await region.getByText('현재: 기록 없음',{exact:true}).isVisible());}
 };
 for(const c of cases){
  await panel(page).getByLabel('이전 HIRA 파일',{exact:true}).setInputFiles(path.join(kit,c.files.previous));await panel(page).getByLabel('현재 HIRA 파일',{exact:true}).setInputFiles(path.join(kit,c.files.current));await analyze(page);await inspect(result(page),c.case);
  await save(page);await inspect(result(page),c.case);
 }
 pass('all five committed XLSX pairs: HIRA processed/saved absent sides explicit; held reasons retained');
 // A failed lookup is not an absent comparison record.
 await page.route('**/hira-runs/*',r=>r.fulfill({status:503,contentType:'application/json',body:JSON.stringify({detail:'가상 조회 실패'})}),{times:1});await panel(page).getByRole('button',{name:/^HIRA 저장 결과 1/}).click();await panel(page).getByRole('alert').waitFor();assert.equal(await result(page).count(),0);assert.equal(await panel(page).getByText(/^(이전|현재): 기록 없음$/).count(),0);pass('failed HIRA lookup does not fabricate absent records');
 await page.route('**/families/*/hira-runs',r=>r.fulfill({status:503,contentType:'application/json',body:JSON.stringify({detail:'가상 목록 조회 실패'})}),{times:1});
 await page.route('**/families/*/runs',r=>r.fulfill({status:503,contentType:'application/json',body:JSON.stringify({detail:'가상 목록 조회 실패'})}),{times:1});
 await family(page,'목록 실패 가상 가족');await panel(page).getByRole('alert').waitFor();
 assert.equal(await page.getByText('저장된 결과가 없습니다.',{exact:true}).count(),0);
 assert.equal(await page.getByText('저장된 HIRA 결과가 없습니다.',{exact:true}).count(),0);
 pass('failed initial photo/HIRA lists are not presented as empty lists');
 // Existing photo Mock: single -> multiple = new; reversed = previous only.
 let photoCount=0;
 for(const [before,after,label,missing] of [['single','multiple','＋ 새로 확인','이전: 기록 없음'],['multiple','single','－ 이전에만 있음','현재: 기록 없음']]){
  await page.getByLabel('현재 사진',{exact:true}).setInputFiles({name:'synthetic.png',mimeType:'image/png',buffer:files.photo});const flow=page.getByRole('region',{name:'사진 업로드 전체 연결',exact:true});await flow.getByLabel('이전 사진 선택').setInputFiles({name:'synthetic.png',mimeType:'image/png',buffer:files.photo});
  for(const [name,scenario] of [['이전',before],['현재',after]]){const side=flow.getByRole('region',{name:`${name} 사진 후보`,exact:true});await side.getByRole('combobox',{name:'가상 추출 사례',exact:true}).selectOption(scenario);await side.getByRole('button',{name:'사진 업로드 후 가짜 후보 보기',exact:true}).click();await side.getByRole('form').first().waitFor();for(const form of await side.getByRole('form').all()){await form.getByRole('checkbox').check();await form.getByRole('button',{name:'추출 내용 확인 완료 (로컬)',exact:true}).click();}}
  await flow.getByRole('button',{name:'수정 후보 B 정규화 미리보기',exact:true}).click();await flow.getByRole('button',{name:'정규화 결과 확인 후 D 비교',exact:true}).click();const article=flow.getByRole('article').filter({hasText:label});await article.getByText('사진 변경 이력',{exact:true}).click();await article.getByText(missing,{exact:true}).waitFor();assert(!/미확인 · 미확인 · 미확인/.test(await article.innerText()));
  await flow.getByRole('button',{name:'확인한 결과와 복용 선택 저장',exact:true}).click();await flow.getByText(/개발용 DB에 저장했습니다/).waitFor();await page.getByRole('button',{name:'저장 목록 새로고침',exact:true}).click();photoCount++;await page.getByRole('button',{name:new RegExp('^저장 결과 '+photoCount+' ')}).waitFor();await page.getByRole('button',{name:/^저장 결과 1/}).click();const saved=page.getByRole('region',{name:'저장된 약 정보',exact:true});await saved.getByText(missing,{exact:true}).waitFor();
  for(const width of [360,390,412,1280]){await page.setViewportSize({width,height:900});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));assert(await saved.getByText(missing,{exact:true}).isVisible());}
 }
 pass('photo new/previous-only processed and saved views distinguish absent record at mobile/desktop widths');
 assert.deepEqual(errors,[]);console.log(JSON.stringify({result:'passed',groups,widths:[360,390,412,1280],runtimeErrors:0,externalApiRequests:0}));
})().catch(e=>{console.error(e);process.exitCode=1;}).finally(async()=>{await browser?.close();});
