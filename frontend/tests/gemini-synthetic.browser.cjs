// Local fake SDK only; never point this runner at Render.
const assert=require('node:assert/strict'),fs=require('node:fs');
const {chromium}=require(process.env.YAKEUM_PLAYWRIGHT_MODULE||'playwright');
const base=process.env.YAKEUM_TEST_URL;
if(!/^http:\/\/127\.0\.0\.1:\d+\/$/.test(base||''))throw Error('Loopback fake server required');
const file=require('node:path').resolve(__dirname,'../../docs/integration/samples/render-gemini/synthetic-bag.png');
(async()=>{const browser=await chromium.launch({headless:true,executablePath:process.env.YAKEUM_BROWSER_EXECUTABLE});try{
 const context=await browser.newContext();const errors=[];
 await context.route('**/*',r=>r.request().url().startsWith(base)||r.request().url().startsWith('blob:')?r.continue():r.abort());
 const p=await context.newPage();p.on('pageerror',e=>errors.push(e.message));
 await p.goto(base);await p.getByRole('button',{name:'개발용 로그인·저장 열기',exact:true}).click();
 await p.getByLabel('가상 계정 아이디').fill('synthetic_admin');await p.getByLabel('비밀번호',{exact:true}).fill('SYNTHETIC-browser-pass-123');
 await p.getByRole('button',{name:'가상 계정 가입 후 로그인',exact:true}).click();await p.getByLabel('가족 표시 이름').fill('합성 검증 가족');await p.getByRole('button',{name:'내 가족 추가',exact:true}).click();
 await p.getByLabel('현재 사진',{exact:true}).setInputFiles(file);
 const f=p.getByRole('region',{name:'사진 업로드 전체 연결',exact:true});await f.getByLabel('이전 사진 선택').setInputFiles(file);await f.getByLabel('사진 추출 방식').selectOption('GEMINI');
 await f.getByLabel(/관리자 합성 검증:/).check();
 let posts=0;p.on('request',r=>{if(r.url().endsWith('/photos/gemini-extract'))posts++});
 for(const side of ['이전','현재']){const s=f.getByRole('region',{name:`${side} 사진 후보`,exact:true});await s.getByRole('button',{name:'Gemini로 사진 추출 요청',exact:true}).click();await s.getByRole('form').waitFor();await s.getByRole('checkbox').check();await s.getByRole('button',{name:'추출 내용 확인 완료',exact:true}).click();}
 assert.equal(posts,2);
 await f.getByRole('button',{name:'확인한 내용으로 의약품 정보 검토',exact:true}).click();await f.getByRole('button',{name:'의약품 정보 확인 후 비교하기',exact:true}).click();await f.getByRole('heading',{name:'사진 처리 결과 · 비교 완료',exact:true}).waitFor();
 assert.match(await f.innerText(),/이전 Gemini 추출 \/ 현재 Gemini 추출/);assert.match(await f.innerText(),/가상 의약품 매칭/);
 await f.getByRole('button',{name:'확인한 결과와 복용 선택 저장',exact:true}).click();await f.getByText('개발용 DB에 저장했습니다.',{exact:false}).waitFor();
 await f.getByRole('button',{name:'저장한 결과 보기',exact:true}).click();await p.getByRole('button',{name:'저장 목록 새로고침',exact:true}).click();await p.getByRole('button',{name:/^저장 결과 1/}).click();await p.getByRole('region',{name:'저장된 약 정보',exact:true}).waitFor();assert.equal(posts,2);
 // Re-entry with the same approved fixture must hit the durable slot, not the SDK.
 await p.getByRole('tab',{name:'사진으로 비교',exact:true}).click();await f.getByLabel('이전 사진 선택').setInputFiles({name:'synthetic-again.png',mimeType:'image/png',buffer:fs.readFileSync(file)});assert(await f.getByRole('region',{name:'이전 사진 후보',exact:true}).getByRole('button',{name:'Gemini로 사진 추출 요청',exact:true}).isDisabled());
 for(const width of [360,390,412,1280]){await p.setViewportSize({width,height:900});assert(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));}
 assert.deepEqual(errors,[]);assert.equal(fs.readFileSync(process.env.YAKEUM_GEMINI_FAKE_SCENARIO.replace(/\.[^.]*$/,'')+'.calls','utf8').trim().split('\n').length,2);
 console.log('PASS: synthetic consent -> two fake SDK calls -> review/compare/save/reload -> consumed-slot UI guard (durable rejection covered by backend tests); mobile widths and provenance preserved; external calls 0');
}finally{await browser.close()}})().catch(e=>{console.error(e);process.exitCode=1});
