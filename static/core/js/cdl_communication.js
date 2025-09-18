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
      const text = textarea.value.trim();
      if(!text && !fileInput.files.length) return;
      const fd = new FormData();
      fd.append('comment', text);
      if(fileInput.files[0]) fd.append('attachment', fileInput.files[0]);
      try{
        const res = await fetch('/api/cdl/communication/', { method:'POST', body: fd, headers: { 'X-Requested-With':'fetch','X-CSRFToken':getCSRF() } });
        if(!res.ok){ const err = await safeJSON(res); toast(err.error||'Send failed'); return; }
        const msg = await res.json();
        appendRow(msg, true);
        textarea.value=''; fileInput.value='';
        scrollBottom();
      }catch(err){ toast('Error sending'); }
    });
  }

  async function loadMessages(){
    try{
      const res = await fetch('/api/cdl/communication/');
      if(!res.ok) return;
      const data = await res.json();
      (data.messages||[]).reverse().forEach(m=> appendRow(m,false));
      refreshEmpty();
      scrollBottom();
    }catch{}
  }

  function appendRow(m,refresh=true){
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td style="padding:6px 8px;border-bottom:1px solid #e2e8f0;font-size:11px;color:#475569;white-space:nowrap">${fmtTime(m.created_at)}</td>
      <td style="padding:6px 8px;border-bottom:1px solid #e2e8f0;font-weight:600;color:#1e3a8a;font-size:12px">${esc(m.user_username||'User')}</td>
      <td style="padding:6px 8px;border-bottom:1px solid #e2e8f0;white-space:pre-wrap;word-break:break-word">${esc(m.comment)}</td>
      <td style="padding:6px 8px;border-bottom:1px solid #e2e8f0">${m.attachment_url?`<a href='${m.attachment_url}' target='_blank' style='font-size:11px;text-decoration:none;display:inline-flex;gap:4px;align-items:center'><i class="fa-regular fa-paperclip"></i> File</a>`:''}</td>`;
    tbody.appendChild(tr);
    if(refresh) refreshEmpty();
  }

  function refreshEmpty(){ empty.style.display = tbody.children.length? 'none':'block'; }
  function scrollBottom(){ scroller.scrollTop = scroller.scrollHeight; }
  function esc(s){ return (s??'').toString().replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }
  function fmtTime(iso){ try{ const d=new Date(iso); return d.toLocaleDateString(undefined,{month:'short',day:'2-digit'})+' '+d.toLocaleTimeString(undefined,{hour:'2-digit',minute:'2-digit'});}catch{return '';} }
  function getCSRF(){ const m=document.cookie.match(/csrftoken=([^;]+)/); return m?m[1]:''; }
  async function safeJSON(r){ try{return await r.json();}catch{return {};}}
  function toast(msg){
    let t=$('#toast');
    if(!t){ t=document.createElement('div'); t.id='toast'; t.style.cssText='position:fixed;bottom:16px;right:16px;background:#1e3a8a;color:#fff;padding:8px 12px;border-radius:8px;font-size:12px;font-weight:600;z-index:999;box-shadow:0 6px 24px rgba(15,23,42,.25)'; document.body.appendChild(t);}    
    t.textContent=msg; t.style.opacity='0'; t.style.display='block'; requestAnimationFrame(()=>{ t.style.transition='.25s'; t.style.opacity='1';}); setTimeout(()=>{ t.style.opacity='0'; setTimeout(()=>{ t.style.display='none';},250); },1700);
  }
})();
