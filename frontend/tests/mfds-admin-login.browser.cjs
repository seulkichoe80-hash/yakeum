// Real app/login/session/admin API; synthetic users; no MFDS execution at all.
const assert=require('node:assert/strict');
const {chromium}=require(process.env.YAKEUM_PLAYWRIGHT_MODULE||'playwright');
const base=process.env.YAKEUM_TEST_URL||'http://127.0.0.1:4293/';
const admin='api/dev-account/admin/mfds-probe';
let browser,groups=0;const errors=[],external=[];let executions=0;
function passed(s){groups++;console.log('passed:',s);}
async function workspace(page){await page.goto(base);await page.getByRole('button',{name:'개발용 로그인·저장 열기',exact:true}).click();}
async function register(page,name){await workspace(page);await page.getByLabel('가상 계정 아이디').fill(name);await page.getByLabel('비밀번호',{exact:true}).fill('SYNTHETIC-login-only-password');await page.getByRole('button',{name:'가상 계정 가입 후 로그인',exact:true}).click();await page.getByRole('heading',{name:'내 가족 자료',exact:true}).waitFor();}
(async()=>{
 browser=await chromium.launch({headless:true,executablePath:process.env.YAKEUM_BROWSER_EXECUTABLE||'/usr/bin/chromium'});
 const ctx=await browser.newContext();
 await ctx.route('**/*',r=>{const url=r.request().url();if(!url.startsWith(base)){external.push('blocked');return r.abort();}if(url.includes(admin+'/execute')){executions++;return r.abort();}return r.continue();});
 const page=await ctx.newPage();page.on('pageerror',e=>errors.push(e.message));page.setDefaultTimeout(10000);
 let cookieLogin=false,authLogin=false;
 page.on('request',async request=>{if(request.url()===base+admin+'/status'){const h=await request.allHeaders();cookieLogin=Boolean(h.cookie);authLogin=Boolean(h.authorization);}});
 await register(page,'synthetic_admin');
 const open=page.getByRole('button',{name:'식약처 관리자 검증 열기',exact:true});await open.waitFor();
 assert(cookieLogin);assert.equal(authLogin,false);passed('real app login authenticates administrator requests with cookie, without Authorization header');
 await open.click();const panel=page.getByRole('region',{name:'식약처 관리자 검증 화면',exact:true});
 await panel.getByRole('heading',{name:'식약처 연결 1회 검증'}).waitFor();
 assert.equal(page.url(),base);assert(!(new URL(page.url()).search||new URL(page.url()).hash));
 let value=JSON.parse(await panel.getByLabel('안전한 진단 결과').textContent());assert.equal(value.state,'UNUSED');
 assert(await panel.getByRole('button',{name:'실제 조회 1회 실행',exact:true}).isDisabled());
 await panel.getByRole('button',{name:'저장된 상태 확인 (외부 호출 없음)',exact:true}).click();await panel.getByText('아직 사용하지 않았습니다.',{exact:true}).waitFor();
 passed('in-app admin button opens same-origin authenticated panel without token URLs or external execution');
 for(const width of [360,390,412,1280]){await page.setViewportSize({width,height:900});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));}
 passed('integrated admin view fits mobile and desktop');
 let navigationHeaders;
 page.once('request',async request=>{navigationHeaders=await request.allHeaders();});
 const response=await page.goto(base+admin+'/view');assert.equal(response.status(),200);
 await page.getByRole('heading',{name:'식약처 연결 1회 검증'}).waitFor();
 assert(Boolean(navigationHeaders.cookie));assert(!navigationHeaders.authorization);
 passed('address navigation omits Authorization but valid session cookie still authenticates legacy HTML');
 await workspace(page);await page.getByRole('button',{name:'식약처 관리자 검증 열기',exact:true}).click();
 // Simulate expired session during status reload, using real server logout.
 const me=await (await ctx.request.get(base+'api/dev-account/me')).json();
 await ctx.request.post(base+'api/dev-account/logout',{headers:{Origin:new URL(base).origin,'X-CSRF-Token':me.csrf_token}});
 await page.getByRole('button',{name:'저장된 상태 확인 (외부 호출 없음)',exact:true}).click();
 await page.getByLabel('가상 계정 아이디').waitFor();assert.equal(await page.getByRole('region',{name:'식약처 관리자 검증 화면',exact:true}).count(),0);
 assert.equal((await ctx.request.get(base+admin+'/status')).status(),401);passed('session expiry clears integrated admin content and server rejects reads');
 let releaseOld, arrivedOld, finishedOld;
 const oldArrived=new Promise(r=>arrivedOld=r), oldGate=new Promise(r=>releaseOld=r), oldFinished=new Promise(r=>finishedOld=r);
 await page.route('**/'+admin+'/status',async route=>{const response=await route.fetch();arrivedOld();await oldGate;try{await route.fulfill({response});}catch{}finishedOld();},{times:1});
 await page.getByLabel('가상 계정 아이디').fill('synthetic_admin');await page.getByLabel('비밀번호',{exact:true}).fill('SYNTHETIC-login-only-password');
 await page.getByRole('button',{name:'로그인',exact:true}).click();await oldArrived;
 await page.getByRole('button',{name:'로그아웃',exact:true}).click();await page.getByLabel('가상 계정 아이디').waitFor();
 await register(page,'synthetic_regular');
 releaseOld();await oldFinished;
 assert.equal(await page.getByRole('button',{name:'식약처 관리자 검증 열기',exact:true}).count(),0);
 passed('late administrator status cannot restore UI after logout and another user login');
 assert.equal((await ctx.request.get(base+admin+'/status')).status(),403);
 assert.equal(await page.getByRole('button',{name:'식약처 관리자 검증 열기',exact:true}).count(),0);
 assert.equal((await page.goto(base+admin+'/view')).status(),403);passed('ordinary user has no admin button and cannot bypass server checks');
 assert.equal(executions,0);assert.deepEqual(errors,[]);assert.deepEqual(external,[]);
 console.log(JSON.stringify({result:'passed',groups,adminExecuteRequests:executions,externalBrowserRequests:0,runtimeErrors:0}));
})().catch(e=>{console.error(e);process.exitCode=1;}).finally(async()=>{await browser?.close();});
