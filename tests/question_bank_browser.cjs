// UI acceptance with mocked AI/upload responses. No paid API or user data is used.
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const assert = require('node:assert/strict');
const { chromium } = require('C:/Users/10657/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const root = path.resolve(__dirname, '..');
const site = path.join(root, 'local_chat_site');
const out = path.join(root, 'output', 'ui-review');
fs.mkdirSync(out, { recursive: true });
let banks = [];
let files = [];
let generatedRequest;
let pauseGeneration=false, failGeneration=false, releaseGeneration, generationStarted;
const reply = 'Q1 [fill_blank]\n水在标准大气压下的冰点是 ____ 摄氏度。\n\nQ2 [multiple_choice]\n哪个温度对应冰点？\nA. 0°C\nB. 10°C\nC. 30°C\nD. 100°C';
const template = fs.readFileSync(path.join(site, 'templates', 'index.html'), 'utf8')
  .replace(/\{\{\s*url_for\('static', filename='([^']+)'\)\s*\}\}/g, '/static/$1')
  .replace(/\{% if not auth.authenticated %\}[^]*?\{% endif %\}/g, '')
  .replace(/\{% if auth.authenticated %\}hidden\{% endif %\}/g, 'hidden')
  .replace(/\{\{[^]*?\}\}/g, 'Student');
const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, 'http://localhost');
  if (url.pathname === '/' || url.pathname === '/profile') {
    res.setHeader('Content-Type', 'text/html; charset=utf-8'); res.end(template); return;
  }
  if (url.pathname.startsWith('/static/')) {
    const file = path.join(site, url.pathname);
    if (!fs.existsSync(file)) { res.statusCode = 404; res.end(); return; }
    res.setHeader('Content-Type', file.endsWith('.js') ? 'text/javascript' : file.endsWith('.css') ? 'text/css' : 'image/png');
    res.end(fs.readFileSync(file)); return;
  }
  let body = '';
  for await (const chunk of req) body += chunk;
  const data = req.headers['content-type']?.includes('application/json') ? JSON.parse(body || '{}') : {};
  res.setHeader('Content-Type', 'application/json; charset=utf-8');
  const send = obj => res.end(JSON.stringify(obj));
  if (url.pathname === '/api/question_sets') return send({ ok: true, banks, limit: 10 });
  if (url.pathname === '/api/kb_status') return send({ ok: true, ready: files.length > 0, files, total_files: files.length });
  if (url.pathname === '/api/past_exam/list') return send({ ok: true, questions: [{ id: 1, source_file: '示例试卷.pdf', question_type: 'short_answer', question: 'Explain a concept.' }] });
  if (url.pathname === '/api/upload') { files = ['课程资料.txt']; return send({ ok: true, saved: files, total_files: 1 }); }
  if (url.pathname === '/api/chat') {
    generatedRequest = data;
    if(pauseGeneration)await new Promise(resolve=>{releaseGeneration=resolve;generationStarted?.();});
    if(failGeneration) {res.statusCode=502;return send({ok:false,msg:'模拟生成失败，请重试。'});}
    const bank = { id: String(banks.length + 1), title: data.bank_title || '课程练习', created_at: new Date().toISOString(), reply,
      questions: reply.split(/\n\n/), settings: data, progress: {}, version: 0 };
    banks.unshift(bank); return send({ ok: true, reply, bank });
  }
  if (url.pathname.endsWith('/progress')) {
    const bank = banks.find(b => b.id === url.pathname.split('/')[3]);
    if (!bank || data.version !== bank.version) { res.statusCode = 409; return send({ ok: false, msg: 'Version conflict' }); }
    bank.progress = data.progress; bank.version++; return send({ ok: true, version: bank.version });
  }
  if (url.pathname === '/api/grade') return send({ ok: true, result: 'Result: Correct\nReference answer: 0°C\nBrief explanation: Water freezes at zero Celsius.' });
  if (url.pathname === '/api/scenario_question') return send({ ok: true, scenario_question: 'Q1 [short_answer]\n请说明冰点在实际生活中的应用。' });
  if (url.pathname === '/api/exam_feedback') return send({ ok: true, round_id: 1, feedback: '本轮练习已完成。' });
  return send({ ok: true });
});

