// Optional local browser checks. Set YAKEUM_PLAYWRIGHT_MODULE to a supplied
// Playwright package, or install Playwright in the development environment.
const assert = require('node:assert/strict');
const path = require('node:path');
const {chromium} = require(process.env.YAKEUM_PLAYWRIGHT_MODULE || 'playwright');
const base = process.env.YAKEUM_TEST_URL || 'http://127.0.0.1:4190/';
const output = process.env.YAKEUM_SCREENSHOT_DIR;
(async()=>{
 const browser = await chromium.launch({
  ...(process.env.YAKEUM_BROWSER_EXECUTABLE
   ? {executablePath:process.env.YAKEUM_BROWSER_EXECUTABLE}
   : {channel:process.env.YAKEUM_BROWSER_CHANNEL || 'msedge'}),
  headless:true,
 });
 try {
  const page = await browser.newPage({viewport:{width:390,height:844}});
  const apiRequests=[]; const runtimeErrors=[];
  page.on('request',r=>{if(new URL(r.url()).pathname.startsWith('/api/')) apiRequests.push(r.url());});
  page.on('pageerror',e=>runtimeErrors.push(e.message));
  await page.goto(base);
  assert.equal(await page.getByRole('heading',{name:'우리 가족 복용정보',exact:true}).count(),1);
  await page.getByRole('button',{name:/↥.*자료 등록/}).click();
  await page.getByRole('combobox',{name:'자료 유형',exact:true}).selectOption('약봉투 사진');
  const panel=page.locator('.image-review');
  const scenario=panel.getByRole('combobox');
  const start=panel.getByRole('button',{name:'가상 추출 결과 보기',exact:true});
  await scenario.selectOption('multiple');await start.click();
  await panel.getByRole('heading',{name:'약품 후보 2개 · 화면 확인 완료 0개',exact:true}).waitFor();
  const first=panel.getByRole('form',{name:'약품 후보 1',exact:true});
  const second=panel.getByRole('form',{name:'약품 후보 2',exact:true});
  await first.getByRole('button',{name:'추출 내용 확인 완료 (로컬)',exact:true}).click();
  assert.match(await first.innerText(),/표시된 입력 오류/);
  await first.getByRole('checkbox').check();
  await first.getByRole('button',{name:'추출 내용 확인 완료 (로컬)',exact:true}).click();
  assert.match(await first.locator('.confirmation-state').innerText(),/로컬 user_confirmed=true/);
  assert.match(await second.locator('.confirmation-state').innerText(),/user_confirmed=false/);
  await first.getByRole('textbox',{name:'제품명',exact:true}).fill('가상 사용자 수정 제품');
  assert.match(await first.locator('.confirmation-state').innerText(),/user_confirmed=false/);
  assert.equal(await first.getByRole('checkbox').isChecked(),false);
  assert.match(await first.innerText(),/AI 추출값: 가상 추출 제품 1 · 사용자 수정/);
  await first.getByRole('button',{name:'AI 추출값으로 되돌리기',exact:true}).click();
  assert.equal(await first.getByRole('textbox',{name:'제품명',exact:true}).inputValue(),'가상 추출 제품 1');
  await second.getByRole('button',{name:'성분 1 삭제',exact:true}).click();
  assert.match(await second.locator('.ingredient-editor').innerText(),/AI 추출값: 가상 복합 성분 B/);
  const layouts=[];
  for(const width of [360,390,768,1280]) {
   await page.setViewportSize({width,height:844});
   const sizes=await page.evaluate(()=>({client:document.documentElement.clientWidth,scroll:document.documentElement.scrollWidth}));
   assert.ok(sizes.scroll<=sizes.client+1,`${width}px horizontal overflow`);
   layouts.push({width,...sizes});
  }
  await page.setViewportSize({width:390,height:844});
  await first.getByRole('textbox',{name:'제품명',exact:true}).focus();await page.keyboard.press('Tab');
  assert.equal(await page.locator(':focus').getAttribute('aria-invalid'),'false');
  if(output){await first.scrollIntoViewIfNeeded();await page.screenshot({path:path.join(output,'C_image_review_mobile_20261019.png')});}
  await scenario.selectOption('missing');await start.click();
  await panel.getByRole('heading',{name:'약품 후보 2개 · 화면 확인 완료 0개',exact:true}).waitFor();
  assert.equal(await first.getByRole('textbox',{name:'제품명',exact:true}).inputValue(),'');
  assert.match(await first.innerText(),/원본 record가 없는 후보/);
  await first.getByRole('button',{name:'확인 보류',exact:true}).click();
  assert.match(await first.locator('.confirmation-state').innerText(),/확인 보류.*false/);
  await first.getByRole('textbox',{name:'제품명',exact:true}).fill('가상 보완 제품');
  await first.getByRole('textbox',{name:'하루 투여 횟수',exact:true}).fill('1e309');
  await first.getByRole('checkbox').check();
  await first.getByRole('button',{name:'추출 내용 확인 완료 (로컬)',exact:true}).click();
  assert.match(await first.locator('.confirmation-state').innerText(),/user_confirmed=false/);
  await first.getByRole('textbox',{name:'하루 투여 횟수',exact:true}).fill('0');
  await first.getByRole('checkbox').check();
  await first.getByRole('button',{name:'추출 내용 확인 완료 (로컬)',exact:true}).click();
  assert.match(await first.locator('.confirmation-state').innerText(),/로컬 user_confirmed=true/);
  await scenario.selectOption('failed');await start.click();
  await panel.getByRole('heading',{name:'가상 이미지 분석에 실패했습니다',exact:true}).waitFor();
  assert.equal(await panel.getByRole('form').count(),0);
  await panel.getByRole('button',{name:'같은 사례 재시도',exact:true}).click();
  await panel.getByRole('heading',{name:'가상 이미지 분석에 실패했습니다',exact:true}).waitFor();
  if(output){await panel.locator('.image-error').scrollIntoViewIfNeeded();await page.screenshot({path:path.join(output,'C_image_review_failure_20261019.png')});}
  await scenario.selectOption('single');await start.click();
  await panel.getByRole('heading',{name:'약품 후보 1개 · 화면 확인 완료 0개',exact:true}).waitFor();
  await scenario.selectOption('multiple');await start.click();
  await page.getByRole('combobox',{name:'가족 구성원',exact:true}).selectOption('00000000-0000-4000-8000-000000000002');
  await page.getByRole('heading',{name:/^(화면 시연용 )?동의와 승인이 필요해요$/}).waitFor();
  await page.getByRole('combobox',{name:'가족 구성원',exact:true}).selectOption('00000000-0000-4000-8000-000000000001');
  await start.waitFor();
  await page.waitForTimeout(750); // deliberately wait beyond the discarded Mock response
  assert.equal(await panel.getByRole('form').count(),0,'stale result must not return after switching family');
  assert.equal(await scenario.inputValue(),'single');
  await start.click();
  await panel.getByRole('button',{name:'가상 분석 취소',exact:true}).click();
  await page.waitForTimeout(750);
  assert.equal(await panel.getByRole('form').count(),0,'cancel must discard pending result');
  await start.click();
  await panel.getByRole('heading',{name:'약품 후보 1개 · 화면 확인 완료 0개',exact:true}).waitFor();
  await page.locator('input[type=date]').fill('2026-10-18');
  assert.equal(await panel.getByRole('form').count(),0,'date change must discard old drafts');
  await start.click();
  await panel.getByRole('heading',{name:'약품 후보 1개 · 화면 확인 완료 0개',exact:true}).waitFor();
  await page.getByRole('combobox',{name:'자료 유형',exact:true}).selectOption('처방전 사진');
  assert.equal(await panel.getByRole('form').count(),0,'source change must discard old drafts');
  assert.deepEqual(apiRequests,[],'image review must never call an API');
  assert.deepEqual(runtimeErrors,[]);
  console.log(JSON.stringify({result:'passed',layouts,scenarios:4,apiRequests:0,runtimeErrors:0,familyReset:'passed',keyboard:'passed'}));
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
