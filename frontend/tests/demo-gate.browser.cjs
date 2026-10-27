// Loopback-only password-entrance smoke; does not claim a real HTTPS deployment.
const assert=require('node:assert/strict');
const {chromium}=require(process.env.YAKEUM_PLAYWRIGHT_MODULE||'playwright');
const base=process.env.YAKEUM_TEST_URL;
assert(base&&['127.0.0.1','localhost'].includes(new URL(base).hostname),'This synthetic gate test is loopback only');
const username='synthetic-gate',password='SYNTHETIC-only-gate-pass-123';
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.env.YAKEUM_BROWSER_EXECUTABLE||'/usr/bin/chromium'});
 try{
  const anonymous=await browser.newContext();
  for(const path of ['','docs','openapi.json','api/dev-account/families']){
   const r=await anonymous.request.get(base+path);assert.equal(r.status(),401);assert.equal(r.headers()['cache-control'],'no-store');
  }
  assert.equal((await anonymous.request.get(base+'api/health')).status(),200);
  await anonymous.close();
  const wrong=await browser.newContext({httpCredentials:{username,password:'wrong'}});
  assert.equal((await wrong.request.get(base)).status(),401);await wrong.close();
  const approved=await browser.newContext({httpCredentials:{username,password}});
  const page=await approved.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await approved.route('**/*',r=>r.request().url().startsWith(base)?r.continue():r.abort());
  await page.goto(base);await page.getByRole('note',{name:'가상 시연 안내'}).waitFor();
  await page.getByRole('button',{name:'개발용 로그인·저장 열기',exact:true}).click();
  await page.getByLabel('가상 계정 아이디').waitFor();
  // Entrance access alone does not grant a logged-in app session.
  assert.equal((await approved.request.get(base+'api/dev-account/me')).status(),401);
  assert.deepEqual(errors,[]);await approved.close();
  console.log(JSON.stringify({result:'passed',unauthorizedUIAndAPIBlocked:true,wrongPasswordBlocked:true,authorizedUI:true,appLoginStillRequired:true,realHTTPSVerified:false,externalApiRequests:0}));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1});
