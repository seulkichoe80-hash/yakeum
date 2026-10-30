// Synthetic transport/files only. Count POSTs to ensure recovery never reprocesses.
const assert=require('node:assert/strict'),fs=require('node:fs');const {execFileSync}=require('node:child_process');
const {chromium}=require(process.env.YAKEUM_PLAYWRIGHT_MODULE||'playwright');
const base=process.env.YAKEUM_TEST_URL||'http://127.0.0.1:4303/';const baseline=process.env.YAKEUM_RECOVERY_BASELINE==='1';
let browser,posts=0,groups=0;const errors=[],external=[];const pass=s=>{groups++;console.log('passed:',s);};
const bytes=execFileSync(process.env.YAKEUM_TEST_PYTHON||'python3',['-c',"from io import BytesIO;import sys,openpyxl;from backend.tests.test_b_d_c_api import _xlsx,_row;r=_row(1,'2026-10-01','가상알파정',None);r[6]='가상알파성분';w=openpyxl.load_workbook(BytesIO(_xlsx([r])));w.active.cell(2,13,'함량');w.active.cell(3,13,'100mg');b=BytesIO();w.save(b);sys.stdout.buffer.write(b.getvalue())"]);
const file={name:'virtual.xlsx',mimeType:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',buffer:bytes};
(async()=>{
 browser=await chromium.launch({headless:true,executablePath:'/usr/bin/chromium'});const ctx=await browser.newContext();
 await ctx.route('**/*',r=>{if(!r.request().url().startsWith(base)){external.push('blocked');return r.abort();}return r.continue();});
 const p=await ctx.newPage();p.on('pageerror',e=>errors.push(e.message));p.on('request',r=>{if(r.method()==='POST'&&r.url().endsWith('/hira/process'))posts++;});p.setDefaultTimeout(10000);
 await p.goto(base);await p.getByRole('button',{name:'개발용 로그인·저장 열기',exact:true}).click();await p.getByLabel('가상 계정 아이디').fill('recover_'+Date.now());await p.getByLabel('비밀번호',{exact:true}).fill('SYNTHETIC-recovery-password');await p.getByRole('button',{name:'가상 계정 가입 후 로그인',exact:true}).click();
 await p.getByLabel('가족 표시 이름').fill('가상 복구 가족');await p.getByRole('button',{name:'내 가족 추가',exact:true}).click();await p.getByRole('heading',{name:'가상 복구 가족 · 사진 연결과 저장'}).waitFor();
 const mode=p.getByRole('checkbox',{name:'실제 식약처 매칭 요청 (별도 승인·서버 활성화 필요)',exact:true});await mode.check();
 const panel=p.getByRole('region',{name:'계정 HIRA 저장',exact:true}),result=panel.getByRole('region',{name:'계정 HIRA 결과',exact:true});
 await panel.getByLabel('이전 HIRA 파일',{exact:true}).setInputFiles(file);await panel.getByLabel('현재 HIRA 파일',{exact:true}).setInputFiles(file);
 await panel.getByRole('button',{name:'HIRA 파일 처리',exact:true}).click();await result.getByRole('heading',{name:'HIRA 처리 결과',exact:true}).waitFor();await result.getByRole('button',{name:'이 HIRA 결과 저장 (보류 포함)',exact:true}).waitFor();pass('successful synthetic live result and save action initially visible');
 await panel.getByRole('button',{name:'HIRA 저장 목록 새로고침',exact:true}).click();await panel.getByText('저장된 HIRA 결과가 없습니다.',{exact:true}).waitFor();
 if(baseline){assert.equal(await result.count(),0);assert.equal(posts,1);console.log(JSON.stringify({baseline:'reproduced: list refresh removes unsaved result and save action',realExternalRequests:0}));return;}
 await result.getByRole('button',{name:'이 HIRA 결과 저장 (보류 포함)',exact:true}).waitFor();assert.equal(posts,1);pass('saved-list refresh preserves current result and save action');
 await mode.uncheck();assert.equal(await result.count(),0);
 await panel.getByRole('button',{name:'저장 전 HIRA 처리 결과 복구',exact:true}).click();await panel.getByRole('button',{name:/^저장 전 HIRA 결과 1/}).click();
 await result.getByRole('heading',{name:'복구한 저장 전 HIRA 결과',exact:true}).waitFor();await result.getByText(/실제 식약처 조회 경로/).waitFor();assert.equal(posts,1);pass('mode remount clears screen but owned draft GET recovers result without another process POST');
 const familyA=await p.getByRole('combobox',{name:'저장할 가족',exact:true}).inputValue();
 let release,seen,done;const gate=new Promise(r=>release=r),arrived=new Promise(r=>seen=r),completed=new Promise(r=>done=r);
 await p.route('**/hira-drafts/*',async route=>{const response=await route.fetch();seen();await gate;try{await route.fulfill({response});}catch{}done();},{times:1});
 await panel.getByRole('button',{name:/^저장 전 HIRA 결과 1/}).click();await arrived;
 await p.getByLabel('가족 표시 이름').fill('가상 다른 복구 가족');await p.getByRole('button',{name:'내 가족 추가',exact:true}).click();await p.getByRole('heading',{name:'가상 다른 복구 가족 · 사진 연결과 저장'}).waitFor();release();await completed;
 assert.equal(await result.count(),0);await p.getByRole('combobox',{name:'저장할 가족',exact:true}).selectOption(familyA);
 await panel.getByRole('button',{name:'저장 전 HIRA 처리 결과 복구',exact:true}).click();await panel.getByRole('button',{name:/^저장 전 HIRA 결과 1/}).click();await result.getByRole('heading',{name:'복구한 저장 전 HIRA 결과',exact:true}).waitFor();assert.equal(posts,1);pass('late recovery response cannot restore another family screen; explicit GET restores original family draft');

 await result.getByRole('button',{name:'이 HIRA 결과 저장 (보류 포함)',exact:true}).click();await result.getByRole('heading',{name:'저장된 HIRA 결과',exact:true}).waitFor();await result.getByText(/실제 복용: 잘 모르겠음/).waitFor();assert.equal(posts,1);pass('recovered result saves without new extraction/matching or automatic intake confirmation');
 await p.reload();await p.getByRole('button',{name:'개발용 로그인·저장 열기',exact:true}).click();await panel.getByRole('button',{name:/^HIRA 저장 결과 1/}).click();await result.getByRole('heading',{name:'저장된 HIRA 결과',exact:true}).waitFor();assert.equal(posts,1);pass('saved result reopens after page reload with original provenance');
 for(const width of [360,390,412,1280]){await p.setViewportSize({width,height:900});assert(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));}
 assert.deepEqual(errors,[]);assert.deepEqual(external,[]);console.log(JSON.stringify({result:'passed',groups,hiraProcessingPosts:posts,realExternalRequests:0,runtimeErrors:0}));
})().catch(e=>{console.error(e);process.exitCode=1;}).finally(async()=>{await browser?.close();});
