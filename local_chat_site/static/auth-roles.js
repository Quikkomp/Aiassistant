/* Choosing an entrance never grants privileges; the server returns the saved role. */
(() => {
  const $=id=>document.getElementById(id), zh=()=>currentLang==='zh';
  const W={welcome:['欢迎来到智练 WizPractice','Welcome to WizPractice'],intro:['选择你的身份，进入属于你的学习与教学空间。','Choose your space for teaching or learning.'],teacher:['我是老师',"I’m a teacher"],student:['我是学生',"I’m a student"],teacherIntro:['从课程资料到课堂考试，轻松了解每一位学生的进步。','From course materials to exams, understand every student’s progress.'],studentIntro:['加入老师的考试，在练习与 AI 反馈中找到下一步方向。','Join your teacher’s exams and find your next step with AI feedback.'],teacherFirst:['创建并分享考试','Create and share exams'],teacherSecond:['管理班级与学习小组','Manage classes and groups'],teacherThird:['查看成绩、逐题答卷与薄弱点','Review marks, answers and weak points'],studentFirst:['加入班级并参加考试','Join classes and take exams'],studentSecond:['回顾自己的作答与成绩','Review your answers and marks'],studentThird:['获取 AI 分析与巩固练习','Get AI analysis and extra practice'],teacherGo:['进入教师空间','Teacher sign in'],studentGo:['进入学生空间','Student sign in'],note:['老师和学生均可直接注册，无需邀请码。','Teachers and students can register directly. No invitation code.'],switchRole:['← 切换身份','← Switch role'],teacherJourney:['让教学有迹可循','A clearer teaching journey'],studentJourney:['让每一次练习看见进步','Small steps. Real progress.'],teacherStep1:['创建试题','Create'],teacherStep2:['审核发布','Review & share'],teacherStep3:['洞察学情','Understand'],studentStep1:['专注作答','Answer'],studentStep2:['获得反馈','Reflect'],studentStep3:['巩固提升','Improve']};
  let selected='student', animation=null, busy=false;
  let actual=['teacher','student'].includes(document.body.dataset.accountRole)?document.body.dataset.accountRole:(document.body.classList.contains('auth-open')?'guest':'teacher');
  function translate(){
    document.querySelectorAll('[data-role-i18n]').forEach(e=>e.textContent=W[e.dataset.roleI18n][zh()?0:1]);
    const teacher=selected==='teacher', label=zh()?(teacher?'老师':'学生'):(teacher?'Teacher':'Student');
    $('auth-selected-role').textContent=zh()?label+'身份':label+' account';
    document.querySelector('#login-form h2').textContent=zh()?label+'登录':label+' sign in';
    document.querySelector('#register-form h2').textContent=zh()?'注册'+label+'账号':'Create a '+label.toLowerCase()+' account';
    document.querySelector('#register-form p').textContent=zh()?'正常注册即可使用所选身份，无需邀请码。':'Register directly for this role. No invitation code required.';
    document.body.dataset.accountRole=actual;
    const badge=$('account-role-badge');if(badge)badge.textContent=actual==='guest'?'':(zh()?(actual==='teacher'?'老师':'学生'):(actual==='teacher'?'Teacher':'Student'));
  }
  function choose(role,animate=true){
    if(busy||!['teacher','student'].includes(role))return;
    selected=role;const source=document.querySelector('.auth-role-card.'+role).getBoundingClientRect();
    animation?.cancel();$('auth-role-choice').hidden=true;const shell=document.querySelector('#auth-screen .auth-shell');shell.hidden=false;
    document.body.classList.remove('auth-choosing');document.body.dataset.loginIdentity=role;setAuthMode('login');translate();
    if(animate&&!matchMedia('(prefers-reduced-motion: reduce)').matches){
      const dest=shell.getBoundingClientRect();shell.style.transformOrigin='0 0';
      animation=shell.animate([{transform:`translate(${source.x-dest.x}px,${source.y-dest.y}px) scale(${source.width/dest.width},${source.height/dest.height})`,opacity:.6},{transform:'none',opacity:1}],{duration:320,easing:'cubic-bezier(.22,.75,.24,1)'});
    }
    $('auth-screen').scrollTop=0;$('login-username').focus({preventScroll:true});
  }
  function reset(){
    if(busy)return;
    animation?.cancel();window.recoveryUI?.reset();
    $('auth-role-choice').hidden=false;document.querySelector('#auth-screen .auth-shell').hidden=true;document.body.classList.add('auth-choosing');
    $('auth-screen').scrollTop=0;
    for(const id of ['login-password','register-password','register-confirm'])$(id).value='';
    setAuthMessage('login-message','');setAuthMessage('register-message','');
  }
  function apply(role){actual=['teacher','student'].includes(role)?role:'guest';translate();}
  function initTrails(){
    const layer=$('auth-role-backdrop'), trails=[];
    for(let i=0;i<32;i++){
      const line=document.createElement('span');line.className='auth-trail';
      line.style.left=((i*29)%112-12)+'%';line.style.top=((i*23)%100+10)+'%';
      line.style.setProperty('--length',(160+(i*37)%240)+'px');layer.append(line);trails.push(line);
    }
    let frame=0, point=null;
    const restore=()=>{point=null;for(const line of trails){line.style.removeProperty('--stretch');line.classList.remove('is-near');}};
    const update=()=>{frame=0;if(!point)return;const rects=trails.map(line=>line.getBoundingClientRect());trails.forEach((line,i)=>{const r=rects[i],dx=point.x-(r.left+r.width/2),dy=point.y-(r.top+r.height/2),near=Math.max(0,1-Math.hypot(dx,dy)/200);line.style.setProperty('--stretch',(1+near*.65).toFixed(3));line.classList.toggle('is-near',near>.1);});};
    $('auth-screen').addEventListener('pointermove',event=>{
      if(!document.body.classList.contains('auth-choosing')||event.pointerType==='touch'||!matchMedia('(hover:hover) and (prefers-reduced-motion:no-preference)').matches)return;
      point={x:event.clientX,y:event.clientY};if(!frame)frame=requestAnimationFrame(update);
    },{passive:true});
    $('auth-screen').addEventListener('pointerleave',restore);
    matchMedia('(prefers-reduced-motion:reduce)').addEventListener('change',restore);
  }
  function lock(value){busy=value;document.querySelectorAll('#switch-auth-role,#auth-screen [data-auth-mode],#guest-btn,#forgot-password-btn').forEach(e=>e.disabled=value);document.querySelector('#auth-screen .auth-card').setAttribute('aria-busy',String(value));}
  window.roleUI={choose,reset,translate,apply,lock,get selected(){return selected;},get current(){return actual;},isTeacher:()=>actual==='teacher'};
  document.addEventListener('DOMContentLoaded',()=>{
    initTrails();
    window.addEventListener('resize',()=>animation?.cancel(),{passive:true});
    document.querySelectorAll('[data-login-role]').forEach(b=>b.addEventListener('click',()=>choose(b.dataset.loginRole)));
    $('switch-auth-role').addEventListener('click',reset);
    const chip=$('account-chip');if(chip&&!$('account-role-badge')){const badge=document.createElement('span');badge.id='account-role-badge';badge.className='account-role-badge';chip.prepend(badge);}
    translate();
    if(document.body.classList.contains('auth-open')){reset();if(/^\/(exam|group)\/[a-f0-9]+/.test(location.pathname))choose('student',false);}
    else {document.querySelector('#auth-screen .auth-shell').hidden=false;$('auth-role-choice').hidden=true;}
  });
})();
