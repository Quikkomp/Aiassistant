// Real exam UI and isolated SQLite: pending/error notices must not move the viewport.
const {spawn}=require('node:child_process');
const path=require('node:path');
const fs=require('node:fs');
const assert=require('node:assert/strict');
const {chromium}=require('C:/Users/10657/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const root=path.resolve(__dirname,'..');
const out=path.join(root,'output/ui-review');fs.mkdirSync(out,{recursive:true});
const fixture=spawn('C:/Users/10657/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe',[path.join(__dirname,'exam_fixture.py')],{cwd:root,windowsHide:true});
let logs='';fixture.stderr.on('data',chunk=>logs+=chunk);
const ready=new Promise((resolve,reject)=>{
  let raw='';fixture.stdout.on('data',chunk=>{raw+=chunk;try{resolve(JSON.parse(raw.split('\n')[0]).port);}catch(_){}});
  fixture.on('exit',code=>reject(new Error('Fixture exited '+code+' '+logs)));
  setTimeout(()=>reject(new Error('Fixture readiness timed out '+logs)),15000).unref();
});
const position=page=>page.evaluate(()=>({x:scrollX,y:scrollY}));
const stable=async(page,before,label)=>{
  const after=await position(page);
  assert.ok(Math.abs(after.y-before.y)<=2,`${label}: scrollY changed ${before.y} -> ${after.y}`);
};
const settle=page=>page.waitForFunction(()=>document.getAnimations().every(a=>a.playState==='finished'));
(async()=>{
  const port=await ready,base='http://127.0.0.1:'+port;
  let browser;try{browser=await chromium.launch({headless:true});}catch(_){browser=await chromium.launch({headless:true,channel:'msedge'});}
  try{
    const context=await browser.newContext({viewport:{width:1440,height:650}});
    await context.request.post(base+'/api/auth/login',{data:{username:'Teacher',password:'mock-password'}});
    const banks=(await (await context.request.get(base+'/api/question_sets')).json()).banks;
    for(let i=0;i<12;i++){
      const exam=(await (await context.request.post(base+'/api/exams',{data:{bank_id:banks[0].id}})).json()).exam;
      const questions=exam.questions.map(q=>({...q,answer:'0°C',explanation:'冰点为零摄氏度。',rubric:'答出零摄氏度得满分。',knowledge:'冰点'}));
      const saved=(await (await context.request.put(base+`/api/exams/${exam.id}`,{data:{...exam,title:`滚动测试 ${i+1}`,questions}})).json()).exam;
      const published=await context.request.post(base+`/api/exams/${exam.id}/publish`,{data:{version:saved.version,reviewed:true}});
      assert.equal(published.status(),200);
    }
    const page=await context.newPage(),errors=[];
    page.on('pageerror',error=>errors.push(error.message));
    await page.goto(base);await page.locator('#nav-exams').click();
    await page.getByRole('tab',{name:'草稿与已发布'}).click();
    assert.equal(await page.locator('.exam-owned-row').count(),12);
    for(const viewport of [{width:1440,height:650},{width:390,height:844}]){
      await page.setViewportSize(viewport);
      const targetIndex=viewport.width>640?7:4;
      const row=page.locator('.exam-owned-row').nth(targetIndex),toggle=row.locator('.exam-expand');
      await toggle.scrollIntoViewIfNeeded();await settle(page);
      let release;
      const pending=new Promise(resolve=>release=resolve);
      const delay=async route=>{await pending;await route.continue();};
      await page.route('**/api/exams/*/analytics',delay);
      const before=await position(page);assert.ok(before.y>200);
      const rowTop=await row.evaluate(el=>el.getBoundingClientRect().top);
      await toggle.click();await page.locator('#exam-message').filter({hasText:'正在处理'}).waitFor();
      await stable(page,before,'pending expand');
      assert.ok(Math.abs((await row.evaluate(el=>el.getBoundingClientRect().top))-rowTop)<=2,'notice must not push the row');
      assert.ok(await page.locator('#exam-message').evaluate(el=>{
        const rect=el.getBoundingClientRect();return rect.top>=0&&rect.bottom<=innerHeight&&rect.left>=0&&rect.right<=innerWidth;
      }),'pending notice must remain in the viewport at the scrolled position');
      await page.screenshot({path:path.join(out,`exam-scroll-pending-${viewport.width>640?'desktop':'mobile'}.png`)});
      release();await row.locator('.exam-roster-panel').waitFor({state:'visible'});
      await page.locator('#exam-message').waitFor({state:'hidden'});await settle(page);
      await stable(page,before,'completed expand');
      await page.unroute('**/api/exams/*/analytics',delay);
      await toggle.click();await row.locator('.exam-roster-panel').waitFor({state:'hidden'});await settle(page);
      await stable(page,before,'collapse');
      const failingRow=page.locator('.exam-owned-row').nth(targetIndex+1);
      await failingRow.locator('.exam-expand').scrollIntoViewIfNeeded();
      const failBefore=await position(page);
      const fail=route=>route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({ok:false,msg:'测试：数据暂时不可用，请重试'})});
      await page.route('**/api/exams/*/analytics',fail);
      await failingRow.locator('.exam-expand').click();
      await page.locator('#exam-message.is-error').waitFor();await stable(page,failBefore,'error notice');
      await page.unroute('**/api/exams/*/analytics',fail);
      await failingRow.locator('.exam-expand').click();await failingRow.locator('.exam-roster-panel').waitFor({state:'visible'});
      await page.locator('#exam-message').waitFor({state:'hidden'});await settle(page);
      const refresh=failingRow.getByRole('button',{name:'刷新数据',exact:true});
      await refresh.scrollIntoViewIfNeeded();const refreshBefore=await position(page);
      await refresh.click();await page.locator('#exam-message').waitFor({state:'hidden'});await settle(page);
      await stable(page,refreshBefore,'roster refresh');
      await failingRow.locator('.exam-expand').click();await failingRow.locator('.exam-roster-panel').waitFor({state:'hidden'});
      await settle(page);
      assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
    }
    await page.setViewportSize({width:1440,height:500});
    await page.locator('.exam-owned-row').nth(7).getByRole('button',{name:'查看试卷',exact:true}).click();
    await page.locator('.exam-editor-layout').waitFor();await settle(page);
    assert.equal((await position(page)).y,0,'opening a paper still starts at the top');
    await page.locator('.exam-heading').getByRole('button',{name:'成绩分析',exact:true}).click();
    await page.locator('.exam-stats-grid').waitFor();await settle(page);
    await page.evaluate(()=>window.scrollTo({top:250,behavior:'instant'}));
    const analyticsBefore=await position(page);assert.ok(analyticsBefore.y>100);
    await page.locator('.exam-heading').getByRole('button',{name:'刷新数据',exact:true}).evaluate(el=>el.click());
    await page.locator('#exam-message').waitFor({state:'hidden'});await settle(page);
    await stable(page,analyticsBefore,'full analytics rerender');
    await page.emulateMedia({reducedMotion:'reduce',colorScheme:'dark'});
    await page.locator('#theme-toggle-btn').click();
    await page.evaluate(()=>window.scrollTo({top:250,behavior:'instant'}));
    await page.locator('.exam-heading').getByRole('button',{name:'刷新数据',exact:true}).evaluate(el=>el.click());
    await page.locator('#exam-message').waitFor({state:'hidden'});
    await stable(page,analyticsBefore,'reduced-motion analytics refresh');
    await page.locator('#nav-library').click();
    assert.equal(await page.locator('#exam-message').isVisible(),false,'exam notices are cleared on leaving exams');
    assert.deepEqual(errors,[]);
    console.log('PASS: desktop/mobile long-list expand, collapse, delayed requests, errors and roster refresh retain scroll position; no live AI or production data');
  }finally{await browser.close();fixture.kill();}
})().catch(error=>{console.error(error);console.error(logs.slice(-1500));fixture.kill();process.exitCode=1;});
