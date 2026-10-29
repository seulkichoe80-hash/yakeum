// Actual protected multipart/SQLite flow with synthetic users and XLSX only.
const assert=require('node:assert/strict');const {execFileSync}=require('node:child_process');const path=require('node:path');
const {chromium}=require(process.env.YAKEUM_PLAYWRIGHT_MODULE||'playwright');
const base=process.env.YAKEUM_TEST_URL||'http://127.0.0.1:4199/';
const data=JSON.parse(execFileSync(process.env.YAKEUM_TEST_PYTHON||'python3',['-c',"import json,base64;from backend.tests.test_b_d_c_api import _xlsx,_row;from backend.tests.test_hira_hold_v2 import known;from backend.tests.test_photo_upload import image;print(json.dumps({k:base64.b64encode(v).decode() for k,v in {'previous':_xlsx([known()]),'current':_xlsx([known(date='2026-10-01')]),'held':_xlsx([known(),_row(9,'invalid',None,None)]),'empty':_xlsx([]),'photo':image()}.items()}))"],{cwd:path.resolve(__dirname,'../..'),encoding:'utf8'}));
const files=Object.fromEntries(Object.entries(data).map(([k,v])=>[k,Buffer.from(v,'base64')]));
const username='mobile_'+Date.now(),password='SYNTHETIC-hira-pass-123';let browser,groups=0;const errors=[],external=[];const pass=s=>{groups++;console.log('passed:',s);};
async function open(page){await page.goto(base);await page.getByRole('button',{name:'개발용 로그인·저장 열기',exact:true}).click();}
async function register(page,name){await open(page);await page.getByLabel('가상 계정 아이디').fill(name);await page.getByLabel('비밀번호',{exact:true}).fill(password);await page.getByRole('button',{name:'가상 계정 가입 후 로그인',exact:true}).click();await page.getByRole('heading',{name:'내 가족 자료',exact:true}).waitFor();}
async function family(page,name){await page.getByLabel('가족 표시 이름').fill(name);await page.getByRole('button',{name:'내 가족 추가',exact:true}).click();await page.getByRole('heading',{name:`${name} · 사진 연결과 저장`,exact:true}).waitFor();return page.getByRole('combobox',{name:'저장할 가족',exact:true}).inputValue();}
const panel=p=>p.getByRole('region',{name:'계정 HIRA 저장',exact:true});const result=p=>panel(p).getByRole('region',{name:'계정 HIRA 결과',exact:true});
async function upload(page,kind='current'){const p=panel(page);await p.getByLabel('이전 HIRA 파일',{exact:true}).setInputFiles({name:'virtual-previous.xlsx',mimeType:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',buffer:files[kind==='empty'?'empty':'previous']});await p.getByLabel('현재 HIRA 파일',{exact:true}).setInputFiles({name:'virtual-current.xlsx',mimeType:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',buffer:files[kind]});}
async function analyze(page){await panel(page).getByRole('button',{name:'HIRA 파일 처리',exact:true}).click();await result(page).getByRole('heading',{name:'HIRA 처리 결과',exact:true}).waitFor();}
async function save(page){await result(page).getByRole('button',{name:'이 HIRA 결과 저장 (보류 포함)',exact:true}).click();await result(page).getByRole('heading',{name:'저장된 HIRA 결과',exact:true}).waitFor();}
async function delayed(page,pattern){let release,seen,done;const gate=new Promise(r=>release=r),arrived=new Promise(r=>seen=r),complete=new Promise(r=>done=r);await page.route(pattern,async r=>{const response=await r.fetch();seen();await gate;try{await r.fulfill({response});}catch{}done();},{times:1});return {arrived:Promise.race([arrived,new Promise((_,rej)=>setTimeout(()=>rej(new Error('interception timeout')),10000).unref())]),release:async()=>{release();await complete;}};}
(async()=>{
 browser=await chromium.launch({headless:true,executablePath:process.env.YAKEUM_BROWSER_EXECUTABLE||'/usr/bin/chromium'});
 const ctx=await browser.newContext();await ctx.route('**/*',r=>{if(!r.request().url().startsWith(base)){external.push(r.request().url());return r.abort();}return r.continue();});
 const page=await ctx.newPage();page.setDefaultTimeout(10000);page.on('pageerror',e=>errors.push(e.message));
 await register(page,username);const fa=await family(page,'모바일 가상 가족');
 await upload(page);await analyze(page);assert.equal(await panel(page).getByText(/HIRA 작업 중/).count(),0);
 await save(page);await result(page).getByRole('button',{name:'먹고 있음 HIRA 저장',exact:true}).click();await result(page).getByText('실제 복용: 먹고 있음 · 사용자 확인 완료',{exact:true}).waitFor();
 // Add a photo snapshot without external providers so both list displays are checked.
 const root=base+`api/dev-account/families/${fa}`;const me=await (await ctx.request.get(base+'api/dev-account/me')).json();const headers={Origin:new URL(base).origin,'X-CSRF-Token':me.csrf_token};const docs=[];
 for(let i=0;i<2;i++){const r=await ctx.request.post(root+'/photos/extract',{headers,multipart:{record_date:'2026-10-27',source_type:'MEDICINE_BAG',file:{name:'synthetic.png',mimeType:'image/png',buffer:files.photo}}});assert.equal(r.status(),200);docs.push(await r.json());}
 function batch(d){return {document_id:d.document_id,reviews:d.results.map((v,index)=>{const r=v.record;return {index,confirmed:true,draft:{product:r.product_name_raw,ingredients:r.ingredients.map((g,originalIndex)=>({name:g.ingredient_name_raw??'',strength:g.product_strength??'',unit:g.product_strength_unit??'',originalIndex})),dose:r.dose_per_administration??'',doseUnit:r.unit??'',perDay:r.administrations_per_day??'',duration:r.duration_days??'',directions:r.dosage_text_raw??''}};})};}
 const photo=await (await ctx.request.post(root+'/photos/process',{headers,data:{previous:batch(docs[0]),current:batch(docs[1]),normalization_confirmed:true}})).json();assert.equal((await ctx.request.post(root+'/runs/'+photo.run_id+'/save',{headers,data:{}})).status(),200);
 await page.getByRole('button',{name:'저장 목록 새로고침',exact:true}).click();await page.getByRole('button',{name:/^저장 결과 1/}).click();await page.getByRole('region',{name:'저장된 약 정보',exact:true}).waitFor();
 assert.match(await page.getByRole('region',{name:'저장된 약 정보',exact:true}).innerText(),/이전 가상 추출 \/ 현재 가상 추출 · 가상 의약품 매칭/);
 for(const text of [await page.getByRole('button',{name:/^저장 결과 1/}).innerText(),await panel(page).getByRole('button',{name:/^HIRA 저장 결과 1/}).innerText()]){assert.match(text,/\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}/);assert(!text.includes('T'));}
 for(const endpoint of ['/runs','/hira-runs']){const list=await (await ctx.request.get(root+endpoint)).json();assert.match(list.runs[0].created,/T.*(?:Z|\+00:00)$/);}
 pass('photo/HIRA Korean display times and friendly source labels; stored ISO timestamps retained');
 await page.getByLabel('현재 사진',{exact:true}).setInputFiles({name:'synthetic-long-photo-name-for-mobile-layout.png',mimeType:'image/png',buffer:files.photo});
 for(const width of [360,390,412,1280]){
  await page.setViewportSize({width,height:900});
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`horizontal overflow at ${width}`);
  let lastBottom=-Infinity;
  for(const name of ['가족 표시 이름','저장할 가족','현재 사진','현재 기준일','사진 자료 유형']){
   const control=['저장할 가족','사진 자료 유형'].includes(name)?page.getByRole('combobox',{name,exact:true}):page.getByLabel(name,{exact:true});
   const geometry=await control.evaluate(input=>{const label=input.closest('label'),r=input.getBoundingClientRect(),l=label.getBoundingClientRect();const range=document.createRange();range.selectNode(label.firstChild);const t=range.getBoundingClientRect();return {left:r.left,right:r.right,top:r.top,bottom:r.bottom,labelTop:l.top,labelBottom:l.bottom,textBottom:t.bottom};});
   assert(geometry.left>=0&&geometry.right<=width,`clipped ${name} at ${width}`);
   assert(geometry.top>=geometry.textBottom+3,`detached/inline label ${name}`);
   assert(geometry.bottom<=geometry.labelBottom+1&&geometry.labelTop>=lastBottom,`overlapping fields ${name}`);lastBottom=geometry.labelBottom;
  }
  const overlap=await page.evaluate(()=>{const rects=[...document.querySelectorAll('.account-workspace button')].filter(e=>e.getClientRects().length).map(e=>({name:e.textContent,r:e.getBoundingClientRect()}));for(let i=0;i<rects.length;i++)for(let j=i+1;j<rects.length;j++){const a=rects[i].r,b=rects[j].r;if(Math.min(a.right,b.right)-Math.max(a.left,b.left)>1&&Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top)>1)return [rects[i].name,rects[j].name];}return null;});assert.equal(overlap,null,`button overlap at ${width}: ${overlap}`);
 }
 pass('360/390/412/1280 layouts: stacked label/control pairs, no clipping/overflow/button overlap');
 await page.route('**/hira/process',r=>r.fulfill({status:503,contentType:'application/json',body:JSON.stringify({detail:'가상 처리 실패'})}),{times:1});
 await panel(page).getByRole('button',{name:'HIRA 파일 처리',exact:true}).click();await panel(page).getByRole('alert').waitFor();assert.equal(await panel(page).getByText(/HIRA 작업 중/).count(),0);assert(await panel(page).getByRole('button',{name:'HIRA 파일 처리',exact:true}).isEnabled());
 await analyze(page);assert.equal(await panel(page).getByText(/HIRA 작업 중/).count(),0);pass('HIRA failure releases busy; explicit retry succeeds and releases busy');
 let gate=await delayed(page,'**/hira/process');await panel(page).getByRole('button',{name:'HIRA 파일 처리',exact:true}).click();await gate.arrived;await panel(page).getByRole('button',{name:'HIRA 작업 취소',exact:true}).click();await gate.release();assert.equal(await result(page).count(),0);assert.equal(await panel(page).getByText(/HIRA 작업 중/).count(),0);pass('HIRA cancel clears busy and rejects late response');
 await analyze(page);
 await page.clock.install();await page.clock.pauseAt(new Date());
 let posts=0;page.on('request',r=>{if(r.method()==='POST'&&r.url().endsWith('/save'))posts++;});
 gate=await delayed(page,'**/hira-runs/*/save');await result(page).getByRole('button',{name:'이 HIRA 결과 저장 (보류 포함)',exact:true}).click();await gate.arrived;
 await page.clock.fastForward(10001);await panel(page).getByText(/응답이 지연되고 있습니다/).waitFor();
 await page.clock.fastForward(50001);await panel(page).getByRole('alert').waitFor();assert.equal(await panel(page).getByText(/HIRA 작업 중/).count(),0);assert(await result(page).getByRole('button',{name:'이 HIRA 결과 저장 (보류 포함)',exact:true}).isDisabled());await gate.release();
 await panel(page).getByRole('button',{name:'HIRA 저장 완료 여부 확인',exact:true}).click();await result(page).getByRole('heading',{name:'저장된 HIRA 결과',exact:true}).waitFor();assert.equal(posts,1);pass('slow save shows guidance, times out, reconciles via GET without a second POST');
 await analyze(page);gate=await delayed(page,'**/hira-runs/*/save');await result(page).getByRole('button',{name:'이 HIRA 결과 저장 (보류 포함)',exact:true}).click();await gate.arrived;await panel(page).getByRole('button',{name:'HIRA 작업 취소',exact:true}).click();await gate.release();assert.equal(await result(page).count(),0);assert.equal(await panel(page).getByText(/HIRA 작업 중/).count(),0);await panel(page).getByRole('button',{name:'HIRA 저장 완료 여부 확인',exact:true}).click();await result(page).getByRole('heading',{name:'저장된 HIRA 결과',exact:true}).waitFor();assert.equal(posts,2);pass('cancelling a save preserves uncertainty and reconciles the committed result without resend');
 await analyze(page);await page.route('**/hira-runs/*/save',r=>r.abort(),{times:1});await result(page).getByRole('button',{name:'이 HIRA 결과 저장 (보류 포함)',exact:true}).click();await panel(page).getByRole('alert').waitFor();await panel(page).getByRole('button',{name:'HIRA 저장 완료 여부 확인',exact:true}).click();await panel(page).getByText(/아직 저장 완료가 확인되지 않았습니다/).waitFor();assert(await result(page).getByRole('button',{name:'이 HIRA 결과 저장 (보류 포함)',exact:true}).isDisabled());assert.equal(posts,3);pass('unconfirmed save remains blocked after an empty status lookup; no automatic resend');
 assert.deepEqual(errors,[]);assert.deepEqual(external,[]);console.log(JSON.stringify({result:'passed',groups,runtimeErrors:0,externalApiRequests:0}));
})().catch(e=>{console.error(e);process.exitCode=1;}).finally(async()=>{await browser?.close();});
