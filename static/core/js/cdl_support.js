(function(){
  const $=(s,r=document)=>r.querySelector(s);
  const esc=s=>(s??'').toString().replace(/[&<>"']/g,m=>({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;','\'':'&#39;' }[m]));
  const params=new URLSearchParams(location.search);
  const eventId=params.get('eventId')||params.get('id');
  if(!eventId){ renderError('Missing eventId in URL'); return; }

  async function fetchDetail(){
    try{
      const res = await fetch(`/api/cdl/support/${encodeURIComponent(eventId)}/`);
      if(!res.ok) throw new Error(`HTTP ${res.status}`);
      const d = await res.json();
      if(!d.success){ throw new Error(d.error||'Failed'); }
  render(d.data);
  await loadMembers();
    }catch(e){ renderError(e.message||'Failed to load'); }
  }

  function kv(k,v){ return `<div class="kv"><strong>${esc(k)}</strong><span>${v??'—'}</span></div>`; }
  function chip(label,cls=''){ return `<span class="pill ${cls}">${esc(label)}</span>`; }

  function render(d){
    const eventEl = $('#eventCard');
    if(eventEl){ eventEl.innerHTML = [
      kv('Title', esc(d.title)),
      kv('Date', esc(d.date||'—')),
      kv('Venue', esc(d.venue||'—')),
      kv('Organization', esc(d.organization||'—')),
    ].join(''); }

    const orgEl = $('#organizerCard');
    if(orgEl){ orgEl.innerHTML = [
      kv('Submitted By', esc(d.submitted_by||'—')),
      kv('Faculty In-charge', esc((d.faculty_incharges||[]).join(', ')||'—')),
      kv('Contact', esc(d.submitter_email||'')),
    ].join(''); }

    const statusEl = $('#statusCard');
    if(statusEl){
      const statusPills = [ chip((d.status||'').toUpperCase(), d.status==='finalized'?'ok':(d.status==='draft'?'warn':'')) ];
      statusEl.innerHTML = [
        kv('Status', statusPills.join(' ')),
        kv('Assigned To', esc(d.assigned_to_name||'Unassigned')),
      ].join('');
    }

    const resEl = $('#resourcesCard');
    if(resEl){
      resEl.innerHTML = `
        ${d.poster_required? chip('Poster'):''}
        ${d.certificates_required? chip('Certificates','warn'):''}
        ${Array.isArray(d.other_services)? d.other_services.map(x=>chip(x)).join(''):''}
      ` || '<div class="empty">No specific resources requested</div>';
    }

    const suppEl = $('#supportCard');
    if(suppEl){
      suppEl.innerHTML = [
        kv('Needs Support', d.needs_support? chip('Yes','ok'):chip('No')),
        kv('Poster Choice', esc(d.poster_choice||'—')),
        kv('Certificate Choice', esc(d.certificate_choice||'—')),
        kv('Design Links', [d.poster_design_link,d.certificate_design_link].filter(Boolean).map(u=>`<a class="link-muted" href="${u}" target="_blank">${u}</a>`).join('<br>') || '—')
      ].join('');
    }

    // Speaker card (first speaker shown; extendable)
    const sp = (Array.isArray(d.speakers) && d.speakers.length) ? d.speakers[0] : null;
    const speakerEl = $('#speakerCard');
    if(sp && speakerEl){
      speakerEl.innerHTML = [
        kv('Name', esc(sp.full_name||'—')),
        kv('Designation', esc(sp.designation||'—')),
        kv('Organization', esc(sp.affiliation||'—')),
        kv('Email', sp.contact_email ? `<a class="link-muted" href="mailto:${esc(sp.contact_email)}">${esc(sp.contact_email)}</a>` : '—'),
        kv('Phone', esc(sp.contact_number||'—')),
        kv('LinkedIn', sp.linkedin_url ? `<a class="link-muted" target="_blank" href="${esc(sp.linkedin_url)}">View Profile</a>` : '—'),
        sp.profile ? `<div class="kv" style="grid-template-columns:1fr"><strong style="grid-column:1/-1;color:var(--muted);font-size:12px">Notes</strong><span style="grid-column:1/-1">${esc(sp.profile)}</span></div>` : ''
      ].join('');
    } else if(speakerEl){
      speakerEl.innerHTML = '<div class="empty">No speaker details provided</div>';
    }

  // Hook Assign button (only rendered for CDL Head)
  $('#btnAssign')?.addEventListener('click', openAssign);
  }

  function renderError(msg){
    ['#eventCard','#organizerCard','#statusCard','#resourcesCard','#supportCard','#speakerCard'].forEach(sel=>{
      const el=$(sel); if(el) el.innerHTML=`<div class="error">${esc(msg)}</div>`;
    });
  }

  // Assign flow — dynamic resource grid
  function openAssign(){ $('#assignModal').style.display='flex'; buildAssignGrid(); }
  $('#assignClose')?.addEventListener('click', ()=> $('#assignModal').style.display='none');
  $('#assignCancel')?.addEventListener('click', ()=> $('#assignModal').style.display='none');

  async function loadMembers(){ /* kept for backwards compatibility; no-op */ }

  async function fetchResourcesAndMembers(){
    const res = await fetch(`/api/cdl/support/${encodeURIComponent(eventId)}/resources/`);
    if(!res.ok) throw new Error('Failed to load resources');
    return res.json();
  }

  async function buildAssignGrid(){
    try{
      const data = await fetchResourcesAndMembers();
      const wrap = $('#assignGrid');
      const members = data.members||[];
      const existing = data.assignments||{};
      if(!(data.resources||[]).length){ wrap.innerHTML = '<div class="empty" style="grid-column:1/-1">No assignable resources for this event</div>'; return; }
      wrap.innerHTML = '';
      for(const r of data.resources){
        const row = document.createElement('div'); row.className='row'; row.style.display='contents';
        const label = document.createElement('div'); label.textContent = r.label || r.key; label.style.display='flex'; label.style.alignItems='center';
        const selectWrap = document.createElement('div');
        const sel = document.createElement('select'); sel.className='select'; sel.dataset.resource = r.key;
        sel.innerHTML = '<option value="">Unassigned</option>' + members.map(m=>`<option value="${m.id}">${esc(m.name)}</option>`).join('');
        const pre = existing[r.key]; if(pre){ sel.value = String(pre.user_id); }
        selectWrap.appendChild(sel);
        wrap.appendChild(label); wrap.appendChild(selectWrap);
      }
      // Save handler
      $('#assignSave').onclick = async ()=>{
        const picks = Array.from(document.querySelectorAll('#assignGrid select')).map(sel=>({resource: sel.dataset.resource, user_id: sel.value? Number(sel.value): null})).filter(x=>x.user_id);
        try{
          const r2 = await fetch(`/api/cdl/support/${encodeURIComponent(eventId)}/task-assignments/`, { method:'POST', headers:{'Content-Type':'application/json','X-CSRFToken':getCSRF()}, body: JSON.stringify({ assignments: picks }) });
          const out = await r2.json();
          if(!r2.ok || !out.success) throw new Error(out.error||('HTTP '+r2.status));
          toast('Assignments saved');
          $('#assignModal').style.display='none';
          await refreshAssignmentsUI();
        }catch(e){ toast('Save failed: '+(e.message||'Error')); }
      };
    }catch(e){
      $('#assignGrid').innerHTML = `<div class="error">${esc(e.message||'Failed to load')}</div>`;
    }
  }

  async function refreshAssignmentsUI(){
    try{
      const data = await fetchResourcesAndMembers();
      const list = $('#assignmentList');
      const existing = data.assignments||{};
      const out = [];
      for(const r of (data.resources||[])){
        const assg = existing[r.key];
        out.push(`<div class="kv"><strong>${esc(r.label||r.key)}</strong><span>${assg? esc(assg.name): 'Unassigned'}</span></div>`);
      }
      list.innerHTML = out.join('') || '';
    }catch{}
  }

  function getCSRF(){
    const name='csrftoken';
    const m=document.cookie.match('(^|;)\\s*'+name+'\\s*=\\s*([^;]+)');
    return m?m.pop():'';
  }

  function toast(msg){
    const t=document.getElementById('toast'); if(!t) return alert(msg);
    t.textContent=msg; t.style.display='block'; t.style.opacity='0'; t.style.transform='translateY(10px)';
    requestAnimationFrame(()=>{ t.style.transition='.25s'; t.style.opacity='1'; t.style.transform='translateY(0)';});
    setTimeout(()=>{ t.style.opacity='0'; t.style.transform='translateY(10px)'; setTimeout(()=>{ t.style.display='none'; },250); }, 1600);
  }

  // wire from notification list -> cdl_support
  document.addEventListener('click', e=>{
    const btn = e.target.closest('[data-event-id][data-navigate-support]');
    if(btn){ const id=btn.dataset.eventId; location.href=`/cdl/support/?eventId=${encodeURIComponent(id)}`; }
  });

  fetchDetail();
})();
