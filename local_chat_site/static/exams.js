/* Teacher-reviewed snapshots and single-attempt training, independent of personal practice. */
(() => {
  const $ = id => document.getElementById(id);
  const W = {
    exams:['考试','Exams'], subtitle:['把你的题库分享给学生，让训练与反馈连成一条学习路径。','Share teacher-reviewed questions and guide students from practice to feedback.'],
    join:['加入考试','Join exam'], banks:['我的题库','My question sets'], published:['草稿与已发布','Drafts & published'], joined:['我参与的','My attempts'],
    login:['考试需要登录账号；每个账号只能参加同一场考试一次。','Sign in to use exams. Each account has one attempt per exam.'],
    noBanks:['题库还没有题目，请先到题库创建一组题目。','Create a question set in your library first.'], empty:['这里暂时没有记录。','No records yet.'],
    edit:['编辑考试','Edit exam'], title:['考试名称','Exam name'], desc:['考试说明（选填）','Instructions (optional)'], save:['保存草稿','Save draft'], publish:['发布','Publish'],
    back:['← 返回考试','← Back to exams'], question:['题目','Question'], answer:['参考答案','Reference answer'], explanation:['解析','Explanation'], rubric:['评分要点','Marking criteria'], knowledge:['知识点','Knowledge point'],
    type:['题型','Type'], points:['分值','Points'], fill_blank:['填空题','Fill in the blank'], multiple_choice:['选择题','Multiple choice'], short_answer:['简答题','Short answer'],
    ai:['AI 补全当前题','AI draft for this question'], aiAll:['AI 补全缺失答案','AI draft missing answers'], saved:['草稿已保存。','Draft saved.'], ready:['已填写','Ready'], missing:['待完善','Incomplete'],
    teacherNote:['默认总分 100 分，可调整每题分值。AI 答案仅为草稿，请审核题干、答案、解析与评分要点；发布后该版本不可修改。','Default total: 100 points. Adjust marks as needed. Review AI-drafted questions, answers, explanations and criteria before publishing. Published versions are immutable.'],
    draft:['草稿','Draft'], closed:['已关闭','Closed'], active:['进行中','In progress'], completed:['已完成','Completed'], pubStatus:['已发布','Published'],
    share:['分享考试','Share exam'], copy:['复制链接','Copy link'], copied:['链接已复制。','Link copied.'], manualCopy:['无法自动复制，请选中链接手动复制。','Select the link and copy it manually.'], close:['关闭','Close'], closeExam:['停止新生加入','Stop new attempts'], closeConfirm:['关闭后不能再开始新的作答，已开始的学生仍可继续。确认关闭？','New attempts will be stopped. Existing students can continue. Close this exam?'],
    review:['我已审核所有题目的答案、解析和评分要点。','I have reviewed every answer, explanation and marking criterion.'], confirmPublish:['确认发布','Confirm publication'], qrNote:['学生扫码或打开链接后登录即可参加。跨设备访问需要网站部署在可访问的地址，不能分享 localhost 链接。','Students scan or open this link and sign in. For other devices, deploy on a reachable host; localhost links cannot be shared.'],
    paste:['粘贴老师分享的链接','Paste the teacher’s exam link'], open:['打开考试','Open exam'], badLink:['请输入有效的考试分享链接。','Enter a valid exam share link.'], start:['开始训练','Start training'], resume:['继续作答','Continue attempt'], result:['查看成绩','View result'],
    once:['每个账号仅有一次作答机会。每题提交后锁定答案，刷新可以续答；当前题批改完成后可查看解析并进行巩固，巩固练习不计入考试得分。','One attempt per account. Each submitted answer is locked; reload to resume. Explanations and unscored consolidation unlock after grading.'],
    teacher:['发布者','Teacher'], count:['题','questions'], total:['总分','Total points'], submitted:['已提交','Submitted'], yourAnswer:['你的答案','Your answer'], submit:['提交并锁定答案','Submit & lock answer'], retry:['重试批改','Retry grading'], pending:['答案已锁定，正在批改。可以稍后刷新；若批改中断，请重试原答案。','Your answer is locked. Grading is pending. Reload later, or retry the same answer if interrupted.'],
    locked:['这道题已提交，原答案不能再修改。','This answer is submitted and cannot be edited.'], required:['请先填写答案。','Enter your answer first.'], finish:['完成考试 · 查看总成绩','Finish & view score'], prev:['上一题','Previous'], next:['下一题','Next'], feedback:['批改反馈','Feedback'],
    learn:['讲解、追问与巩固练习','Explanation & consolidation'], understood:['我理解了','I understand'], unclear:['我还不理解','Still unclear'], detailed:['详细讲解','Explain further'], ask:['问 AI','Ask AI'], similar:['生成类似题','Similar question'], questionPrompt:['输入你的疑问，或提交类似题的答案请求讲解…','Ask a question, or submit your consolidation answer for guidance…'],
    practiceNote:['巩固练习仅用于学习，不改变原题得分。','Consolidation is unscored and does not change exam marks.'], supportSaved:['理解状态已记录。','Understanding recorded.'], results:['考试成绩','Exam results'], score:['得分','Score'], weaknesses:['薄弱点讲解与复习建议','Weaknesses & revision guidance'], generateReport:['生成薄弱点讲解','Generate study report'], reportLoading:['成绩已保存，正在生成薄弱点讲解…','Score saved. Preparing study guidance…'],
    allDone:['全部题目已完成，可查看成绩。','All questions are graded. View your score.'], loading:['加载中…','Loading…'], working:['正在处理，请稍候…','Working…'], students:['学生完成情况','Student progress'], noneStudents:['还没有学生开始作答。','No student has started yet.'], newExam:['新建考试副本','New exam copy'],
    analytics:['成绩分析','Results analytics'], started:['已开始人数','Started'], completedCount:['已完成人数','Completed'], average:['平均分','Average'], passRate:['及格率','Pass rate'], completionRate:['完成率','Completion rate'], highest:['最高分','Highest'], lowest:['最低分','Lowest'], median:['中位数','Median'], distribution:['成绩分布','Score distribution'], accuracy:['逐题正确率','Question accuracy'], groupWeakness:['薄弱知识点','Group weaknesses'], correct:['正确','Correct'], partial:['部分正确','Partial'], wrong:['错误','Incorrect'], mastery:['平均得分率','Mean credit'], refresh:['刷新数据','Refresh'], analyticsNote:['仅统计已完成考试的成绩，统一折算为百分制；及格线为 60 分。薄弱知识点按平均得分率低于 80% 展示，名单显示最近 200 人。','Completed attempts only; marks normalized to 100, pass threshold 60. Knowledge points below 80% mean credit are listed. Roster shows the latest 200 students.'], noStats:['还没有已完成的考试，暂不生成成绩分布。','No completed attempts yet. Score distribution is not available.'],
    participants:['参与学生','Participants'], finishedStudents:['已完成','Completed'], gradedCount:['已批改作答','Graded answers'], averageShort:['平均分 / 100','Average / 100'], expand:['展开','Expand'], collapse:['收起','Collapse'], studentName:['学生','Student'], progress:['答题进度','Progress'], score100:['成绩 / 100','Score / 100'], submittedAt:['完成时间','Completed at'], viewExam:['查看试卷','View paper'], rowNote:['平均分仅统计已完成考试；数据量为已批改的题目作答数。展开可查看最近 200 位参与学生。','Average includes completed attempts only; data volume counts graded question answers. Expand to see the latest 200 participants.'],
  };
  const zh = () => currentLang === 'zh';
  const t = key => W[key]?.[zh()?0:1] || key;
  let epoch=0, operation=0, mode='catalog', tab='banks', draft=null, index=0, attempt=null, info=null, sharedToken='', dialog=null, supportText='', busy=false;
  let catalog={owned:[],joined:[]}, banks=[];
  let analytics=null;
  const expandedExams=new Set(), rosterCache=new Map();
  let lastContentKey='';
  const node=(tag,value='',attrs={})=>{
    const el=document.createElement(tag); el.textContent=value;
    for(const [key,val] of Object.entries(attrs)) el.setAttribute(key,String(val));
    return el;
  };
  const message=(value='',error=false)=>{
    $('exam-message').textContent=value; $('exam-message').hidden=!value;
    $('exam-message').classList.toggle('is-error',error);
  };
  const button=(label,handler,primary=false)=>{
    const el=node('button',label,{type:'button',class:'exam-btn'+(primary?' primary':'')});
    el.addEventListener('click',()=>run(handler,el)); return el;
  };
  async function api(url,data,method='POST') {
    const stamp=epoch;
    const res=await fetch(url,data===undefined?{}:{method,headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
    const obj=await res.json();
    if(stamp!==epoch) throw Object.assign(new Error('View changed'),{quiet:true});
    if(!res.ok||!obj.ok) throw new Error(obj.msg||'Request failed');
    return obj;
  }
  async function run(work,source) {
    if(busy) return;
    busy=true;
    const owner=++operation;
    const controls=[...document.querySelectorAll('#exam-view button,#exam-view input,#exam-view textarea,#exam-view select,.exam-dialog button,.exam-dialog input')].map(el=>[el,el.disabled]);
    controls.forEach(([el])=>el.disabled=true);
    if(source) source.setAttribute('aria-busy','true');
    try {message(t('working')); await work();}
    catch(error) {if(owner===operation&&!error.quiet) message(error.message,true);}
    finally {if(owner===operation)busy=false; controls.forEach(([el,disabled])=>{if(el.isConnected) el.disabled=disabled;}); source?.removeAttribute('aria-busy');}
  }
  function animate() {
    if(!matchMedia('(prefers-reduced-motion: reduce)').matches) $('exam-content').animate([{opacity:.55,transform:'translateY(3px)'},{opacity:1,transform:'translateY(0px)'}],{duration:180,easing:'ease-out'});
  }
  function enter() {
    epoch++;
    window.bankUI?.scheduleSave(true);
    $('bank-library-view').hidden=true; $('bank-practice-view').hidden=true; $('exam-view').hidden=false;
    for(const id of ['nav-library','nav-practice','nav-exams']) {$(id).classList.toggle('active',id==='nav-exams'); $(id).removeAttribute('aria-current');}
    $('nav-exams').setAttribute('aria-current','page'); message();
  }
  function heading(title,subtitle,actions=[]) {
    const head=node('div','',{class:'exam-heading'}), copy=node('div');
    copy.append(node('h1',title),node('p',subtitle)); const row=node('div','',{class:'exam-actions'}); row.append(...actions); head.append(copy,row); return head;
  }
  function card() {return node('section','',{class:'exam-card'});}
  function field(label,value,handler,{tag='input',type='text',disabled=false}={}) {
    const wrap=node('label',label,{class:'exam-field'}), input=node(tag);
    if(tag==='input') input.type=type;
    input.value=value??''; input.disabled=disabled; input.addEventListener('input',()=>handler(input.value)); wrap.append(input); return wrap;
  }
  function content(...children) {
    $('exam-content').replaceChildren(...children);
    const key=mode+((mode==='attempt'||mode==='editor')?`:${index}`:'');
    if(key!==lastContentKey) window.scrollTo({top:0,behavior:'instant'});
    lastContentKey=key; animate();
  }
  function authenticated() {return !$('account-chip').classList.contains('hidden') && !!$('account-name').textContent.trim();}
  async function loadCatalog() {
    enter(); mode='catalog';
    if(!authenticated()) {content(heading(t('exams'),t('subtitle')),node('p',t('login'),{class:'exam-notice'})); return;}
    message(t('loading'));
    const [sets,list]=await Promise.all([api('/api/question_sets'),api('/api/exams')]);
    banks=sets.banks; catalog=list; expandedExams.clear();rosterCache.clear();renderCatalog(); message();
  }
  function renderCatalog() {
    const tabs=node('div','',{class:'exam-tabs',role:'tablist'}), grid=node('div','',{class:'exam-set-grid',role:'tabpanel'});
    for(const key of ['banks','published','joined']) {
      const btn=node('button',t(key),{type:'button',class:'exam-tab',role:'tab','aria-selected':String(tab===key)});
      btn.addEventListener('click',()=>{if(!busy){tab=key;renderCatalog();message();}}); tabs.append(btn);
    }
    const rows=tab==='banks'?banks:tab==='published'?catalog.owned:catalog.joined;
    if(tab==='published') {
      const list=node('div','',{class:'exam-owned-list',role:'tabpanel'});
      rows.forEach(row=>list.append(ownedExamRow(row)));
      content(heading(t('exams'),t('subtitle'),[button(t('join'),openJoin,true)]),tabs,node('p',t('rowNote'),{class:'exam-list-note'}),rows.length?list:node('div',t('empty'),{class:'exam-empty'}));return;
    }
    for(const row of rows) {
      const tile=node('button','',{class:'exam-set',type:'button'});
      tile.append(node('span','▤',{class:'exam-set-icon','aria-hidden':'true'}),node('strong',row.title),node('small',tab==='banks'?`${row.questions.length} ${t('count')} · ${t('edit')}`:t(row.status==='published'?'pubStatus':row.status)));
      tile.addEventListener('click',()=>run(async()=>{
        if(tab==='banks') {draft=(await api('/api/exams',{bank_id:row.id})).exam;index=0;mode='editor';renderEditor();message();}
        else if(tab==='published') {draft=(await api(`/api/exams/${row.id}`)).exam;index=0;mode='editor';renderEditor();message();}
        else {attempt=(await api(`/api/exam_attempts/${row.id}`)).attempt;index=0;supportText='';mode=attempt.status==='completed'?'result':'attempt';render();message();}
      })); grid.append(tile);
    }
    content(heading(t('exams'),t('subtitle'),[button(t('join'),openJoin,true)]),tabs,rows.length?grid:node('div',t(tab==='banks'?'noBanks':'empty'),{class:'exam-empty'}));
  }
  async function openOwnedExam(row,withAnalytics=false) {
    draft=(await api(`/api/exams/${row.id}`)).exam;index=0;
    if(withAnalytics)await showStudents();
    else {mode='editor';renderEditor();message();}
  }
  function ownedExamRow(row) {
    const item=node('section','',{class:'exam-owned-row','aria-label':row.title}), head=node('div','',{class:'exam-owned-head'});
    const title=button(row.title,()=>openOwnedExam(row));title.className='exam-owned-title';
    const identity=node('div','',{class:'exam-owned-identity'}), meta=node('div','',{class:'exam-owned-meta'});
    meta.append(node('span',t(row.status==='published'?'pubStatus':row.status),{class:`exam-status ${row.status}`}),node('span',`${row.question_count} ${t('count')}`));identity.append(title,meta);
    const metrics=node('div','',{class:'exam-owned-metrics'});
    const updateMetrics=()=>{
      metrics.replaceChildren();
      for(const [key,label] of [['started','participants'],['completed','finishedStudents'],['graded_count','gradedCount'],['average','averageShort']]) {
        const metric=node('div','',{class:'exam-owned-metric'});metric.append(node('span',t(label)),node('strong',row[key]===null?'—':String(row[key]??0)));metrics.append(metric);
      }
    };
    updateMetrics();
    const panelId=`exam-roster-${row.id}`, panel=node('div','',{id:panelId,class:'exam-roster-panel',role:'region','aria-label':`${row.title} · ${t('students')}`});
    panel.hidden=true;
    const actions=node('div','',{class:'exam-owned-actions'}), edit=button(t(row.status==='draft'?'edit':'viewExam'),()=>openOwnedExam(row));
    const toggle=button('',async()=>{
      if(expandedExams.has(row.id)) {
        expandedExams.delete(row.id);updateToggle();
        if(!matchMedia('(prefers-reduced-motion: reduce)').matches) {
          const effect=panel.animate([{height:panel.offsetHeight+'px',opacity:1},{height:'0px',opacity:0}],{duration:160,easing:'ease-out'});
          await effect.finished;
        }
        panel.hidden=true;
      } else {
        if(!rosterCache.has(row.id))await loadRoster();
        fillRoster();panel.hidden=false;expandedExams.add(row.id);updateToggle();
        if(!matchMedia('(prefers-reduced-motion: reduce)').matches)panel.animate([{height:'0px',opacity:0},{height:panel.offsetHeight+'px',opacity:1}],{duration:180,easing:'ease-out'});
      }
      message();
    });
    toggle.classList.add('exam-expand');toggle.setAttribute('aria-controls',panelId);
    function updateToggle() {
      const open=expandedExams.has(row.id);toggle.setAttribute('aria-expanded',String(open));toggle.replaceChildren(node('span',t(open?'collapse':'expand')),node('span','⌄',{class:'exam-expand-icon','aria-hidden':'true'}));
    }
    async function loadRoster() {
      const data=(await api(`/api/exams/${row.id}/analytics`)).analytics;rosterCache.set(row.id,data);
      for(const key of ['started','completed','graded_count','average'])row[key]=data[key];updateMetrics();
    }
    function fillRoster() {
      const data=rosterCache.get(row.id), top=node('div','',{class:'exam-roster-heading'}), controls=node('div','',{class:'exam-actions'});
      controls.append(button(t('refresh'),async()=>{await loadRoster();fillRoster();message();}));
      if(row.status!=='draft')controls.append(button(t('analytics'),()=>openOwnedExam(row,true)));
      top.append(node('h2',t('students')),controls);panel.replaceChildren(top);
      if(!data.students.length) {panel.append(node('p',t('noneStudents'),{class:'exam-roster-empty'}));return;}
      const scroll=node('div','',{class:'exam-roster-scroll'}), table=node('table','',{class:'exam-roster-table'}), thead=node('thead'), tr=node('tr'), tbody=node('tbody');
      for(const label of ['studentName','progress','score100','submittedAt'])tr.append(node('th',t(label),{scope:'col'}));thead.append(tr);
      for(const student of data.students) {
        const entry=node('tr'), identity=node('td');identity.append(node('strong',student.username),node('span',t(student.status),{class:`exam-student-status ${student.status}`}));
        const score=student.score===null?'—':String(Number((student.score/data.total*100).toFixed(1)));
        const completedAt=student.completed_at?new Date(student.completed_at).toLocaleString(zh()?'zh-CN':'en-GB',{year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit'}):'—';
        entry.append(identity,node('td',`${student.done} / ${row.question_count}`),node('td',score,{class:'exam-roster-score'}),node('td',completedAt));tbody.append(entry);
      }
      table.append(thead,tbody);scroll.append(table);panel.append(scroll);
    }
    updateToggle();actions.append(edit,toggle);head.append(identity,metrics,actions);item.append(head,panel);
    if(expandedExams.has(row.id)&&rosterCache.has(row.id)) {fillRoster();panel.hidden=false;}
    return item;
  }
  async function saveDraft() {
    draft=(await api(`/api/exams/${draft.id}`,{title:draft.title,description:draft.description,questions:draft.questions,version:draft.version},'PUT')).exam;
  }
  async function prepare(all=false) {
    const stamp=epoch;
    await saveDraft();
    const targets=all?draft.questions.map((q,i)=>!q.answer||!q.explanation||!q.rubric?i:-1).filter(i=>i>=0):[index];
    try {
      for(let n=0;n<targets.length;n++) {
        message(`${t('working')} ${n+1} / ${targets.length}`);
        draft=(await api(`/api/exams/${draft.id}/prepare`,{index:targets[n],version:draft.version})).exam;
      }
    } finally {if(stamp===epoch)renderEditor();}
    message(zh()?'AI 草稿已保存，请审核后发布。':'AI draft saved. Review before publishing.');
  }
  function renderEditor() {
    const editing=draft.status==='draft', q=draft.questions[index], layout=node('div','',{class:'exam-editor-layout'}), outline=card(); outline.classList.add('exam-outline');
    const actions=editing?[button(t('save'),async()=>{await saveDraft();renderEditor();message(t('saved'));}),button(t('publish'),openPublish,true)]:[button(t('share'),showShare,true),button(t('analytics'),showStudents)];
    if(draft.status==='published') actions.push(button(t('closeExam'),async()=>{if(confirm(t('closeConfirm'))){draft=(await api(`/api/exams/${draft.id}/close`,{})).exam;renderEditor();message();}}));
    const meta=card();
    meta.append(field(t('title'),draft.title,v=>draft.title=v,{disabled:!editing}),field(t('desc'),draft.description,v=>draft.description=v,{disabled:!editing}),node('p',t('teacherNote'),{class:'exam-subtle'}));
    draft.questions.forEach((item,i)=>{
      const btn=node('button',`${t('question')} ${i+1}`,{type:'button',class:i===index?'selected':'','aria-current':i===index?'true':'false'});
      btn.append(node('small',t(item.answer&&item.explanation&&item.rubric?'ready':'missing'),{class:item.answer&&item.explanation&&item.rubric?'ready':''}));
      btn.addEventListener('click',()=>{if(!busy){index=i;renderEditor();message();}}); outline.append(btn);
    });
    const detail=card();detail.append(node('h2',`${t('question')} ${index+1}`));
    if(editing) detail.append(node('div','',{class:'exam-actions'}));
    if(editing) detail.lastChild.append(button(t('ai'),()=>prepare()),button(t('aiAll'),()=>prepare(true)));
    detail.append(field(t('question'),q.text,v=>q.text=v,{tag:'textarea',disabled:!editing}));
    const row=node('div','',{class:'exam-fields-row'}), types=node('label',t('type'),{class:'exam-field'}), select=node('select'); select.disabled=!editing;
    for(const kind of ['fill_blank','multiple_choice','short_answer']) {const option=node('option',t(kind),{value:kind});option.selected=q.type===kind;select.append(option);}
    select.addEventListener('change',()=>q.type=select.value); types.append(select);
    row.append(types,field(t('points'),q.points,v=>q.points=Number(v),{type:'number',disabled:!editing}));detail.append(row);
    for(const key of ['answer','explanation','rubric','knowledge']) detail.append(field(t(key),q[key],v=>q[key]=v,{tag:key==='knowledge'?'input':'textarea',disabled:!editing}));
    layout.append(outline,detail);
    content(button(t('back'),loadCatalog),heading(draft.title,t(editing?'draft':draft.status==='published'?'pubStatus':'closed'),actions),meta,layout);
  }
  function modal(title) {
    dialog?.remove();dialog=node('dialog','',{class:'exam-dialog'});
    const head=node('div','',{class:'exam-dialog-head'});
    const close=node('button','×',{type:'button',class:'exam-btn','aria-label':t('close')});close.addEventListener('click',()=>{if(!busy) dialog.close();});
    head.append(node('h2',title),close);dialog.append(head);document.body.append(dialog);
    dialog.addEventListener('cancel',e=>{if(busy)e.preventDefault();});dialog.showModal();return dialog;
  }
  async function openPublish() {
    await saveDraft(); renderEditor(); message();
    const box=modal(t('publish')), label=node('label'), check=node('input','',{type:'checkbox'});
    label.append(check,document.createTextNode(' '+t('review')));
    const publish=button(t('confirmPublish'),async()=>{
      if(!check.checked) throw new Error(t('review'));
      draft=(await api(`/api/exams/${draft.id}/publish`,{version:draft.version,reviewed:true})).exam;
      dialog.close();renderEditor();showShare();message();
    },true);
    box.append(node('p',t('teacherNote'),{class:'exam-subtle'}),label,publish);
  }
  function showShare() {
    const box=modal(t('share')), img=node('img','',{class:'exam-qr',src:`/api/exams/${draft.id}/qr`,alt:zh()?'考试分享二维码':'Exam QR code'});
    const input=node('input','',{type:'text',readonly:'', 'aria-label':t('share')});input.value=draft.share_url;
    const feedback=node('p','',{class:'exam-subtle',role:'status'});
    box.append(img,input,button(t('copy'),async()=>{try{await navigator.clipboard.writeText(input.value);feedback.textContent=t('copied');}catch(_){input.select();feedback.textContent=t('manualCopy');}}),feedback,node('p',t('qrNote'),{class:'exam-subtle'}));
  }
  function openJoin() {
    const box=modal(t('join')), form=node('form'), label=node('label',t('paste')), input=node('input','',{type:'text',required:'',placeholder:'https://…/exam/…'});
    label.append(input);form.append(label);const submit=node('button',t('open'),{class:'exam-btn primary',type:'submit'});form.append(submit);
    form.addEventListener('submit',e=>{e.preventDefault();run(async()=>{
      let token=input.value.trim();
      if(!/^[a-f0-9]{48}$/.test(token)) {
        try {const url=new URL(token,location.origin);if(!['http:','https:'].includes(url.protocol))throw new Error();token=url.pathname.match(/^\/exam\/([a-f0-9]{48})\/?$/)?.[1]||'';}catch(_){token='';}
      }
      if(!token)throw new Error(t('badLink'));
      dialog.close();await openExam(token);
    },submit);});box.append(form);input.focus();message();
  }
  async function openExam(token) {
    enter();sharedToken=token;mode='intro';message(t('loading'));
    info=(await api(`/api/exams/shared/${token}`)).exam;renderIntro();message();
  }
  function renderIntro() {
    const intro=card(), action=button(t(info.attempt?(info.attempt.status==='completed'?'result':'resume'):'start'),async()=>{
      attempt=(await api(`/api/exams/shared/${sharedToken}/start`,{})).attempt;
      index=Math.max(0,attempt.questions.findIndex(q=>q.submission?.status!=='graded'));supportText='';mode=attempt.status==='completed'?'result':'attempt';render();message();
    },true);
    action.disabled=info.status==='closed'&&!info.attempt;
    intro.append(node('p',`${t('teacher')}：${info.teacher} · ${info.count} ${t('count')} · ${t('total')} ${info.total}`,{class:'exam-subtle'}),node('p',info.description,{class:'exam-text'}),node('p',t('once'),{class:'exam-notice'}),action);
    content(button(t('back'),loadCatalog),heading(info.title,t(info.status==='closed'?'closed':'exams')),intro);
  }
  function numberNav() {
    const nav=node('nav','',{class:'exam-number-nav','aria-label':t('question')});
    attempt.questions.forEach((q,i)=>{const b=node('button',String(i+1),{type:'button',class:(i===index?'selected ':'')+(q.submission?.status==='graded'?'done':''),'aria-current':i===index?'step':'false'});b.addEventListener('click',()=>{if(!busy){index=i;supportText='';mode='attempt';renderAttempt();message();}});nav.append(b);});return nav;
  }
  async function submitAnswer(value) {
    if(!value.trim())throw new Error(t('required'));
    if(!attempt.questions[index].submission)attempt.questions[index].submission={answer:value,status:'pending'};
    try {attempt=(await api(`/api/exam_attempts/${attempt.id}/answer`,{index,answer:value})).attempt;renderAttempt();message();}
    catch(error) {if(!error.quiet){attempt=(await api(`/api/exam_attempts/${attempt.id}`)).attempt;renderAttempt();}throw error;}
  }
  function learning(q) {
    const details=node('details','',{class:'exam-learning'});details.append(node('summary',t('learn')));
    if(!supportText) supportText=q.support?.at(-1)?.response||'';
    const actions=node('div','',{class:'exam-actions'}), result=node('div',supportText,{class:'exam-support-result exam-text',role:'status'});result.hidden=!supportText;
    const support=async(kind,messageText='')=>{
      const res=await api(`/api/exam_attempts/${attempt.id}/support`,{index,kind,message:messageText});supportText=res.text;q.support=[...(q.support||[]),{kind,message:messageText,response:res.text}];result.textContent=supportText;result.hidden=false;message();
    };
    for(const value of ['understood','unclear']) actions.append(button(t(value),async()=>{
      await api(`/api/exam_attempts/${attempt.id}/support`,{index,kind:'understanding',value});q.submission.understanding=value;message(t('supportSaved'));
      if(value==='unclear')await support('explain');
    }));
    actions.append(button(t('detailed'),()=>support('explain')),button(t('similar'),()=>support('similar')));
    const form=node('form','',{class:'exam-follow-up'}), input=node('input','',{placeholder:t('questionPrompt'),'aria-label':t('ask'),required:''}), ask=node('button',t('ask'),{type:'submit',class:'exam-btn'});
    form.append(input,ask);form.addEventListener('submit',e=>{e.preventDefault();run(()=>support('ask',input.value),ask);});
    details.append(actions,form,node('p',t('practiceNote'),{class:'exam-subtle'}),result);return details;
  }
  function renderAttempt() {
    const q=attempt.questions[index], sub=q.submission, finished=attempt.status==='completed';
    const done=attempt.questions.filter(item=>item.submission?.status==='graded').length;
    const body=card();body.append(node('p',`${t('question')} ${index+1} / ${attempt.questions.length} · ${q.points} ${t('points')}`,{class:'exam-subtle'}),node('p',q.text,{class:'exam-question-text'}));
    const label=node('label',t('yourAnswer'),{class:'exam-field'}), input=node('textarea', '',{'aria-label':t('yourAnswer')});input.value=sub?.answer||q.draftAnswer||'';input.disabled=!!sub||finished;input.addEventListener('input',()=>q.draftAnswer=input.value);label.append(input);body.append(label);
    if(!sub&&!finished)body.append(button(t('submit'),()=>submitAnswer(input.value),true));
    else if(sub?.status!=='graded'&&!finished) body.append(node('p',t('pending'),{class:'exam-notice'}),button(t('retry'),()=>submitAnswer(sub.answer),true));
    if(sub?.status==='graded') {
      const feedback=node('div','',{class:'exam-grade'});
      feedback.append(node('h3',`${t('score')} ${Number((sub.ratio*q.points).toFixed(2))} / ${q.points}`),node('p',sub.feedback,{class:'exam-text'}),node('h3',t('answer')),node('p',q.answer,{class:'exam-text'}),node('h3',t('explanation')),node('p',q.explanation,{class:'exam-text'}));
      body.append(node('p',t('locked'),{class:'exam-subtle'}),feedback,learning(q));
    }
    const actions=node('div','',{class:'exam-actions'});
    const prev=button(t('prev'),()=>{index--;supportText='';renderAttempt();message();});prev.disabled=index===0;
    const next=button(t('next'),()=>{index++;supportText='';renderAttempt();message();});next.disabled=index===attempt.questions.length-1;
    const complete=button(t(finished?'result':'finish'),async()=>{
      if(!finished)attempt=(await api(`/api/exam_attempts/${attempt.id}/complete`,{})).attempt;
      mode='result';renderResult();message();
      if(!attempt.report)await generateReport();
    },true);complete.disabled=!finished&&done!==attempt.questions.length;
    actions.append(prev,next,complete);
    content(button(t('back'),loadCatalog),heading(attempt.title,`${done} / ${attempt.questions.length} ${t('submitted')}`),numberNav(),body,actions);
  }
  async function generateReport() {
    message(t('reportLoading'));
    attempt=(await api(`/api/exam_attempts/${attempt.id}/report`,{})).attempt;renderResult();message();
  }
  function renderResult() {
    const summary=card(), score=node('div','',{class:'exam-score'});score.append(node('strong',String(attempt.score)),node('span',`/ ${Number(attempt.total.toFixed(2))}`));summary.append(node('h2',t('score')),score);
    attempt.questions.forEach((q,i)=>{
      const row=node('div','',{class:'exam-review-row'});
      row.append(button(`${t('question')} ${i+1}`,()=>{index=i;mode='attempt';supportText='';renderAttempt();message();}),node('span',`${Number((q.submission.ratio*q.points).toFixed(2))} / ${q.points}`));summary.append(row);
    });
    const report=card();report.append(node('h2',t('weaknesses')));
    if(attempt.report)report.append(node('p',attempt.report,{class:'exam-text'}));
    else report.append(button(t('generateReport'),generateReport,true));
    content(button(t('back'),loadCatalog),heading(attempt.title,t('results')),summary,report);
  }
  async function showStudents() {
    analytics=(await api(`/api/exams/${draft.id}/analytics`)).analytics;mode='analytics';renderAnalytics();message();
  }
  function renderAnalytics() {
    const stats=node('div','',{class:'exam-stats-grid'});
    const metric=(key,value,suffix='')=>{const el=card();el.append(node('p',t(key),{class:'exam-subtle'}),node('strong',value===null?'—':String(value)+suffix,{class:'exam-metric'}));return el;};
    stats.append(metric('started',analytics.started),metric('completedCount',analytics.completed),metric('average',analytics.average),metric('passRate',analytics.pass_rate,'%'));
    const details=node('p',`${t('completionRate')} ${analytics.completion_rate??'—'}% · ${t('highest')} ${analytics.highest??'—'} · ${t('lowest')} ${analytics.lowest??'—'} · ${t('median')} ${analytics.median??'—'}`,{class:'exam-notice'});
    const layout=node('div','',{class:'exam-analytics-grid'}), distribution=card();distribution.append(node('h2',t('distribution')));
    if(!analytics.completed)distribution.append(node('p',t('noStats'),{class:'exam-subtle'}));
    else {
      const chart=node('div','',{class:'exam-distribution','aria-label':t('distribution')}), max=Math.max(1,...analytics.distribution.map(b=>b.count));
      for(const bucket of analytics.distribution) {
        const column=node('div','',{class:'exam-dist-column'}), area=node('div','',{class:'exam-dist-area'}), bar=node('div','',{class:'exam-dist-bar'});
        bar.style.height=`${Math.max(2,bucket.count/max*100)}%`;area.append(bar);column.append(node('strong',String(bucket.count)),area,node('span',bucket.label));chart.append(column);
      }
      distribution.append(chart);
    }
    const weakness=card();weakness.append(node('h2',t('groupWeakness')));
    for(const item of analytics.weaknesses)weakness.append(node('p',`${item.knowledge} · ${t('mastery')} ${item.mastery}% · ${item.count} ${zh()?'次作答':'responses'}`,{class:'exam-text'}));
    if(!analytics.weaknesses.length)weakness.append(node('p',analytics.completed?(zh()?'当前没有平均得分率低于 80% 的知识点。':'No knowledge points below 80% mean credit.'):t('noStats'),{class:'exam-subtle'}));
    layout.append(distribution,weakness);
    const questions=card();questions.append(node('h2',t('accuracy')));
    for(const item of analytics.questions) {
      const row=node('div','',{class:'exam-review-row'});
      row.append(node('span',`${t('question')} ${item.index+1}${item.knowledge?' · '+item.knowledge:''}`),node('span',`${item.correct_rate===null?'—':item.correct_rate+'%'} · ${t('correct')} ${item.correct} / ${t('partial')} ${item.partial} / ${t('wrong')} ${item.wrong}`));questions.append(row);
    }
    const roster=card();roster.append(node('h2',t('students')));
    if(!analytics.students.length)roster.append(node('p',t('noneStudents'),{class:'exam-subtle'}));
    for(const row of analytics.students)roster.append(node('p',`${row.username} · ${t(row.status)} · ${row.done}/${draft.questions.length} · ${row.score===null?'—':row.score+' / '+Number(analytics.total.toFixed(2))}`,{class:'exam-review-row'}));
    content(button(t('back'),()=>{mode='editor';renderEditor();message();}),heading(draft.title,t('analytics'),[button(t('refresh'),showStudents)]),node('p',t('analyticsNote'),{class:'exam-notice'}),stats,details,layout,questions,roster);
  }
  function render() {if(mode==='catalog')renderCatalog();else if(mode==='editor')renderEditor();else if(mode==='intro')renderIntro();else if(mode==='attempt')renderAttempt();else if(mode==='analytics')renderAnalytics();else renderResult();}
  window.examUI={
    leave(){epoch++;operation++;busy=false;$('exam-view').hidden=true;$('nav-exams').classList.remove('active');$('nav-exams').removeAttribute('aria-current');dialog?.close();},
    reset(){this.leave();draft=null;attempt=null;info=null;supportText='';banks=[];catalog={owned:[],joined:[]};expandedExams.clear();rosterCache.clear();mode='catalog';lastContentKey='';busy=false;$('exam-content').replaceChildren();},
    translate(){document.querySelectorAll('[data-exam-i18n]').forEach(el=>el.textContent=t(el.dataset.examI18n));if(!$('exam-view').hidden&&!busy)render();},
    resumeLink(){const token=location.pathname.match(/^\/exam\/([a-f0-9]{48})\/?$/)?.[1];if(token&&authenticated())run(()=>openExam(token));},
  };
  document.addEventListener('DOMContentLoaded',()=>{
    $('nav-exams').addEventListener('click',()=>run(loadCatalog));window.examUI.translate();window.examUI.resumeLink();
  });
})();
