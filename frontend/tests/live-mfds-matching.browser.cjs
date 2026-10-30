// Synthetic fake HTTP only. Production services/keys are never used.
const assert=require('node:assert/strict'),fs=require('node:fs');const {execFileSync}=require('node:child_process');
const {chromium}=require(process.env.YAKEUM_PLAYWRIGHT_MODULE||'playwright');
const base=process.env.YAKEUM_TEST_URL||'http://127.0.0.1:4296/';
const scenario=process.env.YAKEUM_MFDS_TEST_CASE,counter=process.env.YAKEUM_MFDS_TEST_COUNTER;
if(!scenario?.startsWith('/tmp/')||!counter?.startsWith('/tmp/'))throw Error('Synthetic test files required');
const data=JSON.parse(execFileSync(process.env.YAKEUM_TEST_PYTHON||'python3',['-c',"import json,base64;from io import BytesIO;import openpyxl;from backend.tests.test_b_d_c_api import _xlsx,_row;from backend.tests.test_photo_upload import image;r=_row(1,'2026-10-01','가상알파정',None);r[6]='가상알파성분';w=openpyxl.load_workbook(BytesIO(_xlsx([r])));w.active.cell(2,13,'함량');w.active.cell(3,13,'100mg');b=BytesIO();w.save(b);print(json.dumps({'photo':base64.b64encode(image()).decode(),'hira':base64.b64encode(b.getvalue()).decode()}))"],{encoding:'utf8'}));
const photo={name:'virtual.png',mimeType:'image/png',buffer:Buffer.from(data.photo,'base64')};
const hira={name:'virtual.xlsx',mimeType:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',buffer:Buffer.from(data.hira,'base64')};
let browser,groups=0;const errors=[],external=[];const pass=s=>{groups++;console.log('passed:',s);};
(async()=>{
 browser=await chromium.launch({headless:true,executablePath:'/usr/bin/chromium'});const ctx=await browser.newContext();
 await ctx.route('**/*',r=>{if(!r.request().url().startsWith(base)){external.push('blocked');return r.abort();}return r.continue();});
 const p=await ctx.newPage();p.setDefaultTimeout(12000);p.on('pageerror',e=>errors.push(e.message));
 await p.goto(base);await p.getByRole('button',{name:'개발용 로그인·저장 열기',exact:true}).click();
 await p.getByLabel('가상 계정 아이디').fill('live_'+Date.now());await p.getByLabel('비밀번호',{exact:true}).fill('SYNTHETIC-browser-password');await p.getByRole('button',{name:'가상 계정 가입 후 로그인',exact:true}).click();
 await p.getByLabel('가족 표시 이름').fill('가상 가족');await p.getByRole('button',{name:'내 가족 추가',exact:true}).click();await p.getByRole('heading',{name:'가상 가족 · 사진 연결과 저장'}).waitFor();
 const mode=p.getByRole('checkbox',{name:'실제 식약처 매칭 요청 (별도 승인·서버 활성화 필요)',exact:true});await mode.check();
 fs.writeFileSync(scenario,'normal');await p.getByLabel('현재 사진',{exact:true}).setInputFiles(photo);
 const flow=p.getByRole('region',{name:'사진 업로드 전체 연결',exact:true});await flow.getByLabel('이전 사진 선택').setInputFiles(photo);
 for(const side of ['이전','현재']){const region=flow.getByRole('region',{name:side+' 사진 후보',exact:true});await region.getByRole('button',{name:'사진 업로드 후 가짜 후보 보기',exact:true}).click();await region.getByRole('form').waitFor();await region.getByRole('checkbox').check();await region.getByRole('button',{name:'추출 내용 확인 완료 (로컬)',exact:true}).click();}
 await flow.getByRole('button',{name:'수정 후보 B 정규화 미리보기',exact:true}).click();await flow.getByRole('button',{name:'정규화 결과 확인 후 D 비교',exact:true}).click();await flow.getByRole('heading',{name:'사진 처리 결과 · 비교 완료',exact:true}).waitFor();
 await flow.getByRole('button',{name:'확인한 결과와 복용 선택 저장',exact:true}).click();await flow.getByText('개발용 DB에 저장했습니다.',{exact:false}).waitFor();
 await p.getByRole('button',{name:'저장 목록 새로고침',exact:true}).click();await p.getByRole('button',{name:/^저장 결과 1/}).click();
 await p.getByRole('region',{name:'저장된 약 정보',exact:true}).getByText(/실제 식약처 조회 경로/).waitFor();pass('photo fake extraction -> confirmed candidates -> strict XML matching -> comparison -> stored live provenance');
 const hp=p.getByRole('region',{name:'계정 HIRA 저장',exact:true});
 async function upload(){await hp.getByLabel('이전 HIRA 파일',{exact:true}).setInputFiles(hira);await hp.getByLabel('현재 HIRA 파일',{exact:true}).setInputFiles(hira);}
 async function process(){await hp.getByRole('button',{name:'HIRA 파일 처리',exact:true}).click();await hp.getByRole('region',{name:'계정 HIRA 결과',exact:true}).waitFor();}
 fs.writeFileSync(scenario,'partial');await upload();await process();const hr=hp.getByRole('region',{name:'계정 HIRA 결과',exact:true});await hr.getByText('! 추가 확인 필요',{exact:true}).waitFor();
 await hr.getByText(/실제 식약처 조회 경로/).waitFor();await hr.getByRole('button',{name:'이 HIRA 결과 저장 (보류 포함)',exact:true}).click();await hr.getByRole('heading',{name:'저장된 HIRA 결과',exact:true}).waitFor();
 await hr.getByText(/실제 식약처 조회 경로/).waitFor();pass('HIRA partial response remains held with source provenance through save and reload');
 fs.writeFileSync(scenario,'error');await process();await hp.getByRole('region',{name:'계정 HIRA 결과',exact:true}).getByText('! 추가 확인 필요',{exact:true}).waitFor();
 assert.equal(await hp.getByRole('article').count(),0);pass('official timeout remains held instead of mock success or stale comparison');
 const before=Number(fs.readFileSync(counter,'utf8'));await mode.uncheck();await upload();await process();
 await hp.getByRole('region',{name:'계정 HIRA 결과',exact:true}).getByText('가상 의약품 매칭',{exact:true}).waitFor();
 assert.equal(Number(fs.readFileSync(counter,'utf8')),before);pass('switching to legacy mock clears old result and makes no official request');
 await hp.getByRole('button',{name:'HIRA 저장 목록 새로고침',exact:true}).click();await hp.getByRole('button',{name:/^HIRA 저장 결과 1/}).click();await hp.getByRole('region',{name:'계정 HIRA 결과',exact:true}).getByText(/실제 식약처 조회 경로/).waitFor();assert.equal(Number(fs.readFileSync(counter,'utf8')),before);pass('saved live result retains its own provenance while current mode is mock');
 for(const width of [360,390,412,1280]){await p.setViewportSize({width,height:900});assert(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));}
 assert.deepEqual(errors,[]);assert.deepEqual(external,[]);console.log(JSON.stringify({result:'passed',groups,realExternalRequests:0,runtimeErrors:0}));
})().catch(e=>{console.error(e);process.exitCode=1;}).finally(async()=>{await browser?.close();});
