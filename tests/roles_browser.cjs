// Public registration for both roles, entry motion and real authorization. Disposable DBs only.
const {spawn}=require('node:child_process'),path=require('node:path'),fs=require('node:fs'),assert=require('node:assert/strict');
const {chromium}=require('C:/Users/10657/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const root=path.resolve(__dirname,'..'),out=path.join(root,'output/ui-review');fs.mkdirSync(out,{recursive:true});
const fixture=spawn('C:/Users/10657/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe',[path.join(__dirname,'auth_fixture.py')],{cwd:root,windowsHide:true});
let logs='';fixture.stderr.on('data',c=>logs+=c);
const ready=new Promise((resolve,reject)=>{let raw='';fixture.stdout.on('data',c=>{raw+=c;try{resolve(JSON.parse(raw.split('\n')[0]).port);}catch(_){}});fixture.on('exit',code=>reject(new Error('Fixture exited '+code+' '+logs)));setTimeout(()=>reject(new Error('Fixture timeout '+logs)),15000).unref();});
(async()=>{
  const base='http://127.0.0.1:'+await ready;
  let browser;try{browser=await chromium.launch({headless:true});}catch(_){browser=await chromium.launch({headless:true,channel:'msedge'});}
  try{
    const tc=await browser.newContext({viewport:{width:1600,height:1000}}),sc=await browser.newContext({viewport:{width:1440,height:1000}}),teacher=await tc.newPage(),student=await sc.newPage(),errors=[];
    for(const p of [teacher,student])p.on('pageerror',e=>errors.push(e.message));
    const settle=p=>p.waitForFunction(()=>document.getAnimations().every(a=>a.playState==='finished'));
    const capture=async(p,name)=>{await settle(p);await p.screenshot({path:path.join(out,name),fullPage:true});};
    const assertAcademicVisuals=async p=>{
      await settle(p);
      assert.equal(await p.locator('.auth-role-mascot').count(),0);
      assert.equal(await p.locator('.auth-role-visual').count(),2);
      assert.equal(await p.locator('#auth-screen img[src*="anime"]').count(),0);
      const valid=await p.locator('.auth-role-card').evaluateAll(cards=>cards.every(card=>{
        const img=card.querySelector('.auth-role-visual'),r=img.getBoundingClientRect(),c=card.getBoundingClientRect();
        const clear=[card.querySelector('h2'),card.querySelector('p')].every(el=>{const t=el.getBoundingClientRect();return r.right<=t.left||r.left>=t.right||r.bottom<=t.top||r.top>=t.bottom;});
        return img.tagName.toLowerCase()==='svg'&&img.getAttribute('aria-hidden')==='true'&&r.left>=c.left&&r.right<=c.right&&r.top>=c.top&&r.bottom<=c.bottom&&clear&&getComputedStyle(img).pointerEvents==='none';
      }));
      if(!valid){await p.screenshot({path:path.join(out,'roles-visual-layout-debug.png'),fullPage:true});}
      assert.equal(valid,true,'Academic visuals must stay within the cards and not overlap headings or descriptions');
    };
    const register=async(p,role,name)=>{
      await p.locator('[data-login-role='+role+']').click();await settle(p);
      await p.locator('#login-form [data-auth-mode=register]').first().click();
      await p.locator('#register-username').fill(name);await p.locator('#register-email').fill(name+'@qq.com');
      await p.locator('#register-password').fill('password-123');await p.locator('#register-confirm').fill('password-123');await p.locator('#terms-check').check();
      assert.equal(await p.locator('#register-form input').count(),5,'No invitation code input');
      await p.locator('#register-form [type=submit]').click();await p.locator('.bank-app').waitFor({state:'visible'});
      assert.equal(await p.locator('#account-role-badge').textContent(),role==='teacher'?'老师':'学生');
    };
    const eb=(p,name)=>p.locator('#exam-view').getByRole('button',{name,exact:true});
    await teacher.goto(base);await teacher.locator('#auth-role-choice').waitFor();
    assert.equal(await teacher.locator('#auth-role-title').innerText(),'欢迎来到智练 WizPractice');
    assert.ok((await teacher.title()).includes('智练 WizPractice'));
    assert.equal(await teacher.locator('img[src*="metathink-logo"]').count(),0);
    await teacher.locator('.auth-topbar .logo-img').evaluate(img=>img.decode());
    assert.ok(await teacher.locator('.auth-topbar .logo-img').evaluate(img=>img.naturalWidth>0&&img.src.includes('wizpractice-mark.svg')));
    assert.ok(!/MetaThink|Meta Think|Exercise Generator/.test(await teacher.locator('body').innerText()));
    assert.equal(await teacher.locator('#login-form').isVisible(),false);
    const cards=await teacher.locator('.auth-role-card').evaluateAll(es=>es.map(e=>{const r=e.getBoundingClientRect();return {x:r.x,w:r.width,h:r.height};}));
    assert.ok(cards[0].w>=399&&cards[0].w<=401&&cards[0].h>=570&&cards[0].x<cards[1].x);
    assert.equal(cards[0].h,cards[1].h);
    assert.ok(await teacher.locator('#auth-role-title').evaluate(e=>e.getBoundingClientRect().top<130));
    assert.equal(await teacher.locator('#auth-role-choice [data-role-i18n=eyebrow]').count(),0);
    await assertAcademicVisuals(teacher);
    assert.equal(await teacher.locator('.auth-trail').count(),32);
    assert.equal(await teacher.locator('.auth-trail').first().evaluate(e=>getComputedStyle(e,'::before').height),'2px');
    assert.equal(await teacher.locator('.auth-role-journey').count(),2);
    assert.equal(await teacher.locator('.auth-journey-steps li').count(),6);
    assert.equal(await teacher.locator('.auth-journey-steps li').first().evaluate(e=>getComputedStyle(e,'::before').content),'none','Journey nodes must not inherit the feature-list checkmarks');
    const label=await teacher.locator('[data-login-role=teacher]').textContent();
    for(const role of ['teacher','student']){
      const button=teacher.locator('[data-login-role='+role+']');await button.hover();
      await button.locator('.auth-entry-arrow').evaluate(e=>{const a=e.getAnimations().find(a=>a.animationName==='authEntryArrow');if(!a||a.effect.getTiming().duration!==620)throw new Error('Expected a short arrow animation');const frames=a.effect.getKeyframes();if(!frames[0].transform.includes('-28px')||!frames.at(-1).transform.includes('0px'))throw new Error('Arrow must slide left to right');});
      await settle(teacher);assert.equal(await button.locator('.auth-entry-arrow').evaluate(e=>getComputedStyle(e).opacity),'1');
    }
    await capture(teacher,'roles-entry-arrow-hover.png');
    assert.equal(await teacher.locator('[data-login-role=teacher]').textContent(),label,'Hover must not change the button label');
    await teacher.locator('#auth-lang-toggle-btn').click();assert.equal(await teacher.locator('.auth-journey-caption').first().textContent(),'A clearer teaching journey');assert.equal(await teacher.locator('[data-login-role=student] svg').count(),1);
    assert.equal(await teacher.locator('#auth-role-title').innerText(),'Welcome to WizPractice');
    await assertAcademicVisuals(teacher);await capture(teacher,'roles-choice-en-desktop.png');
    await teacher.locator('#auth-lang-toggle-btn').click();await teacher.mouse.move(20,80);
    await capture(teacher,'roles-choice-desktop.png');
    const trail=teacher.locator('.auth-trail').nth(2),r=await trail.boundingBox();await teacher.mouse.move(r.x+r.width/2,r.y+r.height/2);
    await teacher.waitForFunction(()=>document.querySelectorAll('.auth-trail.is-near').length>0);
    assert.ok(await teacher.locator('.auth-trail.is-near').first().evaluate(e=>Number(e.style.getPropertyValue('--stretch'))>1.1));
    await capture(teacher,'roles-trails-hover.png');
    await teacher.locator('[data-login-role=teacher]').click();
    assert.ok(await teacher.locator('.auth-shell').evaluate(e=>e.getAnimations().some(a=>a.effect.getTiming().duration===320)));
    await settle(teacher);await capture(teacher,'roles-teacher-login.png');
    await teacher.locator('#switch-auth-role').click();await register(teacher,'teacher','teacher_01');
    await teacher.reload();assert.equal(await teacher.locator('#account-role-badge').textContent(),'老师');
    await student.goto(base);await register(student,'student','student_01');
    assert.equal((await (await sc.request.get(base+'/api/auth/status')).json()).role,'student');
    await student.locator('#nav-groups').click();await student.locator('#group-view .exam-empty').waitFor();
    assert.equal(await student.locator('#group-view').getByRole('button',{name:'创建小组',exact:true}).count(),0);
    assert.equal((await sc.request.post(base+'/api/groups',{data:{name:'not allowed'}})).status(),403);
    await student.locator('#nav-exams').click();await eb(student,'加入考试').waitFor();
    assert.deepEqual(await student.locator('#exam-view [role=tab]').allTextContents(),['我参与的']);
    assert.equal((await sc.request.post(base+'/api/exams',{data:{bank_id:'fake'}})).status(),403);
    await capture(student,'roles-student-exams.png');
    // A teacher creates and reviews an exam; no paid AI and no real uploads.
    const bank=(await (await tc.request.post(base+'/_test/seed_bank')).json()).bank_id;
    let exam=(await (await tc.request.post(base+'/api/exams',{data:{bank_id:bank}})).json()).exam;
    exam=(await (await tc.request.post(base+`/api/exams/${exam.id}/prepare`,{data:{index:0,version:exam.version}})).json()).exam;
    exam=(await (await tc.request.post(base+`/api/exams/${exam.id}/publish`,{data:{version:exam.version,reviewed:true}})).json()).exam;
    await student.goto(exam.share_url);await eb(student,'开始训练').click();await student.locator('#exam-view textarea').fill('0°C');await eb(student,'提交并锁定答案').click();await student.locator('.exam-grade').waitFor();
    await eb(student,'完成考试 · 查看总成绩').click();await student.locator('.exam-score').waitFor();
    await teacher.locator('#nav-exams').click();await teacher.locator('#exam-view').getByRole('tab',{name:'草稿与已发布',exact:true}).click();
    assert.equal(await eb(teacher,'加入考试').count(),0);
    await teacher.locator('.exam-owned-row').getByRole('button',{name:'展开',exact:true}).click();await teacher.locator('.exam-roster-table').getByRole('button',{name:'student_01',exact:true}).click();
    await teacher.locator('#exam-view').getByRole('heading',{name:'学生答案',exact:true}).waitFor();assert.equal(await teacher.locator('#exam-view').getByText('0°C',{exact:true}).count(),2,'Student answer and reference answer are both shown');
    await capture(teacher,'roles-student-answer-review.png');
    await teacher.setViewportSize({width:390,height:844});await capture(teacher,'roles-review-mobile.png');assert.ok(await teacher.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
    await teacher.locator('#logout-btn').click();await teacher.locator('#auth-role-choice').waitFor();await capture(teacher,'roles-choice-mobile.png');
    await assertAcademicVisuals(teacher);await teacher.locator('#auth-lang-toggle-btn').click();await assertAcademicVisuals(teacher);await capture(teacher,'roles-choice-en-mobile.png');await teacher.locator('#auth-lang-toggle-btn').click();
    assert.ok(await teacher.locator('#auth-screen').evaluate(e=>e.scrollWidth<=innerWidth));
    await teacher.locator('[data-login-role=student]').click();await teacher.locator('#login-username').fill('teacher_01');await teacher.locator('#login-password').fill('password-123');await teacher.locator('#login-form [type=submit]').click();await teacher.locator('#login-message').filter({hasText:'身份与当前入口不符'}).waitFor();
    await teacher.locator('#switch-auth-role').click();await teacher.emulateMedia({reducedMotion:'reduce'});await teacher.locator('[data-login-role=teacher]').focus();assert.equal(await teacher.locator('[data-login-role=teacher] .auth-entry-arrow').evaluate(e=>e.getAnimations().length),0);await teacher.locator('[data-login-role=teacher]').click();assert.equal(await teacher.locator('.auth-shell').evaluate(e=>e.getAnimations().length),0);
    await teacher.locator('#login-password').fill('password-123');await teacher.locator('#login-form [type=submit]').click();await teacher.locator('.bank-app').waitFor({state:'visible'});assert.equal(await teacher.locator('#account-role-badge').textContent(),'老师');
    assert.deepEqual(errors,[]);console.log('PASS: public teacher/student registration without invitation codes, saved roles, distinct menus, backend permissions, wrong-entrance protection, teacher answer review, narrow/tall cards, pointer trails, mobile and reduced motion; no real accounts/mail/AI');
  }finally{await browser.close();fixture.kill();}
})().catch(e=>{console.error(e);console.error(logs.slice(-2400));fixture.kill();process.exitCode=1;});
