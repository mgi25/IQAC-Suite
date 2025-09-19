// Kanban-style board for assigning tasks to members
(function(){
  const $=(s,r=document)=>r.querySelector(s);
  const esc=s=>(s??'').toString().replace(/[&<>"']/g,m=>({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;','\'':'&#39;' }[m]));
  const params=new URLSearchParams(location.search);
  const eventId=params.get('eventId')||params.get('id');
  if(!eventId){ alert('Missing eventId'); return; }
    const root=document.getElementById('cdl-assign-page');
    const EMPLOYEE_MODE = (params.get('mode')==='employee') || ((root&&root.dataset?root.dataset.employeeMode:'')==='1');

  const state={ members:[], rows:[], filter:'', baselineAssigned:new Set() };

  function toast(msg){ const t=$('#toast'); if(!t) return alert(msg); t.textContent=msg; t.style.display='block'; t.style.opacity='0'; t.style.transform='translateY(10px)'; requestAnimationFrame(()=>{ t.style.transition='.25s'; t.style.opacity='1'; t.style.transform='translateY(0)';}); setTimeout(()=>{ t.style.opacity='0'; t.style.transform='translateY(10px)'; setTimeout(()=>{ t.style.display='none'; },250); }, 1600); }
  function getCSRF(){ const m=document.cookie.match('(^|;)\\s*csrftoken\\s*=\\s*([^;]+)'); return m?m.pop():''; }

  async function load(){
     const res=await fetch(`/api/cdl/support/${encodeURIComponent(eventId)}/resources/` + (EMPLOYEE_MODE? '?mode=employee' : ''));
    if(!res.ok) throw new Error('Failed to load');
    const d=await res.json(); if(!d.success) throw new Error(d.error||'Failed');
    state.members=d.members||[];
    const existing=d.assignments||{}; // {key: {user_id,name}}
    const base=(d.resources||[]).map(r=>({ kind:'resource', key:r.key, label:r.label, user_id: existing[r.key]?.user_id||'', isCustom:false, status:'backlog' }));
    // Bring forward custom tasks from existing assignments (keys not present in d.resources)
    const extra=[]; for(const key of Object.keys(existing)){
      if(!(base.some(b=>b.key===key))){ extra.push({ kind:'custom', key:key, label:toTitle(key), user_id: existing[key]?.user_id||'', isCustom:true, status:'backlog' }); }
    }
    // Load server-side tasks with status/labels
    const serverTasks = (d.tasks||[]).map(t=>({ kind:(t.label && !base.some(b=>b.key===t.resource))?'custom':'resource', key:t.resource, label:t.label, user_id:t.assignee_id||'', isCustom: !!(t.label && !base.some(b=>b.key===t.resource)), status: t.status||'backlog', id: t.id }));
    // Merge: prefer serverTasks entries over base/extra for the same key
  const merged = new Map();
  [...base, ...extra, ...serverTasks].forEach(it=>{ merged.set(it.key, {...(merged.get(it.key)||{}), ...it}); });
  const allRows = Array.from(merged.values());
  // In employee mode, only show tasks that are truly assigned to the current user (i.e., persisted tasks)
  state.rows = EMPLOYEE_MODE ? allRows.filter(r => r.id || (r.user_id && String(r.user_id).length>0)) : allRows;
  state.baselineAssigned = new Set(Object.keys(existing).filter(k=>!!existing[k]?.user_id));
    renderBoard();
  }

  function toTitle(s){ return (s||'').replace(/_/g,' ').replace(/\b\w/g,c=>c.toUpperCase()); }

  let draggingKey=null, draggingEl=null;

  async function updateTask(row){
    // Employees cannot create tasks; only update status of existing tasks (must have id)
    if(EMPLOYEE_MODE && !row.id){ toast('This task is not assigned to you'); return; }
    try{
        const r = await fetch(`/api/cdl/support/${encodeURIComponent(eventId)}/tasks/`, {
        method:'PUT', headers:{'Content-Type':'application/json','X-CSRFToken':getCSRF()},
          body: JSON.stringify({ id: row.id, resource: row.key, label: row.label||'', status: row.status||'backlog', assignee_id: row.user_id || null })
      });
      if(r && r.ok){ toast('Status updated'); }
      try{ localStorage.setItem('cdl_tasks_ping', String(Date.now())); }catch{}
    }catch(e){ /* non-blocking */ }
  }
  async function deleteTask(resourceKey){
    try{
      await fetch(`/api/cdl/support/${encodeURIComponent(eventId)}/tasks/`, {
        method:'DELETE', headers:{'Content-Type':'application/json','X-CSRFToken':getCSRF()},
        body: JSON.stringify({ resource: resourceKey })
      });
      toast('Task removed');
      try{ localStorage.setItem('cdl_tasks_ping', String(Date.now())); }catch{}
    }catch(e){ toast('Failed to remove'); }
  }

  function renderBoard(){
    const board=$('#board'); if(!board) return;
    board.className='board';
    board.innerHTML='';

    // Columns: Backlog, In Progress, Done (status lanes)
    const columns=[
      { id:'backlog', name:'Backlog', status:'backlog' },
      { id:'in_progress', name:'In Progress', status:'in_progress' },
      { id:'done', name:'Done', status:'done' }
    ];

    const filter = (state.filter||'').toLowerCase();
    const items = state.rows.map(r=>({
      id: r.id || ('task_'+(r.key||Math.random().toString(36).slice(2))),
      key: r.key,
      label: r.label||r.key,
      isCustom: !!r.isCustom,
      user_id: r.user_id||null,
      status: r.status || 'backlog'
    })).filter(x=>!filter || (x.label||'').toLowerCase().includes(filter) || (x.key||'').toLowerCase().includes(filter));

    // Build columns
    for(const col of columns){
      const el=document.createElement('div'); el.className='col'; el.dataset.colId=col.id; el.dataset.status = col.status;
      el.innerHTML = `<div class="col-head">${esc(col.name)}</div><div class="col-body" data-dropzone="1"></div>`;
      board.appendChild(el);
    }

    // Distribute cards
    for(const it of items){
      const card = document.createElement('div'); card.className='card-item'; card.draggable=true; card.dataset.key=it.key; card.dataset.custom=it.isCustom?'1':'0'; card.dataset.id=it.id||'';
      const memberSelect = EMPLOYEE_MODE ? '' : `<select class="mini-select"><option value="">Unassigned</option>${state.members.map(m=>`<option value="${m.id}" ${String(it.user_id||'')===String(m.id)?'selected':''}>${esc(m.name)}</option>`).join('')}</select>`;
      const title = (it.isCustom && !EMPLOYEE_MODE)
        ? `<input class="title-input" value="${esc(it.label||'')}">`
        : `<div class="card-title-text">${esc(it.label)}</div>`;
      const metaParts = [ (it.isCustom? 'Custom':'Resource') ];
      if(!EMPLOYEE_MODE) metaParts.push(memberSelect);
      card.innerHTML = `<div class="card-title">${title}</div><div class="card-meta">${metaParts.join(' • ')}</div>`;
      addDnD(card);
      const col = $(`.col[data-status="${it.status||'backlog'}"] .col-body`);
      (col||$(`.col[data-status="backlog"] .col-body`)).appendChild(card);

      // Inline handlers
      const sel = card.querySelector('.mini-select');
        if(sel){ sel.addEventListener('change', ()=>{ const row = state.rows.find(r=>r.key===it.key); if(!row) return; row.user_id = sel.value || ''; updateTask(row); }); }
      const ti = card.querySelector('.title-input');
      if(ti){ ti.addEventListener('blur', ()=>{ const row=state.rows.find(r=>r.key===it.key); if(row){ row.label = ti.value || row.label; updateTask(row); }}); }
    }

    // Attach drop handlers once per zone
    document.querySelectorAll('[data-dropzone]')?.forEach(zone=>{
      zone.addEventListener('dragover', e=>{ if(draggingEl){ e.preventDefault(); zone.classList.add('drop'); } });
      zone.addEventListener('dragleave', ()=>zone.classList.remove('drop'));
      zone.addEventListener('drop', e=>{
        e.preventDefault(); zone.classList.remove('drop');
        if(!draggingKey || !draggingEl) return;
        const row=state.rows.find(r=>r.key===draggingKey); if(!row) return;
        const col=zone.closest('.col'); const status=col?.dataset.status || 'backlog';
        row.status = status; updateTask(row);
        zone.appendChild(draggingEl);
        draggingKey=null; draggingEl=null;
      });
    });

    // Allow remove via context for custom
  board.addEventListener('contextmenu', e=>{
      const card=e.target.closest('.card-item'); if(!card) return;
      e.preventDefault();
      if(card.dataset.custom==='1' && !EMPLOYEE_MODE){
    const key=card.dataset.key; state.rows = state.rows.filter(r=>r.key!==key); renderBoard();
    deleteTask(key);
      }
    });
  }

  function addDnD(card){
    card.addEventListener('dragstart', e=>{ draggingKey=card.dataset.key; draggingEl=card; e.dataTransfer.setData('text/plain', draggingKey); card.classList.add('dragging'); });
    card.addEventListener('dragend', ()=>{ card.classList.remove('dragging'); draggingKey=null; draggingEl=null; });
  }

  function collectPayload(){
    // Return array of {resource, user_id}
    const out=[];
    for(const r of state.rows){
      const userId = r.user_id? Number(r.user_id): null;
      let key = r.key;
      if(r.isCustom && (!key || /\s/.test(key))){
        const label=(r.label||'').trim(); if(!label) continue; key = label.toLowerCase().replace(/\s+/g,'_'); r.key=key;
      }
      if(userId){ out.push({ resource:key, user_id:userId, status: r.status||'backlog', label: r.label||'' }); }
    }
    return out;
  }

  async function save(){
    const assignments = collectPayload();
    const nowAssignedKeys = new Set(assignments.map(a=>a.resource));
    const toUnassign = Array.from(state.baselineAssigned).filter(k=>!nowAssignedKeys.has(k));
    const payload = { assignments, unassign: toUnassign };
    try{
      const btn=$('#saveAll'); const status=$('#saveStatus');
      if(btn){ btn.disabled=true; btn.textContent='Saving…'; }
      if(status){ status.textContent='Saving…'; }
      const r = await fetch(`/api/cdl/support/${encodeURIComponent(eventId)}/task-assignments/`, {
        method:'POST', headers:{'Content-Type':'application/json','X-CSRFToken':getCSRF()}, body: JSON.stringify(payload)
      });
      const out = await r.json();
      if(!r.ok || !out.success) throw new Error(out.error||('HTTP '+r.status));
      // Update baseline after successful save
      state.baselineAssigned = new Set([ ...nowAssignedKeys ]);
      toast('Assignments saved'); if(status){ status.textContent='Saved just now'; setTimeout(()=>status.textContent='',3000); }
      try{ localStorage.setItem('cdl_tasks_ping', String(Date.now())); }catch{}
    }catch(e){ toast('Save failed: '+(e.message||'Error')); }
    finally{
      const btn=$('#saveAll'); if(btn){ btn.disabled=false; btn.textContent='Save Changes'; }
    }
  }

  if(!EMPLOYEE_MODE) $('#addCustom').addEventListener('click', async ()=>{
    const key = 'custom_'+Math.random().toString(36).slice(2);
    const label = 'New custom task';
    state.rows.push({ kind:'custom', key, label, user_id:'', isCustom:true, status:'backlog' });
    renderBoard();
    // Persist immediately so it appears for collaborators
    try{
      await fetch(`/api/cdl/support/${encodeURIComponent(eventId)}/tasks/`, { method:'POST', headers:{'Content-Type':'application/json','X-CSRFToken':getCSRF()}, body: JSON.stringify({resource:key, label, status:'backlog'}) });
      try{ localStorage.setItem('cdl_tasks_ping', String(Date.now())); }catch{}
    }catch{}
  });
  if(!EMPLOYEE_MODE) $('#saveAll').addEventListener('click', save);
  if(EMPLOYEE_MODE){
    const btn=$('#saveMyStatus');
    if(btn){ btn.addEventListener('click', async ()=>{
      btn.disabled=true; const old=btn.textContent; btn.textContent='Saving…';
      try{
        // Save status for all assigned tasks the user sees
        for(const r of state.rows){ if(!r.id) continue; await updateTask(r); }
        toast('Status saved');
      }finally{ btn.disabled=false; btn.textContent=old; }
    }); }
  }
  $('#backBtn').addEventListener('click', ()=>{ location.href = `/cdl/support/?eventId=${encodeURIComponent(eventId)}`; });
  $('#searchTasks').addEventListener('input', e=>{ state.filter = e.target.value||''; renderBoard(); });

  // Basic styles for board (scoped)
  const style=document.createElement('style');
  style.textContent = `
  .board{display:grid;grid-template-columns:repeat(3, minmax(260px, 1fr));gap:12px;padding:10px}
    .board .col{border:1px solid var(--border);border-radius:10px;background:#fff;display:flex;flex-direction:column;min-height:360px}
    .board .col-head{padding:10px 12px;border-bottom:1px solid var(--border);font-weight:600;color:var(--muted);display:flex;align-items:center;gap:6px}
    .board .col-body{padding:10px;display:flex;flex-direction:column;gap:8px;min-height:280px}
  .card-item{border:1px solid var(--border);border-radius:10px;padding:10px;background:var(--surf);cursor:grab;user-select:none}
    .card-item.dragging{opacity:.6}
  .card-title{font-weight:600; display:flex; align-items:center}
  .card-title .title-input{width:100%; padding:6px 8px; border:1px solid var(--border); border-radius:8px; font-weight:600}
  .mini-select{width:auto; padding:4px 6px; border:1px solid var(--border); border-radius:6px; font-size:12px}
    .card-meta{font-size:12px;color:var(--muted)}
    .board .col-body.drop{outline:2px dashed var(--primary);outline-offset:2px}
  `;
  document.head.appendChild(style);

  load().catch(err=>{ const b=$('#board'); if(b) b.innerHTML = `<div class="error" style="padding:12px">${esc(err.message||'Failed')}</div>`; });

    // Lightweight polling for real-time sync
    let pollTimer=null; function startPolling(){ if(pollTimer) return; pollTimer=setInterval(()=>{ load().catch(()=>{}); }, 10000); }
    startPolling();

    // Instant cross-tab sync: refresh when Workboard or other tabs broadcast a change
    window.addEventListener('storage', (e)=>{
      if(e && e.key==='cdl_tasks_ping'){
        load().catch(()=>{});
      }
    });
})();
