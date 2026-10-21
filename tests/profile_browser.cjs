// Profile acceptance against real templates/scripts with isolated mock account APIs.
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const assert = require('node:assert/strict');
const { chromium } = require('C:/Users/10657/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const site = path.resolve(__dirname, '../local_chat_site');
const out = path.resolve(__dirname, '../output/ui-review');
fs.mkdirSync(out, { recursive:true });
const html = fs.readFileSync(path.join(site, 'templates/profile.html'), 'utf8').replace(/\{\{\s*url_for\('static', filename='([^']+)'\)\s*\}\}/g, '/static/$1');
let passwordRequests = 0;
let failHistory = false;
let detailDelay = 0;
let submittedPassword;
const rounds = [{ id:1, created_at:'2026-10-10 10:00', total_questions:5, round_score:80, has_analysis:true }, { id:2, created_at:'2026-10-09 16:00', total_questions:3, round_score:65, has_analysis:false }];
const server = http.createServer(async (req,res) => {
  const url = new URL(req.url, 'http://localhost');
  if (url.pathname === '/profile') { res.setHeader('Content-Type', 'text/html; charset=utf-8'); return res.end(html); }
  if (url.pathname === '/') { res.setHeader('Content-Type', 'text/html; charset=utf-8'); return res.end('<h1>Library</h1>'); }
  if (url.pathname.startsWith('/static/')) {
    const file = path.join(site, url.pathname);
    res.setHeader('Content-Type', file.endsWith('.js') ? 'text/javascript' : file.endsWith('.css') ? 'text/css' : file.endsWith('.svg') ? 'image/svg+xml' : 'image/png');
    return res.end(fs.readFileSync(file));
  }
  let raw=''; for await (const chunk of req) raw+=chunk;
  const data=JSON.parse(raw || '{}');
  res.setHeader('Content-Type','application/json; charset=utf-8');
  const send=data=>res.end(JSON.stringify(data));
  if (url.pathname === '/api/profile') return send({ ok:true, user:{ username:'Student',email:'student@example.com',public_user_id:'user_demo_001'}, total_rounds:2 });
  if (url.pathname === '/api/profile/rounds') {
    if (failHistory) { res.statusCode=500; return send({ok:false,msg:'Temporary failure'}); }
    return send({ok:true,rounds});
  }
  if (url.pathname.startsWith('/api/profile/rounds/')) {
    if (detailDelay) await new Promise(resolve=>setTimeout(resolve,detailDelay));
    return send({ok:true, round:{id:1,created_at:'2026-10-10 10:00',round_score:80,correct_count:4,partial_count:0,wrong_count:1,analysis:'基本概念掌握良好，建议加强实际应用。'},answers:[{question:'Explain <script>window.injected=true</script> OpenGL.',student_answer:'A graphics API.',evaluation:'Correct. Clear explanation.',verdict:'correct'}]});
  }
  if (url.pathname === '/api/profile/change_password') { passwordRequests++; submittedPassword=data; return send({ok:true}); }
  if (url.pathname === '/api/auth/logout') return send({ok:true});
  res.statusCode=404; send({ok:false,msg:'Not found'});
});
(async()=>{
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  let browser;
  try { browser=await chromium.launch({headless:true}); }
  catch (_) { browser=await chromium.launch({headless:true,channel:'msedge'}); }
  const page=await browser.newPage({viewport:{width:1440,height:1000}});
  const errors=[]; page.on('pageerror',e=>errors.push(e.message));
  const capture = async name => {
    await page.waitForFunction(()=>document.getAnimations().every(animation=>animation.playState==='finished'));
    await page.screenshot({path:path.join(out,name),fullPage:true});
  };
  try {
    await page.goto('http://127.0.0.1:'+server.address().port+'/profile');
    await page.waitForFunction(()=>document.querySelector('#profile-info-username').textContent==='Student');
    assert.equal(await page.locator('#profile-info-view').isVisible(),true);
    assert.equal(await page.locator('.bank-sidebar-bottom > p').textContent(),'MetaThink AI & STEAM Lab@XJTLU');
    assert.equal(await page.locator('#profile-security-view').isVisible(),false);
    await capture('profile-info-desktop.png');
    await page.locator('.profile-navigation [data-profile-view="history"]').click();
    assert.equal(await page.locator('.round-item').count(),2);
    await capture('profile-history-desktop.png');
    await page.locator('.round-item').first().click();
    await page.locator('#round-detail').waitFor({state:'visible'});
    assert.equal(await page.locator('#profile-history-list-card').isVisible(),false);
    assert.equal(await page.locator('.round-question').textContent(),'Explain <script>window.injected=true</script> OpenGL.');
    assert.equal(await page.evaluate(()=>window.injected),undefined);
    await capture('profile-detail-desktop.png');
    await page.locator('#close-round-detail').click();
    assert.equal(await page.locator('#profile-history-list-card').isVisible(),true);
    detailDelay=200;
    await page.locator('.round-item').first().click();
    await page.locator('.profile-navigation [data-profile-view="security"]').click();
    await page.waitForFunction(()=>!document.querySelector('#profile-page-message').textContent);
    await page.locator('#current-password').fill('old-demo-password');
    await page.locator('#new-password').fill('new-demo-password');
    await page.locator('#confirm-password').fill('different-demo-password');
    await page.locator('#password-form [type="submit"]').click();
    assert.equal(passwordRequests,0);
    assert.equal((await page.locator('#password-message').textContent()).includes('不一致'),true);
    await page.locator('#confirm-password').fill('new-demo-password');
    await page.locator('#password-form [type="submit"]').click();
    await page.waitForFunction(()=>document.querySelector('#password-message').classList.contains('success'));
    assert.equal(passwordRequests,1);
    assert.equal(submittedPassword.current_password,'old-demo-password');
    assert.equal(await page.locator('#new-password').inputValue(),'');
    await capture('profile-security-desktop.png');
    await page.locator('#profile-lang-btn').click();
    assert.equal(await page.locator('#profile-section-title').textContent(),'Account security');
    await page.locator('#profile-theme-btn').click();
    assert.equal(await page.evaluate(()=>document.body.classList.contains('dark-theme')),true);
    await capture('profile-dark-desktop.png');
    await page.reload();
    assert.equal(await page.locator('#profile-section-title').textContent(),'Account security');
    assert.equal(await page.evaluate(()=>document.body.classList.contains('dark-theme')),true);
    await page.locator('#profile-lang-btn').click(); await page.locator('#profile-theme-btn').click();
    await page.setViewportSize({width:390,height:844});
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
    await capture('profile-security-mobile.png');
    await page.locator('.profile-navigation [data-profile-view="info"]').click();
    await page.locator('#change-password-toggle').click();
    assert.equal(await page.locator('#profile-security-view').isVisible(),true);
    failHistory=true;
    await page.goto('http://127.0.0.1:'+server.address().port+'/profile#history');
    await page.reload();
    await page.locator('#retry-history-btn').waitFor({state:'visible'});
    assert.equal((await page.locator('#round-list').textContent()).includes('加载失败'),true);
    failHistory=false;
    await page.locator('#retry-history-btn').click();
    await page.locator('.round-item').first().waitFor();
    assert.equal(await page.locator('#profile-page-message').isVisible(),false);
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
    await capture('profile-history-mobile.png');
    assert.deepEqual(errors,[]);
    console.log('PASS: profile navigation/history/detail/password validation/mock update/theme/language/retry/mobile; no browser errors');
  } finally { await browser.close(); server.close(); }
})().catch(err=>{console.error(err);server.close();process.exitCode=1;});
