// Real templates/scripts + local fonts, mocked questions/AI. No account data or paid requests.
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const assert = require('node:assert/strict');
const {chromium} = require('C:/Users/10657/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const site = path.resolve(__dirname, '../local_chat_site');
const out = path.resolve(__dirname, '../output/ui-review');
fs.mkdirSync(out, {recursive:true});
const formula = String.raw`\(S_{area}=\frac{1}{2}\times\pi\times r^2\)`;
const display = String.raw`\[
\int_0^1 x^2\,dx=\frac{1}{3}
\]`;
const questions = [String.raw`Q1 [multiple_choice]: 下列哪项是计算半圆面积的正确公式？
A. \(S_{area}=2\times\pi\times r^2\)
B. \(S_{area}=\pi\times r^2\)
C. ${formula}
D. \(S_{area}=\frac{1}{4}\times\pi\times r^2\)`, `Q2 [short_answer]\n计算积分：${display}`];
const feedback = `Result: Correct\nReference answer: ${formula}\nBrief explanation: 半圆面积是圆面积的一半。\n${display}`;
const report = `复习面积公式 ${formula}，不要忘记除以 2。`;
const bank = {id:'math-set', title:'半圆面积与积分', questions, reply:questions.join('\n\n'), settings:{}, progress:{}, version:0};
const template = name => fs.readFileSync(path.join(site, 'templates', name), 'utf8')
  .replace(/\{\{\s*url_for\('static', filename='([^']+)'\)\s*\}\}/g, '/static/$1')
  .replace(/\{% if not auth.authenticated %\}[^]*?\{% endif %\}/g, '')
  .replace(/\{% if auth.authenticated %\}hidden\{% endif %\}/g, 'hidden')
  .replace(/\{\{[^]*?\}\}/g, 'Student');
const examQuestion = {text:questions[0], type:'multiple_choice', points:100, submission:null};
const attempt = {id:'math-attempt', title:'数学考试', status:'active', total:100, questions:[examQuestion]};
const server = http.createServer(async (req,res) => {
  const url = new URL(req.url, 'http://localhost');
  if (url.pathname === '/' || url.pathname === '/profile') {
    res.setHeader('Content-Type', 'text/html; charset=utf-8');
    return res.end(template(url.pathname === '/' ? 'index.html' : 'profile.html'));
  }
  if (url.pathname.startsWith('/static/')) {
    const file = path.join(site, url.pathname);
    if (!file.startsWith(site + path.sep) || !fs.existsSync(file)) {res.statusCode=404; return res.end();}
    res.setHeader('Content-Type', file.endsWith('.js')?'text/javascript':file.endsWith('.css')?'text/css':file.endsWith('.svg')?'image/svg+xml':file.endsWith('.woff2')?'font/woff2':'application/octet-stream');
    return res.end(fs.readFileSync(file));
  }
  let raw=''; for await (const chunk of req) raw+=chunk;
  const data=JSON.parse(raw || '{}');
  res.setHeader('Content-Type', 'application/json; charset=utf-8');
  const send = value => res.end(JSON.stringify(value));
  if (url.pathname === '/api/question_sets') return send({ok:true,banks:[bank],limit:10});
  if (url.pathname.endsWith('/progress')) {bank.progress=data.progress; bank.version++; return send({ok:true,version:bank.version});}
  if (url.pathname === '/api/kb_status') return send({ok:true,files:[],ready:false,total_files:0});
  if (url.pathname === '/api/past_exam/list') return send({ok:true,questions:[]});
  if (url.pathname === '/api/grade') return send({ok:true,result:feedback});
  if (url.pathname === '/api/explain_detailed') return send({ok:true,explanation:`由完整圆的面积推导：${formula}\n${display}`});
  if (url.pathname === '/api/qa') return send({ok:true,reply:report});
  if (url.pathname.includes('/shared/') && url.pathname.endsWith('/start')) return send({ok:true,attempt});
  if (url.pathname.includes('/shared/')) return send({ok:true,exam:{title:'数学考试',teacher:'Teacher',count:1,total:100,status:'published',description:formula}});
  if (url.pathname.endsWith('/answer')) {
    examQuestion.submission={answer:data.answer,status:'graded',ratio:1,feedback};
    Object.assign(examQuestion,{answer:formula,explanation:report}); return send({ok:true,attempt});
  }
  if (url.pathname.endsWith('/support')) return send({ok:true,text:report});
  if (url.pathname === '/api/profile') return send({ok:true,user:{username:'Student',email:'test@example.com'},total_rounds:1});
  if (url.pathname === '/api/profile/rounds') return send({ok:true,rounds:[{id:1,created_at:'2026-10-20',round_score:100,total_questions:1,has_analysis:true}]});
  if (url.pathname === '/api/profile/rounds/1') return send({ok:true,round:{id:1,created_at:'2026-10-20',analysis:report},answers:[{question:questions[0],student_answer:formula,evaluation:feedback,verdict:'correct'}]});
  return send({ok:true});
});

(async () => {
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  let browser;
  try {
    try {browser=await chromium.launch({headless:true});} catch (_) {browser=await chromium.launch({headless:true,channel:'msedge'});}
    const page=await browser.newPage({viewport:{width:1440,height:1000}}), errors=[], external=[], failed=[];
    const base=`http://127.0.0.1:${server.address().port}`;
    page.on('pageerror',error=>errors.push(error.message));
    page.on('requestfailed',req=>failed.push(req.url()));
    await page.route('**/*', route=>{
      if (!route.request().url().startsWith(base)) {external.push(route.request().url());return route.abort();}
      return route.continue();
    });
    await page.goto(base);
    await page.locator('.bank-open-btn').first().click();
    assert.equal(await page.locator('.question-choice-text .katex').count(),4);
    await page.locator('.question-choice-btn[data-choice="C"]').click();
    assert.equal(await page.locator('.question-choice-btn[data-choice="C"]').getAttribute('aria-checked'),'true');
    await page.locator('.submit-btn').click();
    await page.locator('.grade-result .katex-display').waitFor();
    assert.equal(await page.locator('.grade-result .katex').count(),2);
    await page.locator('.feedback-tools summary').click();
    await page.locator('.explain-btn').click();
    await page.locator('#explain-modal-content .katex-display').waitFor();
    assert.equal(await page.locator('#explain-modal-question .katex').count(),4);
    await page.locator('#explain-close-btn').click();
    await page.evaluate(report=>showExamFeedback(report), report);
    await page.waitForFunction(report=>document.querySelector('#bank-save-status').textContent==='已保存',report);
    assert.equal(bank.progress.examFeedback,report);
    assert.equal(bank.progress.questionAnswers[0],'C');
    assert.equal(bank.progress.questionEvaluations[0],feedback);
    await page.screenshot({path:path.join(out,'math-question-desktop.png'),fullPage:true});
    await page.reload();await page.locator('.bank-open-btn').first().click();
    assert.equal(await page.locator('.question-choice-text .katex').count(),4);
    assert.equal(await page.locator('#exam-feedback .katex').count(),1);
    await page.locator('#exam-next-btn').click();
    assert.equal(await page.locator('.question-card-body .katex-display').count(),1);

    // Currency, escaping, malformed formulas, code and malicious HTML remain safe.
    const checks=await page.evaluate(() => {
      const el=document.createElement('div');document.body.append(el);
      const raw=String.raw`价格 $10 and $20；转义 \$x\$；$x^2$；$$y^2$$；\(\unknownCommand{x}\)；\(z_1\) <img src=x onerror="window.injected=1">`;
      window.mathUI.setText(el,raw);
      const count=el.querySelectorAll('.katex').length;
      window.mathUI.render(el);
      const safe=count===3&&el.querySelectorAll('.katex').length===3&&!el.querySelector('img')&&!window.injected&&el.textContent.includes('$10 and $20')&&el.textContent.includes('\\$x\\$')&&window.mathUI.source(el)===raw;
      const code=document.createElement('code');code.textContent=String.raw`\(a^2\)`;el.append(code);window.mathUI.render(el);
      const codeSafe=!code.querySelector('.katex');
      window.mathUI.setText(el,String.raw`\(\href{javascript:alert(1)}{x}\) \(\includegraphics{https://example.com/x.png}\) \(\def\a{\a}\a\)`);
      const trustSafe=!el.querySelector('a,img,script');
      el.remove();return {safe,codeSafe,trustSafe};
    });
    assert.deepEqual(checks,{safe:true,codeSafe:true,trustSafe:true});

    await page.evaluate(()=>window.examUI.openToken('a'.repeat(48)));
    await page.getByRole('button',{name:'开始训练',exact:true}).click();
    await page.locator('.exam-question-text .katex').first().waitFor();
    assert.equal(await page.locator('.exam-question-text .katex').count(),4);
    assert.equal(await page.locator('.exam-grade').count(),0);
    await page.locator('#exam-view textarea').fill('C');
    await page.getByRole('button',{name:'提交并锁定答案',exact:true}).click();
    await page.locator('.exam-grade .katex').first().waitFor();
    assert.equal(await page.locator('#exam-view textarea').inputValue(),'C');
    assert.equal(await page.locator('#exam-view textarea').isDisabled(),true);
    await page.locator('.exam-learning summary').click();
    await page.getByRole('button',{name:'详细讲解',exact:true}).click();
    await page.locator('.exam-support-result .katex').waitFor();
    assert.equal(await page.locator('.exam-support-result .katex').count(),1);
    await page.setViewportSize({width:390,height:844});
    await page.screenshot({path:path.join(out,'math-exam-mobile.png'),fullPage:true});
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
    await page.evaluate(()=>document.body.classList.add('dark-theme'));
    await page.screenshot({path:path.join(out,'math-exam-dark-mobile.png'),fullPage:true});

    await page.goto(base+'/profile');
    await page.locator('[data-profile-view="history"]').first().click();
    await page.locator('.round-list button').first().click();
    await page.locator('.round-question .katex').first().waitFor();
    assert.equal(await page.locator('#round-analysis .katex').count(),1);
    assert.equal(await page.locator('.round-answer-block .katex').count(),3);
    await page.evaluate(()=>document.fonts.ready);
    assert.deepEqual(external,[]);assert.deepEqual(failed,[]);assert.deepEqual(errors,[]);
    console.log('Math browser acceptance passed: options, grading, explanation, save/reload, exams, history, mobile, local fonts and safety.');
  } finally {await browser?.close();await new Promise(resolve=>server.close(resolve));}
})().catch(error=>{console.error(error);process.exitCode=1;});
