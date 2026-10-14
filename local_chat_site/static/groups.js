/* Learning groups: owner administration, explicit invites and reviewed exam delivery. */
(() => {
  const $=id=>document.getElementById(id), tr=(cn,en)=>currentLang==='zh'?cn:en;
  const words={groups:['小组','Groups'],create:['创建小组','Create group'],join:['加入小组','Join group'],members:['组员管理','Members'],exams:['已发布考试','Group exams'],results:['成绩统计','Results'],owner:['群主','Owner'],member:['组员','Member'],active:['正常','Active'],removed:['已移出','Removed'],assigned:['待参加','Not started'],completed:['已完成','Completed'],started:['作答中','In progress'],refresh:['刷新','Refresh'],back:['← 返回小组','← Back to groups'],close:['关闭','Close'],publish:['发布考试','Assign exam'],invite:['邀请组员','Invite members'],info:['查看信息','View details'],remove:['移出小组','Remove'],restore:['恢复组员','Restore'],name:['小组名称','Group name'],description:['小组说明','Description'],save:['保存','Save'],empty:['这里暂时没有记录。','No records yet.']};
  const t=k=>words[k]?.[currentLang==='zh'?0:1]||k;
  const n=(tag,value='',attrs={})=>{const e=document.createElement(tag);e.textContent=value;for(const [k,v] of Object.entries(attrs))e.setAttribute(k,String(v));return e;};
  let epoch=0,operation=0,busy=false,groups=[],current=null,tab='members',kind='list',preview=null,inviteToken='',dialog=null,lastKey='',results=null,resultExam='';
  const logged=()=>!$('account-chip').classList.contains('hidden')&&!!$('account-name').textContent.trim();
  function message(value='',error=false){
    const el=dialog?.open?dialog.querySelector('.group-dialog-message'):$('group-message');
    if(!el)return;el.textContent=value;el.hidden=!value;el.classList.toggle('is-error',error);
  }
  async function api(url,data,method='POST'){
    const stamp=epoch,res=await fetch(url,data===undefined?{}:{method,headers:{'Content-Type':'application/json'},body:JSON.stringify(data)}),obj=await res.json();
    if(stamp!==epoch)throw Object.assign(new Error('View changed'),{quiet:true});
    if(!res.ok||!obj.ok)throw new Error(obj.msg||'Request failed');return obj;
  }
  async function run(work,source){
    if(busy)return;busy=true;const owner=++operation;
    const controls=[...document.querySelectorAll('#group-view button,#group-view input,#group-view select,.group-dialog button,.group-dialog input,.group-dialog textarea,.group-dialog select')].map(e=>[e,e.disabled]);
    controls.forEach(([e])=>e.disabled=true);source?.setAttribute('aria-busy','true');
    try{message(tr('正在处理，请稍候…','Working…'));await work();}
    catch(err){if(owner===operation&&!err.quiet)message(err.message,true);}
    finally{if(owner===operation)busy=false;controls.forEach(([e,disabled])=>{if(e.isConnected)e.disabled=disabled;});source?.removeAttribute('aria-busy');}
  }
  function btn(label,work,primary=false){const e=n('button',label,{type:'button',class:'exam-btn'+(primary?' primary':'')});e.addEventListener('click',()=>run(work,e));return e;}
  function enter(){
    epoch++;lastKey='';window.bankUI?.scheduleSave(true);window.examUI?.leave();
    $('bank-library-view').hidden=true;$('bank-practice-view').hidden=true;$('group-view').hidden=false;
    for(const id of ['nav-library','nav-practice','nav-exams','nav-groups']){$(id).classList.toggle('active',id==='nav-groups');$(id).removeAttribute('aria-current');}
    $('nav-groups').setAttribute('aria-current','page');message();
  }
  function content(...children){
    const key=kind+(current?':'+current.id:'')+(kind==='detail'?':'+tab:'');
    const navigating=key!==lastKey,position={left:scrollX,top:scrollY};
    $('group-content').replaceChildren(...children);window.scrollTo(navigating?{left:0,top:0,behavior:'instant'}:{...position,behavior:'instant'});lastKey=key;
    if(navigating&&!matchMedia('(prefers-reduced-motion: reduce)').matches)$('group-content').animate([{opacity:.55,transform:'translateY(3px)'},{opacity:1,transform:'none'}],{duration:180,easing:'ease-out'});
  }
  function heading(title,subtitle,actions=[]){const head=n('div','',{class:'exam-heading'}),copy=n('div'),row=n('div','',{class:'exam-actions'});copy.append(n('h1',title),n('p',subtitle));row.append(...actions);head.append(copy,row);return head;}
  const card=()=>n('section','',{class:'exam-card'});
  const date=value=>value?new Date(value).toLocaleString(currentLang==='zh'?'zh-CN':'en-GB'):'—';
  const state=value=>t(value==='active'?'started':value);
  function field(label,value,tag='input'){const wrap=n('label',label,{class:'exam-field'}),input=n(tag);input.value=value||'';wrap.append(input);return [wrap,input];}
  function modal(title){
    $('group-message').hidden=true;$('group-message').textContent='';
    dialog?.remove();dialog=n('dialog','',{class:'exam-dialog group-dialog','aria-label':title});const head=n('div','',{class:'exam-dialog-head'}),close=n('button','×',{type:'button',class:'exam-btn','aria-label':t('close')});
    close.addEventListener('click',()=>{if(!busy)dialog.close();});head.append(n('h2',title),close);
    dialog.append(head,n('p','',{class:'bank-message group-dialog-message',role:'status','aria-live':'polite',hidden:''}));
    dialog.addEventListener('cancel',event=>{if(busy)event.preventDefault();});document.body.append(dialog);dialog.showModal();return dialog;
  }
  async function load(){
    enter();kind='list';current=null;results=null;
    if(!logged()){content(heading(t('groups'),tr('登录后创建或加入学习小组。','Sign in to create or join a learning group.')));message();return;}
    groups=(await api('/api/groups')).groups;renderList();message();
  }
  function renderList(){
    const list=n('div','',{class:'group-list'});
    for(const g of groups){
      const row=n('article','',{class:'group-list-row'}),identity=n('div'),metrics=n('div','',{class:'group-list-metrics'});
      identity.append(n('span',t(g.role),{class:'group-role '+g.role}),n('h2',g.name),n('p',g.description||tr('一起学习，共同进步。','Learn together, grow together.')));
      metrics.append(n('strong',String(g.member_count)),n('span',tr('位组员','members')),n('strong',String(g.exam_count)),n('span',tr('场考试','exams')));
      row.append(identity,metrics,btn(tr('进入小组 →','Open group →'),()=>open(g.id)));list.append(row);
    }
    content(heading(t('groups'),tr('把资料、练习和反馈，连接成一个共同学习的空间。','A shared space for assignments, learning and feedback.'),[btn(t('join'),joinDialog),btn(t('create'),()=>editDialog(),true)]),groups.length?list:n('div',tr('还没有小组。创建一个学习小组，或通过老师的邀请链接加入。','Create a learning group, or join through a teacher’s invitation.'),{class:'exam-empty'}));
  }
  async function open(id,notice=''){
    if($('group-view').hidden)enter();
    const changed=current?.id!==id;current=(await api('/api/groups/'+id)).group;kind='detail';
    if(changed){tab=current.role==='owner'?'members':'exams';results=null;resultExam='';}
    if(tab==='results'&&current.role==='owner'&&current.exams.length){
      if(!current.exams.some(e=>e.id===resultExam))resultExam=current.exams[0].id;
      results=(await api(`/api/groups/${current.id}/exams/${resultExam}/results`)).analytics;
    }
    renderDetail();message(notice);
  }
  function editDialog(editing=false){
    const box=modal(t(editing?'save':'create')),form=n('form');
    const [nameWrap,name]=field(t('name'),editing?current.name:'');name.required=true;name.maxLength=100;
    const [descWrap,desc]=field(t('description'),editing?current.description:'','textarea');desc.maxLength=2000;
    const submit=n('button',t(editing?'save':'create'),{type:'submit',class:'exam-btn primary'});form.append(nameWrap,descWrap,submit);
    form.addEventListener('submit',event=>{event.preventDefault();run(async()=>{
      const data={name:name.value.trim(),description:desc.value};
      const obj=await api(editing?'/api/groups/'+current.id:'/api/groups',data,editing?'PUT':'POST');
      dialog.close();current=null;await open(obj.group.id,tr('小组已保存。','Group saved.'));
    },submit);});box.append(form);name.focus();message();
  }
  function parseToken(value){
    let token=value.trim();if(/^[a-f0-9]{48}$/.test(token))return token;
    try{const url=new URL(token,location.origin);if(['http:','https:'].includes(url.protocol))return url.pathname.match(/^\/group\/([a-f0-9]{48})\/?$/)?.[1]||'';}catch(_){}return '';
  }
  function joinDialog(){
    const box=modal(t('join')),form=n('form'),[wrap,input]=field(tr('粘贴小组邀请链接','Paste a group invitation link'),'');input.required=true;input.placeholder='https://…/group/…';
    const submit=n('button',tr('查看邀请','Preview invitation'),{type:'submit',class:'exam-btn primary'});form.append(wrap,submit);
    form.addEventListener('submit',event=>{event.preventDefault();run(async()=>{const token=parseToken(input.value);if(!token)throw new Error(tr('请输入有效的小组邀请链接。','Enter a valid group invitation link.'));preview=(await api('/api/groups/shared/'+token)).group;inviteToken=token;dialog.close();kind='invite';current=null;renderInvite();message();},submit);});box.append(form);input.focus();message();
  }
  async function showInviteToken(token){
    enter();kind='invite';current=null;inviteToken=token;preview=(await api('/api/groups/shared/'+token)).group;renderInvite();message();
  }
  function renderInvite(){
    const body=card();body.append(n('span',tr('学习小组邀请','Learning group invitation'),{class:'group-role owner'}),n('h2',preview.name),n('p',preview.description,{class:'exam-text'}),n('p',tr('群主：','Owner: ')+preview.owner_name,{class:'exam-subtle'}));
    body.append(n('p',tr('加入后，老师发布的小组考试会显示在“考试 → 我参与的”中。你的本组考试成绩对群主可见，其他组员不能查看。','Group assignments appear in Exams → My attempts. The owner can see your group exam results; other members cannot.'),{class:'exam-notice'}));
    const join=btn(preview.joined?tr('进入小组','Open group'):t('join'),async()=>{const result=await api('/api/groups/shared/'+inviteToken+'/join',{});current=null;await open(result.group.id,tr('已加入小组。','Group joined.'));},true);join.disabled=preview.blocked;
    if(preview.blocked)body.append(n('p',tr('你已被移出，请联系群主恢复成员资格。','Contact the owner to restore your membership.'),{class:'exam-subtle'}));body.append(join);content(btn(t('back'),load),heading(preview.name,tr('由邀请开启一段共同学习。','Start learning together.')),body);
  }
  function inviteDialog(){
    const box=modal(t('invite')),input=n('input','',{readonly:'','aria-label':tr('小组邀请链接','Group invitation link')});input.value=current.invite_url;
    box.append(n('img','',{class:'exam-qr',src:`/api/groups/${current.id}/qr`,alt:tr('小组邀请二维码','Group invitation QR code')}),input);
    const actions=n('div','',{class:'exam-actions'});actions.append(btn(tr('复制链接','Copy link'),async()=>{try{await navigator.clipboard.writeText(input.value);message(tr('邀请链接已复制。','Invitation copied.'));}catch(_){input.select();message(tr('请选择链接手动复制。','Select the link and copy it manually.'));}}),btn(tr('更新邀请链接','Renew invite'),async()=>{
      if(!confirm(tr('更新后旧邀请链接将失效，已加入的组员不受影响。继续吗？','Invalidate old invitation links? Existing members are unaffected.'))) {message();return;}
      current=(await api(`/api/groups/${current.id}/invite`,{})).group;dialog.close();inviteDialog();
    }));box.append(actions,n('p',tr('扫码或打开链接后，登录账号并确认加入。请使用可访问的网站域名，不要分享 localhost。','Open or scan the link, sign in and confirm joining. Use a reachable site address, not localhost.'),{class:'exam-subtle'}));message();
  }
  function renderDetail(){
    const owner=current.role==='owner',actions=[btn(t('refresh'),()=>open(current.id)),...(owner?[btn(tr('编辑小组','Edit group'),()=>editDialog(true)),btn(t('invite'),inviteDialog),btn(t('publish'),publishDialog,true)]:[])];
    const tabs=n('div','',{class:'exam-tabs',role:'tablist'});
    for(const key of owner?['members','exams','results']:['exams','members']){const button=n('button',t(key),{class:'exam-tab',type:'button',role:'tab','aria-selected':tab===key});button.addEventListener('click',()=>run(async()=>{tab=key;renderDetail();if(key==='results'&&current.exams.length)await loadResults(resultExam||current.exams[0].id);else message();},button));tabs.append(button);}
    const body=tab==='members'?members():tab==='exams'?examList():resultsView();
    content(btn(t('back'),load),heading(current.name,current.description||tr('一起学习，共同进步。','Learn together, grow together.'),actions),n('p',`${t(current.role)} · ${current.owner_name} · ${current.member_count} ${tr('位组员','members')} · ${current.exams.length} ${tr('场考试','exams')}`,{class:'group-detail-meta'}),tabs,body);
  }
  function members(){
    const owner=current.role==='owner',section=card();
    section.append(n('h2',owner?tr('小组成员','Group members'):tr('我的成员信息','My membership')),n('p',owner?tr('可查看组员信息和本组考试成绩。移出后不再接收小组考试，历史作答保留。','View member information and group results. Removed members stop receiving assignments; completed work is retained.'):tr('群主可查看你的本组考试成绩，不会读取你的个人题库、资料或聊天记录。','The owner can see your group exam results, not your private libraries, files or chats.'),{class:'exam-subtle'}));
    const list=n('div','',{class:'group-members'});
    for(const member of current.members){
      const row=n('div','',{class:'group-member-row'}),avatar=n('span',member.username.slice(0,1).toUpperCase(),{class:'group-avatar','aria-hidden':'true'}),identity=n('div');
      identity.append(n('strong',member.username),n('small',`${t(member.role)} · ${t(member.status)} · ${tr('入组时间：','Joined: ')}${date(member.joined_at)}`));
      const controls=n('div','',{class:'exam-actions'});controls.append(btn(t('info'),()=>memberInfo(member)));
      if(owner&&member.role!=='owner')controls.append(btn(t(member.status==='active'?'remove':'restore'),async()=>{
        if(member.status==='active'&&!confirm(tr(`确认移出 ${member.username}？历史成绩不会删除。`,`Remove ${member.username}? Historical results will remain.`))){message();return;}
        current=(await api(`/api/groups/${current.id}/members/${encodeURIComponent(member.user_id)}`,{status:member.status==='active'?'removed':'active'},'PUT')).group;renderDetail();message(tr('成员状态已更新。','Membership updated.'));
      }));row.append(avatar,identity,controls);list.append(row);
    }
    section.append(list);return section;
  }
  async function memberInfo(member){
    const info=(await api(`/api/groups/${current.id}/members/${encodeURIComponent(member.user_id)}`)).member,box=modal(info.username);
    box.append(n('p',`${tr('用户 ID：','User ID: ')}${info.user_id}`,{class:'exam-subtle'}),n('p',`${t(info.status)} · ${tr('入组时间：','Joined: ')}${date(info.joined_at)}`,{class:'exam-subtle'}),n('h3',tr('本组考试记录','Group exam history')));
    const list=n('div','',{class:'group-member-history'});for(const exam of info.exams){const row=n('div','',{class:'exam-review-row'});row.append(n('span',exam.title),n('span',`${state(exam.status)} · ${exam.score===null?'—':exam.score+' / 100'}`));list.append(row);}box.append(info.exams.length?list:n('p',t('empty'),{class:'exam-subtle'}));message();
  }
  function examList(){
    const list=n('div','',{class:'group-list'});if(!current.exams.length)return n('div',tr('还没有发布考试。群主可从题库选择题目，审核后发布给组员。','No assignments yet. The owner can choose a question set and review it before assigning.'),{class:'exam-empty'});
    for(const exam of current.exams){const row=n('article','',{class:'group-exam-row'}),copy=n('div'),controls=n('div','',{class:'exam-actions'});
      copy.append(n('h2',exam.title),n('p',`${exam.question_count} ${tr('题','questions')} · ${tr('发布于 ','Assigned ')}${date(exam.published_at)}${exam.status==='closed'?' · '+tr('已关闭','Closed'):''}`));
      if(current.role==='owner'){copy.append(n('small',`${tr('已下发给 ','Delivered to ')}${exam.assigned_count} ${tr('位组员','members')}`));controls.append(btn(tr('查看试卷','View paper'),()=>window.examUI.openOwned(exam.id,{id:current.id,name:current.name})),btn(tr('查看成绩','View results'),async()=>{tab='results';await loadResults(exam.id);}));}
      else controls.append(btn(exam.attempt_status==='completed'?tr('查看成绩','View result'):exam.attempt_id?tr('继续作答','Resume'):tr('参加考试','Start exam'),()=>window.examUI.openToken(exam.token),true));
      row.append(copy,controls);list.append(row);
    }return list;
  }
  async function publishDialog(){
    const [sets,exams]=await Promise.all([api('/api/question_sets'),api('/api/exams')]);
    const box=modal(tr('发布考试到小组','Assign an exam to the group'));
    box.append(n('p',tr(`发布给当前全部 ${current.member_count} 位组员。后加入的组员会收到仍开放的考试。`,`Assign to all ${current.member_count} current members. Later members receive exams that remain open.`),{class:'exam-notice'}));
    const [bankWrap,bank]=field(tr('从我的题库创建考试','Create from my question library'),'','select');for(const item of sets.banks)bank.append(n('option',`${item.title} · ${item.questions.length} ${tr('题','questions')}`,{value:item.id}));
    const review=btn(tr('前往审核并发布','Review & assign'),async()=>{dialog.close();await window.examUI.editBank(bank.value,{id:current.id,name:current.name,publish:true});},true);review.disabled=!sets.banks.length;
    box.append(n('h3',tr('新建考试','New exam')),bankWrap,n('p',tr('沿用考试编辑页，先检查参考答案、解析和评分要点，再确认发布。','Review reference answers, explanations and criteria in the exam editor before assigning.'),{class:'exam-subtle'}),review);
    const published=exams.owned.filter(e=>e.status==='published');
    const [examWrap,select]=field(tr('或选择已经审核发布的考试','Or select an already reviewed exam'),'','select');for(const item of published)select.append(n('option',item.title,{value:item.id}));
    const existing=btn(tr('发布给全部组员','Assign to all members'),async()=>{
      const result=await api(`/api/groups/${current.id}/exams`,{exam_id:select.value,reviewed:true});dialog.close();current=result.group;tab='exams';results=null;renderDetail();message(tr(`已发布给 ${result.delivered_count} 位组员。`,`Assigned to ${result.delivered_count} members.`));
    },true);existing.disabled=!published.length;box.append(n('h3',tr('复用已发布考试','Reuse a published exam')),examWrap,existing);message();
  }
  async function loadResults(examId){
    resultExam=examId;
    const [detail,stats]=await Promise.all([api('/api/groups/'+current.id),api(`/api/groups/${current.id}/exams/${examId}/results`)]);
    current=detail.group;results=stats.analytics;renderDetail();message();
  }
  function resultsView(){
    if(!current.exams.length)return n('div',tr('发布一场考试后，可在这里查看组员的成绩。','Assign an exam to view member results here.'),{class:'exam-empty'});
    const section=n('section'),controls=n('div','',{class:'group-results-controls'}),[wrap,select]=field(tr('选择考试','Choose an exam'),'','select');
    for(const exam of current.exams){const option=n('option',exam.title,{value:exam.id});option.selected=exam.id===resultExam;select.append(option);}select.addEventListener('change',()=>run(()=>loadResults(select.value),select));controls.append(wrap,btn(t('refresh'),()=>loadResults(resultExam||current.exams[0].id)));section.append(controls);
    if(!results||!resultExam){section.append(n('p',tr('请选择考试查看成绩。','Choose an exam to view results.'),{class:'exam-subtle'}));return section;}
    const stats=n('div','',{class:'exam-stats-grid'});for(const [label,value] of [[tr('已下发','Assigned'),results.assigned],[tr('已开始','Started'),results.started],[tr('已完成','Completed'),results.completed],[tr('平均分 / 100','Average / 100'),results.average]]){const metric=card();metric.append(n('p',label,{class:'exam-subtle'}),n('strong',value===null?'—':String(value),{class:'exam-metric'}));stats.append(metric);}section.append(stats);
    section.append(n('p',`${tr('待参加','Not started')} ${results.not_started} · ${tr('完成率','Completion rate')} ${results.completion_rate??'—'}% · ${tr('及格率','Pass rate')} ${results.pass_rate??'—'}%`,{class:'exam-notice'}));
    const distribution=card();distribution.append(n('h2',tr('成绩分布','Score distribution')));const chart=n('div','',{class:'exam-distribution'}),max=Math.max(1,...results.distribution.map(b=>b.count));for(const bucket of results.distribution){const column=n('div','',{class:'exam-dist-column'}),area=n('div','',{class:'exam-dist-area'}),bar=n('div','',{class:'exam-dist-bar'});bar.style.height=Math.max(2,bucket.count/max*100)+'%';area.append(bar);column.append(n('strong',String(bucket.count)),area,n('span',bucket.label));chart.append(column);}distribution.append(chart);section.append(distribution);
    const roster=card();roster.append(n('h2',tr('组员成绩明细','Member results')),n('p',tr('仅统计收到本组考试的组员。分数统一折算为百分制，未完成不计入平均分；历史成绩在移出后保留。','Only recipients in this group are included. Scores are normalized to 100; unfinished work is excluded from averages. Removed members retain historical results.'),{class:'exam-subtle'}));
    const scroll=n('div','',{class:'group-table-scroll'}),table=n('table','',{class:'exam-roster-table'}),head=n('thead'),header=n('tr'),body=n('tbody');
    const labels=[tr('组员','Member'),tr('状态','Status'),tr('答题进度','Progress'),tr('成绩 / 100','Score / 100'),tr('完成时间','Completed')];for(const label of labels)header.append(n('th',label,{scope:'col'}));head.append(header);
    const count=current.exams.find(e=>e.id===resultExam)?.question_count||0;
    for(const student of results.students){
      const row=n('tr'),values=[student.username+(student.member_status==='removed'?' · '+t('removed'):''),state(student.status),`${student.done} / ${count}`,student.score===null?'—':String(Number((student.score/results.total*100).toFixed(1))),date(student.completed_at)];
      values.forEach((value,i)=>row.append(n('td',value,{'data-label':labels[i],...(i===3?{class:'exam-roster-score'}:{})})));body.append(row);
    }table.append(head,body);scroll.append(table);roster.append(scroll);section.append(roster);return section;
  }
  function leave(){epoch++;operation++;busy=false;$('group-view').hidden=true;$('nav-groups').classList.remove('active');$('nav-groups').removeAttribute('aria-current');$('group-message').hidden=true;dialog?.close();}
  window.groupUI={open:(id,notice)=>run(()=>open(id,notice)),leave,reset(){leave();groups=[];current=null;results=null;resultExam='';kind='list';lastKey='';},translate(){document.querySelectorAll('[data-group-i18n]').forEach(e=>e.textContent=t(e.dataset.groupI18n));if(!$('group-view').hidden&&!busy){if(kind==='list')renderList();else if(kind==='invite')renderInvite();else renderDetail();}},resumeLink(){const token=location.pathname.match(/^\/group\/([a-f0-9]{48})\/?$/)?.[1];if(token&&logged())run(()=>showInviteToken(token));}};
  document.addEventListener('DOMContentLoaded',()=>{$('nav-groups').addEventListener('click',()=>run(load));window.groupUI.translate();window.groupUI.resumeLink();});
})();
