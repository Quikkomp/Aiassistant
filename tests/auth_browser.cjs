// Isolated account-entry and workspace-motion acceptance; no real accounts or paid APIs.
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const assert = require('node:assert/strict');
const { chromium } = require('C:/Users/10657/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const site = path.resolve(__dirname, '../local_chat_site');
const out = path.resolve(__dirname, '../output/ui-review');
fs.mkdirSync(out, { recursive:true });
const html = fs.readFileSync(path.join(site, 'templates/index.html'), 'utf8')
  .replace(/\{\{\s*url_for\('static', filename='([^']+)'\)\s*\}\}/g, '/static/$1')
  .replace(/\{% if not auth.authenticated %\}([^]*?)\{% endif %\}/g, '$1')
  .replace(/\{% if auth.authenticated %\}hidden\{% endif %\}/g, '')
  .replace(/\{\{[^]*?\}\}/g, '');
const bank = {id:'1',title:'基础概念练习',created_at:'2026-10-10T10:00:00',reply:'Q1 [fill_blank]\n水的冰点是 ____ 摄氏度。',questions:['Q1 [fill_blank]\n水的冰点是 ____ 摄氏度。'],settings:{question_type:'fill_blank'},progress:{},version:0};
let loginRequests=0, registerRequests=0, guestRequests=0;
const server = http.createServer(async (req,res)=>{
  const url=new URL(req.url,'http://localhost');
  if(url.pathname==='/') {res.setHeader('Content-Type','text/html; charset=utf-8'); return res.end(html);}
  if(url.pathname.startsWith('/static/')) {
    const file=path.join(site,url.pathname);
    if(!fs.existsSync(file)) {res.statusCode=404; return res.end();}
    res.setHeader('Content-Type',file.endsWith('.js')?'text/javascript':file.endsWith('.css')?'text/css':file.endsWith('.svg')?'image/svg+xml':'image/png');
    return res.end(fs.readFileSync(file));
  }
  let raw=''; for await(const chunk of req) raw+=chunk;
  const data=JSON.parse(raw||'{}');
  res.setHeader('Content-Type','application/json; charset=utf-8');
  const send=data=>res.end(JSON.stringify(data));
  if(url.pathname==='/api/auth/login') {
    loginRequests++;
    if(data.password!=='demo-password') {res.statusCode=401; return send({ok:false,msg:'用户名或密码不正确'});}
    return send({ok:true,username:data.username,role:data.role});
  }
  if(url.pathname==='/api/auth/register') {registerRequests++; return send({ok:true,username:data.username,role:data.role});}
  if(url.pathname==='/api/auth/guest') {guestRequests++; return send({ok:true});}
  if(url.pathname==='/api/auth/logout') return send({ok:true});
  if(url.pathname==='/api/question_sets') return send({ok:true,banks:[bank],limit:10});
  if(url.pathname==='/api/kb_status') return send({ok:true,ready:false,files:[],total_files:0});
  if(url.pathname==='/api/past_exam/list') return send({ok:true,questions:[]});
  if(url.pathname.endsWith('/progress')) {bank.progress=data.progress; bank.version++; return send({ok:true,version:bank.version});}
  return send({ok:true});
});
(async()=>{
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  let browser;
  try {browser=await chromium.launch({headless:true});}
  catch(_) {browser=await chromium.launch({headless:true,channel:'msedge'});}
  const page=await browser.newPage({viewport:{width:1440,height:1000}});
  const errors=[]; page.on('pageerror',error=>errors.push(error.message));
  const base='http://127.0.0.1:'+server.address().port;
  const settle=()=>page.waitForFunction(()=>document.getAnimations().every(a=>a.playState==='finished'));
  const capture=async name=>{await settle(); await page.screenshot({path:path.join(out,name),fullPage:true});};
  const fits=()=>page.evaluate(()=>document.querySelector('#auth-screen').scrollWidth<=innerWidth);
  try {
    await page.goto(base);await page.locator('[data-login-role=student]').click();
    assert.equal(await page.locator('#login-form').isVisible(),true);
    assert.equal(await page.locator('.bank-app').isVisible(),false);
    const layout=await page.evaluate(()=>({form:document.querySelector('.auth-card').getBoundingClientRect().x,visual:document.querySelector('.auth-visual').getBoundingClientRect().x,animation:getComputedStyle(document.querySelector('.auth-card')).animationName}));
    assert.ok(layout.visual<layout.form, 'Visual left, login form right');
    assert.ok(await page.locator('.auth-shell').evaluate(e=>e.getBoundingClientRect().width<=1321),'Login card stays compact');
    assert.ok(await page.locator('.auth-copy-login h1').evaluate(e=>e.getBoundingClientRect().height<parseFloat(getComputedStyle(e).lineHeight)*1.5),'Welcome title fits on one line on desktop');
    assert.equal(layout.animation,'authFormArrive');
    assert.ok(await fits());
    await capture('auth-login-desktop.png');
    await page.locator('#login-form .auth-link').click();
    assert.equal(await page.locator('#register-form').isVisible(),true);
    await capture('auth-register-desktop.png');
    await page.locator('#auth-lang-toggle-btn').click();
    assert.match(await page.locator('#register-form h2').textContent(),/Create/);
    await page.locator('#register-form .auth-switch button').click();
    await page.locator('#login-username').fill('Student');
    await page.locator('#login-password').fill('wrong-demo-password');
    await page.locator('#login-form [type="submit"]').click();
    await page.waitForFunction(()=>document.querySelector('#login-message').textContent.includes('不正确'));
    assert.equal(loginRequests,1);
    await page.locator('#login-password').fill('demo-password');
    await page.locator('#login-form [type="submit"]').click();
    await page.locator('#bank-library-view').waitFor({state:'visible'});
    assert.equal(await page.locator('#account-name').textContent(),'Student');
    await page.locator('#nav-practice').click();
    await page.locator('#bank-practice-view').waitFor({state:'visible'});
    const motion=await page.locator('#bank-practice-view').evaluate(el=>{
      const effect=el.getAnimations().find(a=>a.id==='workspace-transition')?.effect;
      return {duration:effect?.getTiming().duration, frames:effect?.getKeyframes().map(({opacity,transform})=>({opacity,transform}))};
    });
    assert.equal(motion.duration,180);
    assert.deepEqual(motion.frames,[{opacity:'0.55',transform:'translateY(3px)'},{opacity:'1',transform:'translateY(0px)'}]);
    await settle();
    await page.locator('#nav-library').click();
    const libraryFrames=await page.locator('#bank-library-view').evaluate(el=>el.getAnimations().find(a=>a.id==='workspace-transition')?.effect.getKeyframes().map(({opacity,transform})=>({opacity,transform})));
    assert.deepEqual(libraryFrames,motion.frames);
    assert.equal(await page.locator('#bank-library-view').isVisible(),true);
    assert.equal(await page.locator('#bank-practice-view').isVisible(),false);
    // Fast repeated navigation must not leave a panel translucent or translated.
    await page.locator('#nav-practice').click();
    await page.locator('#bank-practice-view').waitFor({state:'visible'});
    await page.locator('#nav-library').click();
    await settle();
    assert.equal(await page.locator('#bank-library-view').evaluate(el=>getComputedStyle(el).opacity),'1');
    await page.locator('#logout-btn').click();await page.locator('[data-login-role=student]').click();
    await page.locator('#login-form').waitFor({state:'visible'});
    assert.equal(await page.locator('.auth-card').evaluate(el=>getComputedStyle(el).animationName),'authFormArrive');
    await page.setViewportSize({width:390,height:844});
    await settle();
    await page.locator('#auth-lang-toggle-btn').click();
    assert.ok(await fits());
    assert.equal(await page.locator('.auth-visual').isVisible(),false);
    await capture('auth-login-mobile.png');
    await page.locator('#login-form .auth-link').click();
    assert.ok(await fits());
    await capture('auth-register-mobile.png');
    await page.locator('#register-username').fill('NewStudent');
    await page.locator('#register-email').fill('student@example.com');
    await page.locator('#register-password').fill('demo-password');
    await page.locator('#register-confirm').fill('demo-password');
    await page.locator('#terms-check').check();
    await page.locator('#register-form [type="submit"]').click();
    await page.locator('#bank-library-view').waitFor({state:'visible'});
    assert.equal(registerRequests,1);
    assert.equal(await page.locator('#account-name').textContent(),'NewStudent');
    await page.emulateMedia({reducedMotion:'reduce'});
    await page.goto(base);await page.locator('[data-login-role=student]').click();
    assert.equal(await page.locator('.auth-card').evaluate(el=>getComputedStyle(el).animationName),'none');
    await page.locator('#guest-btn').click();
    await page.locator('#bank-library-view').waitFor({state:'visible'});
    assert.equal(guestRequests,1);
    await page.locator('#nav-practice').click();
    await page.locator('#bank-practice-view').waitFor({state:'visible'});
    assert.equal(await page.locator('#bank-practice-view').evaluate(el=>el.getAnimations().length),0);
    assert.equal(await page.locator('#account-chip').isVisible(),false);
    assert.deepEqual(errors,[]);
    console.log('PASS: split login/register layout, entrance/re-entry animations, mock auth/guest, matching 180ms/3px workspace transitions, fast navigation, mobile, language and reduced motion; no browser errors');
  } finally {await browser.close(); await new Promise(resolve=>server.close(resolve));}
})().catch(error=>{console.error(error); process.exitCode=1;});
