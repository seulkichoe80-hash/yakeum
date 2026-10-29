// Synthetic server only. No live external API request.
const assert=require('node:assert/strict');
const {chromium}=require(process.env.YAKEUM_PLAYWRIGHT_MODULE||'playwright');
const base=process.env.YAKEUM_TEST_URL||'http://127.0.0.1:4290/';
const route='api/dev-account/admin/mfds-probe';
const restart=process.env.YAKEUM_MFDS_ADMIN_RESTART==='1';
let browser;const errors=[],external=[];let groups=0;
const passed=s=>{groups++;console.log('passed:',s);};
(async()=>{
 browser=await chromium.launch({headless:true,executablePath:process.env.YAKEUM_BROWSER_EXECUTABLE||'/usr/bin/chromium'});
 const context=await browser.newContext();
 await context.route('**/*',r=>{if(!r.request().url().startsWith(base)){external.push('blocked external');return r.abort();}return r.continue();});
 const page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));page.setDefaultTimeout(10000);
 await page.goto(base);await page.getByRole('button',{name:'개발용 로그인·저장 열기',exact:true}).click();
 await page.getByLabel('가상 계정 아이디').fill('synthetic_admin');await page.getByLabel('비밀번호',{exact:true}).fill('SYNTHETIC-admin-only-pass');
 await page.getByRole('button',{name:restart?'로그인':'가상 계정 가입 후 로그인',exact:true}).click();await page.getByRole('heading',{name:'내 가족 자료',exact:true}).waitFor();
 await page.goto(base+route+'/view');await page.getByText(restart?'실행이 종료되었습니다.':'아직 사용하지 않았습니다.',{exact:false}).waitFor();
 const run=page.getByRole('button',{name:'실제 조회 1회 실행',exact:true});
 if(!restart){
 assert(await run.isDisabled());await page.getByRole('checkbox').check();assert(await run.isEnabled());
 await run.click();await page.getByText('실행 상태와 안전한 결과입니다.',{exact:false}).waitFor();
 }else{assert(await run.isDisabled());}
 let result=JSON.parse(await page.locator('#result').textContent());
 assert.equal(result.state,'FINISHED');assert.equal(result.result.api_success,true);assert.equal(result.result.total_count,7);assert.equal(result.result.received_count,3);
 assert.equal(result.result.unique_candidate_evidence,false);assert(await run.isDisabled());passed(restart?'server restart retains durable result and blocks another execution':'admin consent runs synthetic probe and displays safe partial-page summary');
 await page.reload();await page.getByText('실행이 종료되었습니다.',{exact:false}).waitFor();
 await page.getByRole('checkbox').check();assert(await page.getByRole('button',{name:'실제 조회 1회 실행',exact:true}).isDisabled());
 await page.getByRole('button',{name:'저장된 상태 확인 (외부 호출 없음)',exact:true}).click();await page.getByText('실행이 종료되었습니다.',{exact:false}).waitFor();
 assert(!((await page.locator('#result').textContent()).includes('SYNTHETIC-SECRET')));passed('reload and status queries never enable another execution');
 for(const width of [360,390,412,1280]){await page.setViewportSize({width,height:900});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));}
 passed('admin view has no horizontal overflow at mobile and desktop widths');
 const me=await (await context.request.get(base+'api/dev-account/me')).json();
 await context.request.post(base+'api/dev-account/logout',{headers:{Origin:new URL(base).origin,'X-CSRF-Token':me.csrf_token}});
 assert.equal((await page.goto(base+route+'/view')).status(),401);assert.equal((await context.request.get(base+route+'/status')).status(),401);
 passed('logged-out browser cannot read diagnostic page or stored result');
 assert.deepEqual(errors,[]);assert.deepEqual(external,[]);
 console.log(JSON.stringify({result:'passed',groups,runtimeErrors:0,externalBrowserRequests:0,transport:'synthetic only'}));
})().catch(e=>{console.error(e);process.exitCode=1;}).finally(async()=>{await browser?.close();});
