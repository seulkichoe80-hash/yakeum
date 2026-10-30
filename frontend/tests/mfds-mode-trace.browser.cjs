// Trace real browser state/request/backend with fake users/files; live provider disabled.
const assert=require('node:assert/strict');const {execFileSync}=require('node:child_process');
const {chromium}=require(process.env.YAKEUM_PLAYWRIGHT_MODULE||'playwright');
const base=process.env.YAKEUM_TEST_URL||'http://127.0.0.1:4301/';let browser,groups=0;
const errors=[],external=[],modes=[];const pass=s=>{groups++;console.log('passed:',s);};
const bytes=execFileSync(process.env.YAKEUM_TEST_PYTHON||'python3',['-c',"import sys;from backend.tests.test_b_d_c_api import _xlsx;from backend.tests.test_hira_hold_v2 import known;sys.stdout.buffer.write(_xlsx([known()]))"]);
const file={name:'virtual.xlsx',mimeType:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',buffer:bytes};
(async()=>{
 browser=await chromium.launch({headless:true,executablePath:'/usr/bin/chromium'});const ctx=await browser.newContext();
 await ctx.route('**/*',r=>{if(!r.request().url().startsWith(base)){external.push('blocked');return r.abort();}return r.continue();});
 const page=await ctx.newPage();page.setDefaultTimeout(10000);page.on('pageerror',e=>errors.push(e.message));
 page.on('request',req=>{if(req.method()==='POST'&&req.url().endsWith('/hira/process')){const match=/name="official_mode"\r\n\r\n([^\r]+)/.exec(req.postDataBuffer().toString('latin1'));modes.push(match?.[1]||'MISSING');}});
 async function open(){await page.goto(base);await page.getByRole('button',{name:'개발용 로그인·저장 열기',exact:true}).click();}
 await open();await page.getByLabel('가상 계정 아이디').fill('mode_'+Date.now());await page.getByLabel('비밀번호',{exact:true}).fill('SYNTHETIC-mode-password');await page.getByRole('button',{name:'가상 계정 가입 후 로그인',exact:true}).click();
 async function add(name){await page.getByLabel('가족 표시 이름').fill(name);await page.getByRole('button',{name:'내 가족 추가',exact:true}).click();await page.getByRole('heading',{name:name+' · 사진 연결과 저장'}).waitFor();return page.getByRole('combobox',{name:'저장할 가족',exact:true}).inputValue();}
 const a=await add('가상 모드 A');const hp=page.getByRole('region',{name:'계정 HIRA 저장',exact:true});
 const mode=page.getByRole('checkbox',{name:'실제 식약처 매칭 요청 (별도 승인·서버 활성화 필요)',exact:true});
 async function upload(){await hp.getByLabel('이전 HIRA 파일',{exact:true}).setInputFiles(file);await hp.getByLabel('현재 HIRA 파일',{exact:true}).setInputFiles(file);}
 assert(!(await mode.isChecked()));await upload();
 const mockResponse=page.waitForResponse(r=>r.request().method()==='POST'&&r.url().endsWith('/hira/process'));
 await hp.getByRole('button',{name:'HIRA 파일 처리',exact:true}).click();const original=await (await mockResponse).json();
 assert.equal(original.result.processing.official_data_mode,'LOCAL_MOCK');assert.equal(original.result.response_version,'TASK_D_HIRA_V2');
 assert.equal(original.result.accepted_results.current[0].record.mfds_product_id,'OFFICIAL-0001');
 await hp.getByRole('button',{name:'이 HIRA 결과 저장 (보류 포함)',exact:true}).click();await hp.getByRole('heading',{name:'저장된 HIRA 결과',exact:true}).waitFor();
 pass('unchecked state sends LOCAL_MOCK and backend returns exact mock indicators including OFFICIAL-0001');
 await mode.check();assert(await mode.isChecked());assert.equal(await hp.getByRole('region',{name:'계정 HIRA 결과',exact:true}).count(),0);
 await upload();assert(await mode.isChecked());await hp.getByLabel('현재 HIRA 파일',{exact:true}).setInputFiles([]);assert(await mode.isChecked());await hp.getByLabel('현재 HIRA 파일',{exact:true}).setInputFiles(file);assert(await mode.isChecked());
 const disabled=page.waitForResponse(r=>r.request().method()==='POST'&&r.url().endsWith('/hira/process'));
 await hp.getByRole('button',{name:'HIRA 파일 처리',exact:true}).click();assert.equal((await disabled).status(),503);await hp.getByRole('alert').waitFor();
 assert.equal(modes.at(-1),'MFDS_LIVE');assert.equal(await hp.getByRole('region',{name:'계정 HIRA 결과',exact:true}).count(),0);
 pass('file selection/clear does not lose checked mode; MFDS_LIVE reaches disabled server branch without mock fallback');
 await page.route('**/hira/process',r=>r.fulfill({status:200,contentType:'application/json',body:JSON.stringify(original)}),{times:1});
 await hp.getByRole('button',{name:'HIRA 파일 처리',exact:true}).click();await hp.getByText('요청한 의약품 매칭 출처와 응답이 다릅니다.',{exact:true}).waitFor();
 assert.equal(modes.at(-1),'MFDS_LIVE');assert.equal(await hp.getByRole('region',{name:'계정 HIRA 결과',exact:true}).count(),0);
 pass('injected mock response to live processing is rejected and no success result displayed');
 const b=await add('가상 모드 B');assert(await mode.isChecked());await page.getByRole('combobox',{name:'저장할 가족',exact:true}).selectOption(a);assert(await mode.isChecked());
 await upload();const familyResponse=page.waitForResponse(r=>r.request().method()==='POST'&&r.url().endsWith('/hira/process'));await hp.getByRole('button',{name:'HIRA 파일 처리',exact:true}).click();assert.equal((await familyResponse).status(),503);assert.equal(modes.at(-1),'MFDS_LIVE');
 pass('family add and A-B-A reconstruction preserve selected live mode and request field');
 await hp.getByRole('button',{name:'HIRA 저장 목록 새로고침',exact:true}).click();await hp.getByRole('button',{name:/^HIRA 저장 결과 1/}).click();await hp.getByRole('heading',{name:'저장된 HIRA 결과',exact:true}).waitFor();
 assert(await mode.isChecked());await hp.getByRole('region',{name:'계정 HIRA 결과',exact:true}).getByText('가상 의약품 매칭',{exact:true}).waitFor();
 await hp.getByRole('note',{name:'이전 저장 결과 안내',exact:true}).waitFor();for(const width of [360,390,412,1280]){await page.setViewportSize({width,height:900});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));}pass('old saved mock result stays readable with an explicit history-versus-current-selection notice');
 await page.getByRole('button',{name:'가상 시연 화면으로 돌아가기',exact:true}).click();await page.getByRole('button',{name:'개발용 로그인·저장 열기',exact:true}).click();await page.getByRole('heading',{name:'내 가족 자료',exact:true}).waitFor();
 assert(!(await mode.isChecked()));await upload();
 const again=page.waitForResponse(r=>r.request().method()==='POST'&&r.url().endsWith('/hira/process'));
 await hp.getByRole('button',{name:'HIRA 파일 처리',exact:true}).click();const body=await (await again).json();assert.equal(modes.at(-1),'LOCAL_MOCK');assert.equal(body.result.processing.official_data_mode,'LOCAL_MOCK');
 pass('whole login workspace re-entry resets selection to visibly unchecked default mock and sends LOCAL_MOCK');
 await page.reload();await page.getByRole('button',{name:'개발용 로그인·저장 열기',exact:true}).click();await page.getByRole('heading',{name:'내 가족 자료',exact:true}).waitFor();assert(!(await mode.isChecked()));pass('full page reload returns to visible default mock without processing');
 assert.deepEqual(errors,[]);assert.deepEqual(external,[]);assert.deepEqual(modes,['LOCAL_MOCK','MFDS_LIVE','MFDS_LIVE','MFDS_LIVE','LOCAL_MOCK']);
 console.log(JSON.stringify({result:'passed',groups,requestModes:modes,realExternalRequests:0,runtimeErrors:0}));
})().catch(e=>{console.error(e);process.exitCode=1;}).finally(async()=>{await browser?.close();});
