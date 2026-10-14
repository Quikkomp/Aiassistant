/* Recovery grants stay in memory, never in URLs, cookies or localStorage. */
(() => {
  const $=id=>document.getElementById(id);
  const W={title:['找回密码','Reset password'],intro:['验证注册邮箱，安全找回你的学习空间。','Verify your registered email to recover your learning space.'],emailStep:['填写邮箱','Email'],codeStep:['验证邮箱','Verify'],passwordStep:['设置密码','Password'],email:['注册邮箱','Registered email'],emailHint:['请输入注册时填写的邮箱，不是网站的发信邮箱。','Use the email registered to your account, not the site’s sender address.'],code:['六位邮箱验证码','Six-digit email code'],codeHint:['验证码 10 分钟内有效，最多尝试 5 次。','Valid for 10 minutes; up to 5 attempts.'],newPassword:['新密码','New password'],confirmPassword:['确认新密码','Confirm password'],passwordHint:['8–128 位，不需要额外设置一套邮箱登录密码。','8–128 characters; the same password is used for username and email sign-in.'],changeEmail:['更换邮箱或重新验证','Change email or restart'],backLogin:['← 返回登录','← Back to sign in'],send:['发送验证码','Send code'],verify:['验证并继续','Verify & continue'],reset:['重置密码','Reset password'],resend:['重新发送','Resend code'],working:['正在处理…','Working…'],sent:['如果该邮箱已注册，验证码将发送至该邮箱。请检查收件箱和垃圾邮件。','If the email is registered, a code will be sent. Check your inbox and spam folder.'],verified:['邮箱验证成功，请设置新密码。','Email verified. Set a new password.'],done:['密码已重置，旧登录会话已失效。请返回登录，使用新密码。','Password reset. Previous sessions are invalidated. Sign in with your new password.']};
  const E={username_invalid:['用户名应为 3–32 个字符，支持中文、英文、数字及 _、-、.，首尾须为中文、字母或数字。','Use 3–32 Chinese characters, letters, digits, _, - or .; start and end with a letter or number.'],email_invalid:['请输入有效的邮箱地址。','Enter a valid email address.'],password_invalid:['新密码应为 8–128 个字符。','Use 8–128 characters for the new password.'],password_mismatch:['两次输入的密码不一致。','Passwords do not match.'],account_exists:['用户名或邮箱已被使用。','Username or email is already in use.'],invalid_credentials:['用户名、邮箱或密码不正确。','Incorrect username, email or password.'],invalid_code:['验证码无效、已使用或已过期，请重新获取。','The code is incorrect, used or expired. Request a new code.'],invalid_reset:['重置凭据无效或已过期，请重新验证邮箱。','Reset authorization is invalid or expired. Verify your email again.'],rate_limited:['操作过于频繁，请稍后再试。','Too many requests. Please try later.'],mail_unavailable:['验证码邮件服务尚未配置或暂不可用，请联系网站管理员。','Recovery email is not configured or temporarily unavailable. Contact the site administrator.'],service_unavailable:['账号服务暂不可用，请稍后重试。','Account service unavailable. Please try later.'],invalid_request:['请求格式无效。','Invalid request.'],session_expired:['登录已失效，请重新登录。','Session expired. Sign in again.']};
  const text=k=>W[k]?.[currentLang==='zh'?0:1]||k;
  const errorText=(code,fallback)=>E[code]?.[currentLang==='zh'?0:1]||fallback||text('working');
  let stage=0,requestId='',grant='',email='',pending=false,epoch=0,controller=null,timer=null,statusKey='';
  const cooldowns=new Map();
  const seconds=()=>Math.max(0,Math.ceil(((cooldowns.get(email)||0)-Date.now())/1000));
  function notice(value='',success=false){setAuthMessage('forgot-message',value,success);}
  function update(){
    for(const id of ['recovery-email','recovery-code','recovery-password','recovery-confirm'])$(id).disabled=pending;
    $('recovery-email').readOnly=stage>0;
    for(const [id,index] of [['recovery-code-step',1],['recovery-password-step',2]]){$(id).hidden=stage!==index;$(id).disabled=stage!==index;}
    document.querySelectorAll('.auth-recovery-steps li').forEach((li,i)=>{li.classList.toggle('is-current',stage===i);li.classList.toggle('is-complete',stage>i);if(stage===i)li.setAttribute('aria-current','step');else li.removeAttribute('aria-current');});
    $('recovery-submit').hidden=stage===3;
    $('recovery-submit').disabled=pending||(stage===0&&seconds()>0);
    $('recovery-submit').textContent=pending?text('working'):stage===0&&seconds()>0?`${seconds()}s · ${text('send')}`:text(['send','verify','reset'][Math.min(stage,2)]);
    $('recovery-resend').disabled=pending||seconds()>0;
    $('recovery-resend').textContent=seconds()>0?`${seconds()}s · ${text('resend')}`:text('resend');
    $('recovery-restart').hidden=stage===0||stage===3;$('recovery-restart').disabled=pending;
  }
  async function api(path,data,signal){
    const response=await fetch('/api/auth/password/'+path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data),signal});
    const result=await response.json();
    if(!response.ok||!result.ok){if(result.retry_after)cooldowns.set(email,Date.now()+result.retry_after*1000);throw Object.assign(new Error(errorText(result.code,result.msg)),{code:result.code});}
    return result;
  }
  async function run(work){
    if(pending)return;pending=true;const owner=epoch,startStage=stage;controller=new AbortController();statusKey='';notice('');update();
    try{await work(controller.signal,owner);}
    catch(error){if(owner===epoch&&error.name!=='AbortError')notice(error.message);}
    finally{if(owner===epoch){pending=false;controller=null;update();if(stage!==startStage&&stage<3)$(stage===1?'recovery-code':'recovery-password').focus({preventScroll:true});}}
  }
  async function send(signal,owner){
    email=$('recovery-email').value.trim().toLowerCase();if(seconds()>0)throw new Error(errorText('rate_limited'));
    const result=await api('request',{email},signal);if(owner!==epoch)return;
    requestId=result.request_id;grant='';$('recovery-code').value='';stage=1;
    cooldowns.set(email,Date.now()+(result.retry_after||60)*1000);statusKey='sent';notice(text(statusKey),true);update();$('recovery-code').focus({preventScroll:true});
  }
  function reset(){
    epoch++;controller?.abort();controller=null;pending=false;stage=0;requestId='';grant='';email='';statusKey='';clearInterval(timer);timer=null;
    $('forgot-form')?.reset();notice('');if($('recovery-submit'))update();
  }
  function open(){reset();const account=$('login-username').value.trim();if(account.includes('@')){$('recovery-email').value=account;email=account.toLowerCase();}$('login-password').value='';timer=setInterval(update,1000);update();$('recovery-email').focus({preventScroll:true});}
  function translate(){document.querySelectorAll('[data-recovery-i18n]').forEach(el=>el.textContent=text(el.dataset.recoveryI18n));$('recovery-email').placeholder=currentLang==='zh'?'例如：你的注册邮箱@example.com':'Your registered email@example.com';$('recovery-code').placeholder='000000';if(statusKey)notice(text(statusKey),true);update();}
  window.recoveryUI={open,reset,translate,errorText};
  document.addEventListener('DOMContentLoaded',()=>{
    $('forgot-form').addEventListener('submit',event=>{event.preventDefault();run(async(signal,owner)=>{
      if(stage===0){await send(signal,owner);return;}
      if(stage===1){const result=await api('verify',{email,request_id:requestId,code:$('recovery-code').value.trim()},signal);if(owner!==epoch)return;grant=result.reset_token;stage=2;$('recovery-code').value='';statusKey='verified';notice(text(statusKey),true);update();$('recovery-password').focus({preventScroll:true});return;}
      if(stage===2){if($('recovery-password').value!==$('recovery-confirm').value)throw new Error(errorText('password_mismatch'));await api('reset',{email,request_id:requestId,reset_token:grant,password:$('recovery-password').value,confirm_password:$('recovery-confirm').value},signal);if(owner!==epoch)return;grant='';requestId='';$('recovery-password').value='';$('recovery-confirm').value='';stage=3;$('login-username').value=email;statusKey='done';notice(text(statusKey),true);update();}
    });});
    $('recovery-resend').addEventListener('click',()=>run(send));
    $('recovery-restart').addEventListener('click',()=>{const savedEmail=email;reset();email=savedEmail;$('recovery-email').value=savedEmail;timer=setInterval(update,1000);update();$('recovery-email').focus({preventScroll:true});});
    $('recovery-email').addEventListener('input',()=>{if(stage===0){email=$('recovery-email').value.trim().toLowerCase();update();}});
    translate();
  });
})();