(async () => {
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const base = `http://127.0.0.1:${server.address().port}`;
  let browser;
  try { browser = await chromium.launch({ headless: true }); }
  catch (_) { browser = await chromium.launch({ headless: true, channel: 'msedge' }); }
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  const errors = [];
  page.on('pageerror', err => errors.push(err.message));
  try {
    await page.goto(base);
    await page.locator('#create-bank-btn').waitFor();
    assert.equal(await page.locator('#bank-library-view').isVisible(), true);
    assert.equal(await page.locator('.bank-navigation a[href="/profile"]').count(), 0);
    assert.equal(await page.locator('.bank-sidebar-bottom a[href="/profile"]').isVisible(), true);
    assert.ok(await page.locator('.bank-profile-link').evaluate(el=>el.getBoundingClientRect().top > innerHeight * .7));
    await page.screenshot({ path: path.join(out, 'library-desktop.png'), fullPage: true });
    await page.locator('#create-bank-btn').click();
    assert.equal(await page.locator('#create-bank-dialog').isVisible(), true);
    assert.equal(await page.locator('#creator-details').getAttribute('open'), null);
    assert.equal(await page.locator('.creator-composer > .creator-suggestions [data-prompt-example]').count(), 3);
    assert.equal(await page.locator('.creator-composer-footer [data-prompt-example]').count(), 0);
    const promptStyles = await page.locator('[data-prompt-example]').evaluateAll(buttons => buttons.map(el => {
      const s = getComputedStyle(el);
      return { border: s.borderTopWidth, background: s.backgroundColor, animation: s.animationName, delay: parseFloat(s.animationDelay) };
    }));
    assert.ok(promptStyles.every(s => s.border === '0px' && s.background === 'rgba(0, 0, 0, 0)' && s.animation === 'promptReveal'));
    assert.ok(promptStyles[0].delay < promptStyles[1].delay && promptStyles[1].delay < promptStyles[2].delay);
    await page.locator('[data-prompt-example="basics"]').click();
    assert.equal((await page.locator('#user-input').inputValue()).includes('5 道基础概念填空题'), true);
    assert.equal(await page.locator('.bank-name-label').evaluate(el => getComputedStyle(el).color), 'rgb(66, 81, 106)');
    await page.locator('#user-input').fill('根据上传资料生成两道题，包含一道填空和一道选择。');
    await page.locator('#bank-title-input').fill('基础概念练习');
    await page.locator('#file-input').setInputFiles({ name: '课程资料.txt', mimeType: 'text/plain', buffer: Buffer.from('Water freezes at zero Celsius.') });
    await page.waitForFunction(() => document.querySelectorAll('.material-checkbox').length === 1);
    await page.locator('#creator-details > summary').click();
    await page.locator('#past-exam-style-toggle').check();
    await page.locator('#past-exam-template-source').selectOption('示例试卷.pdf');
    await page.screenshot({ path: path.join(out, 'creator-settings-desktop.png'), fullPage: true });
    await page.locator('#creator-details > summary').click();
    await page.screenshot({ path: path.join(out, 'creator-desktop.png'), fullPage: true });
    pauseGeneration=true;
    const started=new Promise(resolve=>generationStarted=resolve);
    await page.locator('#send-btn').click();await started;
    await page.locator('#creator-generation-overlay').waitFor({state:'visible'});
    assert.equal(await page.locator('#create-bank-dialog').getAttribute('aria-busy'),'true');
    assert.equal(await page.locator('#creator-dialog-scroll').evaluate(el=>el.inert),true);
    assert.equal(await page.locator('#close-creator-btn').isDisabled(),true);
    assert.equal(await page.locator('.creator-generation-bolt').evaluate(el=>getComputedStyle(el).animationName),'creatorBoltBounce');
    assert.equal(await page.locator('.creator-generation-bolt').evaluate(el=>getComputedStyle(el).animationIterationCount),'infinite');
    await page.keyboard.press('Escape');assert.equal(await page.locator('#create-bank-dialog').isVisible(),true);
    await page.screenshot({path:path.join(out,'creator-generating-desktop.png'),fullPage:true});
    await page.setViewportSize({width:390,height:844});
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
    const center=await page.locator('#creator-generation-overlay').evaluate(el=>{
      const a=el.getBoundingClientRect(),b=document.querySelector('#create-bank-dialog').getBoundingClientRect();
      return {x:Math.abs(a.x+a.width/2-b.x-b.width/2),y:Math.abs(a.y+a.height/2-b.y-b.height/2)};
    });assert.ok(center.x<2&&center.y<2);
    await page.screenshot({path:path.join(out,'creator-generating-mobile.png'),fullPage:true});
    await page.evaluate(()=>document.body.classList.add('dark-theme'));
    await page.screenshot({path:path.join(out,'creator-generating-dark-mobile.png'),fullPage:true});
    await page.evaluate(()=>document.body.classList.remove('dark-theme'));
    await page.emulateMedia({reducedMotion:'reduce'});
    assert.equal(await page.locator('.creator-generation-bolt').evaluate(el=>getComputedStyle(el).animationName),'none');
    assert.equal(await page.locator('#creator-generation-overlay').isVisible(),true);
    await page.emulateMedia({reducedMotion:'no-preference'});await page.setViewportSize({width:1440,height:1000});
    pauseGeneration=false;releaseGeneration();
    await page.locator('.bank-open-btn').waitFor();
    assert.equal(generatedRequest.style_template_only, true);
    assert.deepEqual(generatedRequest.selected_docs, ['课程资料.txt']);
    assert.deepEqual(generatedRequest.selected_past_exam_ids, [1]);
    assert.equal(generatedRequest.message.includes('两道题'), true);
    assert.equal(await page.locator('#create-bank-dialog').isVisible(), false);
    assert.equal(await page.locator('#creator-generation-overlay').getAttribute('hidden'),'');
    assert.equal(await page.locator('#creator-dialog-scroll').evaluate(el=>el.inert),false);
    await page.screenshot({ path: path.join(out, 'library-saved-desktop.png'), fullPage: true });
    await page.locator('.bank-open-btn').click();
    await page.locator('.feedback-tools > summary').click();
    assert.equal(await page.locator('.feedback-response-group button:disabled').count(), 2);
    assert.equal(await page.locator('.feedback-learning-group button:disabled').count(), 2);
    assert.equal(await page.locator('.feedback-action-hint').isVisible(), true);
    await page.locator('.feedback-tools > summary').click();
    await page.locator('.answer-input').fill('0');
    await page.waitForFunction(() => document.querySelector('#bank-save-status').textContent === '已保存');
    await page.locator('.submit-btn').click();
    await page.locator('.grade-result').getByText('Result: Correct').waitFor();
    assert.equal(await page.locator('.feedback-response-group button:disabled').count(), 0);
    assert.equal(await page.locator('.feedback-action-hint').isVisible(), false);
    await page.locator('#exam-next-btn').click();
    await page.locator('.question-choice-btn').first().click();
    await page.locator('#back-to-bank-btn').click();
    await page.reload();
    await page.locator('.bank-open-btn').click();
    assert.equal(await page.locator('.question-choice-btn.selected').count(), 1);
    await page.locator('#exam-prev-btn').click();
    assert.equal(await page.locator('.answer-input').inputValue(), '0');
    for (const selector of ['.feedback-tools > summary', '.practice-score-details > summary']) {
      const summary = page.locator(selector);
      const initial = await summary.evaluate(el => {
        const style = getComputedStyle(el);
        return { background: style.backgroundColor, height: el.getBoundingClientRect().height, color: style.color };
      });
      assert.ok(initial.height >= 44, 'Disclosure has a touch-friendly hit area');
      assert.equal(initial.color, 'rgb(53, 84, 165)');
      await summary.hover();
      await page.waitForFunction(({ selector, background }) => getComputedStyle(document.querySelector(selector)).backgroundColor !== background,
        { selector, background: initial.background });
      await summary.focus();
      await page.keyboard.press('Enter');
      assert.equal(await summary.evaluate(el => el.parentElement.open), true);
      await page.keyboard.press('Enter');
      assert.equal(await summary.evaluate(el => el.parentElement.open), false);
    }
    await page.mouse.move(0, 0);
    await page.locator('.feedback-tools > summary').click();
    await page.waitForFunction(() => Array.from(document.querySelectorAll('.feedback-action-buttons button')).every(el => el.getAnimations().every(animation => animation.playState === 'finished')));
    const actionStyles = await page.locator('.feedback-action-buttons button').evaluateAll(buttons => buttons.map(el => ({ height: el.getBoundingClientRect().height, background: getComputedStyle(el).backgroundColor })));
    assert.ok(actionStyles.every(s => s.height === 40));
    assert.equal(actionStyles[0].background, 'rgb(237, 247, 241)');
    assert.equal(actionStyles[1].background, 'rgb(255, 245, 233)');
    assert.equal(actionStyles[4].background, 'rgb(237, 243, 255)');
    await page.locator('.ask-ai-btn').click();
    assert.equal(await page.locator('#question-qa-panel').isVisible(), true);
    await page.locator('#scenario-entry-btn').click();
    assert.equal(await page.locator('#scenario-modal').isVisible(), true);
    await page.locator('#scenario-close-btn').click();
    if (!(await page.locator('.understand-row').isVisible())) await page.locator('.feedback-tools > summary').click();
    await page.waitForFunction(() => Array.from(document.querySelectorAll('.feedback-action-buttons button')).every(el => el.getAnimations().every(animation => animation.playState === 'finished')));
    await page.screenshot({ path: path.join(out, 'feedback-actions-desktop.png'), fullPage: true });
    await page.setViewportSize({ width: 390, height: 844 });
    assert.ok(await page.locator('.understand-row').evaluate(el => el.children[1].getBoundingClientRect().top > el.children[0].getBoundingClientRect().bottom));
    await page.screenshot({ path: path.join(out, 'feedback-actions-mobile.png'), fullPage: true });
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
    await page.locator('.feedback-tools .understand-btn').click();
    assert.equal(await page.locator('.question-choice-btn').count(), 4);
    await page.locator('#exam-prev-btn').click();
    await page.setViewportSize({ width: 1440, height: 1000 });
    await page.screenshot({ path: path.join(out, 'practice-desktop.png'), fullPage: true });
    await page.setViewportSize({ width: 390, height: 844 });
    await page.screenshot({ path: path.join(out, 'practice-mobile.png'), fullPage: true });
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
    await page.locator('#back-to-bank-btn').click();
    await page.locator('#create-bank-btn').click();
    await page.waitForFunction(() => Array.from(document.querySelectorAll('[data-prompt-example]')).every(el => getComputedStyle(el).opacity === '1'));
    await page.screenshot({ path: path.join(out, 'creator-mobile.png'), fullPage: true });
    await page.locator('[data-prompt-example="challenge"]').click();
    assert.equal((await page.locator('#user-input').inputValue()).includes('5 道高难度简答题'), true);
    assert.equal(await page.evaluate(() => document.querySelector('#create-bank-dialog').scrollWidth <= document.querySelector('#create-bank-dialog').clientWidth), true);
    await page.emulateMedia({ reducedMotion: 'reduce' });
    assert.equal(await page.locator('[data-prompt-example="basics"]').evaluate(el => getComputedStyle(el).animationName), 'none');
    await page.emulateMedia({ reducedMotion: 'no-preference' });
    // A failed generation stops the animation and preserves the prompt for retry.
    pauseGeneration=true;failGeneration=true;
    const failedStart=new Promise(resolve=>generationStarted=resolve);
    const preservedPrompt=await page.locator('#user-input').inputValue();
    await page.locator('#send-btn').click();await failedStart;
    await page.locator('#creator-generation-overlay').waitFor({state:'visible'});
    pauseGeneration=false;releaseGeneration();
    await page.locator('#creator-message').getByText('模拟生成失败，请重试。',{exact:true}).waitFor();
    assert.equal(await page.locator('#creator-generation-overlay').isVisible(),false);
    assert.equal(await page.locator('#create-bank-dialog').getAttribute('aria-busy'),'false');
    assert.equal(await page.locator('#creator-dialog-scroll').evaluate(el=>el.inert),false);
    assert.equal(await page.locator('#send-btn').isEnabled(),true);
    assert.equal(await page.locator('#user-input').inputValue(),preservedPrompt);
    failGeneration=false;
    await page.locator('#creator-details > summary').click();
    assert.equal(await page.evaluate(() => document.querySelector('#create-bank-dialog').scrollWidth <= document.querySelector('#create-bank-dialog').clientWidth), true);
    await page.locator('#close-creator-btn').click();
    await page.screenshot({ path: path.join(out, 'library-mobile.png'), fullPage: true });
    assert.equal(await page.locator('.bank-profile-link').isVisible(), true);
    assert.equal(await page.locator('.bank-sidebar-bottom [data-bank-i18n="storage"]').count(), 0);
    assert.equal(await page.locator('.bank-page-heading [data-bank-i18n="librarySubtitle"]').evaluate(el => getComputedStyle(el).color), 'rgb(89, 101, 121)');
    await page.locator('.bank-capacity-wrap').focus();
    await page.waitForFunction(() => getComputedStyle(document.querySelector('#bank-capacity-help')).visibility === 'visible');
    assert.equal(await page.locator('#bank-capacity-help').evaluate(el => getComputedStyle(el).visibility), 'visible');
    await page.setViewportSize({ width: 1440, height: 1000 });
    const original = banks[0];
    banks = Array.from({ length: 9 }, (_, i) => ({ ...original, id: `capacity-${i}`, title: `练习 ${i + 1}`, progress: {}, version: 0 }));
    await page.reload();
    await page.waitForFunction(() => document.querySelector('#bank-capacity').textContent.includes('9 / 10'));
    assert.equal(await page.locator('#bank-capacity-warning').textContent(), '还可创建 1 组题目。');
    await page.locator('#create-bank-btn').click();
    assert.equal((await page.locator('#creator-capacity-hint').textContent()).includes('最后一个可用位置'), true);
    await page.locator('#close-creator-btn').click();
    banks.push({ ...original, id: 'capacity-10', progress: {}, version: 0 });
    await page.reload();
    await page.waitForFunction(() => document.querySelector('#bank-capacity').classList.contains('is-full'));
    await page.locator('#create-bank-btn').click();
    assert.equal(await page.locator('#create-bank-dialog').isVisible(), false);
    assert.equal((await page.locator('#bank-page-message').textContent()).includes('题库已满'), true);
    await page.locator('#lang-toggle-btn').click();
    assert.equal(await page.locator('#bank-capacity').textContent(), '10 / 10 sets saved');
    assert.equal((await page.locator('#bank-capacity-warning').textContent()).includes('Library full'), true);
    await page.locator('#lang-toggle-btn').click();
    await page.screenshot({ path: path.join(out, 'library-full-desktop.png'), fullPage: true });
    assert.deepEqual(errors, []);
    console.log('PASS: create/upload/template/save/reload/answers/grading/navigation/mobile/capacity warnings/i18n; bouncing generation overlay, success/failure cleanup, modal/input locks, dark/mobile/reduced motion; no browser errors');
  } finally {releaseGeneration?.(); await browser.close(); server.close(); }
})().catch(err => { console.error(err); server.close(); process.exitCode = 1; });
