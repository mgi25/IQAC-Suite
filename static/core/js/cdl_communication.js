(function(){
  const $=s=>document.querySelector(s);
  const tbody = $('#commTBody');
  const empty = $('#commEmpty');
  const form = $('#commForm');
  const textarea = $('#commText');
  const fileInput = $('#commFile');
  const scroller = $('#commScroller');

  init();

  async function init(){
    await loadMessages();
    bind();
  }

  function bind(){
    form?.addEventListener('submit', async e => {
      e.preventDefault();
      await sendMessage();
    });

    // Shift+Enter sends, Enter inserts newline (default textarea)
    textarea?.addEventListener('keydown', async e => {
      if(e.key === 'Enter' && e.shiftKey){
        e.preventDefault();
        await sendMessage();
      }
    });
  }

  async function sendMessage(){
    const textRaw = textarea.value;
    const text = textRaw.trim();
    if(!text && !fileInput.files.length) return;
    const fd = new FormData();
    fd.append('comment', textRaw); // preserve users' newlines exactly
    if(fileInput.files[0]) fd.append('attachment', fileInput.files[0]);
    try{
      const res = await fetch('/api/cdl/communication/', { method:'POST', body: fd, headers: { 'X-Requested-With':'fetch','X-CSRFToken':getCSRF() } });
      if(!res.ok){ const err = await safeJSON(res); toast(err.error||'Send failed'); return; }
      const msg = await res.json();
      appendRow(msg, true);
      textarea.value=''; fileInput.value='';
      textarea.focus();
      scrollBottom();
    }catch(err){ toast('Error sending'); }
  }

  let messageCache = [];

  async function loadMessages(){
    try{
      const res = await fetch('/api/cdl/communication/');
      if(!res.ok) return;
      const data = await res.json();
      messageCache = (data.messages||[]).reverse();
      renderGrouped();
      scrollBottom();
    }catch{}
  }

  function appendRow(m){
    messageCache.push(m);
    renderGrouped(true);
  }

  function renderGrouped(keepScroll=false){
    const prevBottom = scroller.scrollHeight - scroller.scrollTop;
    tbody.innerHTML='';
    // Group by date string (yyyy-mm-dd)
    const groups = {};
    for(const m of messageCache){
      const day = m.created_at.slice(0,10);
      (groups[day] = groups[day] || []).push(m);
    }
    const dayKeys = Object.keys(groups).sort();
    for(const day of dayKeys){
      const msgs = groups[day];
      msgs.sort((a,b)=> new Date(a.created_at) - new Date(b.created_at));
      msgs.forEach((m,i)=>{
        const tr=document.createElement('tr');
        const dateCell = i===0 ? `<td rowspan="${msgs.length}" style="padding:6px 8px;border-bottom:1px solid #e2e8f0;font-size:12px;font-weight:600;color:#334155;vertical-align:top;white-space:nowrap">${fmtDate(day)}</td>` : '';
        tr.innerHTML = `
          ${dateCell}
          <td style="padding:6px 8px;border-bottom:1px solid #e2e8f0;font-weight:600;color:#1e3a8a;font-size:12px;white-space:nowrap">${esc(m.user_username||'User')}<div style='font-size:10px;font-weight:400;color:#64748b;margin-top:2px'>${fmtTime(m.created_at)}</div></td>
          <td style="padding:6px 8px;border-bottom:1px solid #e2e8f0;white-space:pre-wrap;word-break:break-word">${esc(m.comment)}</td>
          <td style="padding:6px 8px;border-bottom:1px solid #e2e8f0">${m.attachment_url?`<a href='${m.attachment_url}' target='_blank' style='font-size:11px;text-decoration:none;display:inline-flex;gap:4px;align-items:center'><i class="fa-regular fa-paperclip"></i> File</a>`:''}</td>`;
        tbody.appendChild(tr);
      });
    }
    refreshEmpty();
    if(keepScroll){ scrollBottom(); } else { scroller.scrollTop = scroller.scrollHeight - prevBottom; }
  }

  function refreshEmpty(){ empty.style.display = messageCache.length? 'none':'block'; }
  function scrollBottom(){ scroller.scrollTop = scroller.scrollHeight; }
  function esc(s){ return (s??'').toString().replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }
  function fmtDate(day){ try{ const d=new Date(day); return d.toLocaleDateString(undefined,{day:'2-digit',month:'short',year:'numeric'});}catch{return day;} }
  function fmtTime(iso){ try{ const d=new Date(iso); return d.toLocaleTimeString(undefined,{hour:'2-digit',minute:'2-digit'});}catch{return '';} }
  function getCSRF(){ const m=document.cookie.match(/csrftoken=([^;]+)/); return m?m[1]:''; }
  async function safeJSON(r){ try{return await r.json();}catch{return {};}}
  function toast(msg){
    let t=$('#toast');
    if(!t){ t=document.createElement('div'); t.id='toast'; t.style.cssText='position:fixed;bottom:16px;right:16px;background:#1e3a8a;color:#fff;padding:8px 12px;border-radius:8px;font-size:12px;font-weight:600;z-index:999;box-shadow:0 6px 24px rgba(15,23,42,.25)'; document.body.appendChild(t);}    
    t.textContent=msg; t.style.opacity='0'; t.style.display='block'; requestAnimationFrame(()=>{ t.style.transition='.25s'; t.style.opacity='1';}); setTimeout(()=>{ t.style.opacity='0'; setTimeout(()=>{ t.style.display='none';},250); },1700);
  }
})();
