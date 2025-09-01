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
    $('#eventCard').innerHTML = [
      kv('Title', esc(d.title)),
      kv('Date', esc(d.date||'—')),
      kv('Venue', esc(d.venue||'—')),
      kv('Organization', esc(d.organization||'—')),
    ].join('');

    $('#organizerCard').innerHTML = [
      kv('Submitted By', esc(d.submitted_by||'—')),
      kv('Faculty In-charge', esc((d.faculty_incharges||[]).join(', ')||'—')),
      kv('Contact', esc(d.submitter_email||'')),
    ].join('');

    const statusPills = [ chip((d.status||'').toUpperCase(), d.status==='finalized'?'ok':(d.status==='draft'?'warn':'')) ];
    $('#statusCard').innerHTML = [
      kv('Status', statusPills.join(' ')),
      kv('Assigned To', esc(d.assigned_to_name||'Unassigned')),
    ].join('');

    $('#resourcesCard').innerHTML = `
      ${d.poster_required? chip('Poster'):''}
      ${d.certificates_required? chip('Certificates','warn'):''}
      ${Array.isArray(d.other_services)? d.other_services.map(x=>chip(x)).join(''):''}
    ` || '<div class="empty">No specific resources requested</div>';

    $('#supportCard').innerHTML = [
      kv('Needs Support', d.needs_support? chip('Yes','ok'):chip('No')),
      kv('Poster Choice', esc(d.poster_choice||'—')),
      kv('Certificate Choice', esc(d.certificate_choice||'—')),
      kv('Design Links', [d.poster_design_link,d.certificate_design_link].filter(Boolean).map(u=>`<a class="link-muted" href="${u}" target="_blank">${u}</a>`).join('<br>') || '—')
    ].join('');

    // Speaker card (first speaker shown; extendable)
    const sp = (Array.isArray(d.speakers) && d.speakers.length) ? d.speakers[0] : null;
    if(sp){
      $('#speakerCard').innerHTML = [
        kv('Name', esc(sp.full_name||'—')),
        kv('Designation', esc(sp.designation||'—')),
        kv('Organization', esc(sp.affiliation||'—')),
        kv('Email', sp.contact_email ? `<a class="link-muted" href="mailto:${esc(sp.contact_email)}">${esc(sp.contact_email)}</a>` : '—'),
        kv('Phone', esc(sp.contact_number||'—')),
        kv('LinkedIn', sp.linkedin_url ? `<a class="link-muted" target="_blank" href="${esc(sp.linkedin_url)}">View Profile</a>` : '—'),
        sp.profile ? `<div class="kv" style="grid-template-columns:1fr"><strong style="grid-column:1/-1;color:var(--muted);font-size:12px">Notes</strong><span style="grid-column:1/-1">${esc(sp.profile)}</span></div>` : ''
      ].join('');
    } else {
      $('#speakerCard').innerHTML = '<div class="empty">No speaker details provided</div>';
    }

    // Hook Assign button
    $('#btnAssign')?.addEventListener('click', openAssign);
  }

  function renderError(msg){
    ['#eventCard','#organizerCard','#statusCard','#resourcesCard','#supportCard'].forEach(sel=>{
      const el=$(sel); if(el) el.innerHTML=`<div class="error">${esc(msg)}</div>`;
    });
  }

  // Assign flow
  function openAssign(){ $('#assignModal').style.display='flex'; fetchUsersByRole(); }
  $('#assignClose')?.addEventListener('click', ()=> $('#assignModal').style.display='none');
  $('#assignCancel')?.addEventListener('click', ()=> $('#assignModal').style.display='none');

  async function loadMembers(){
    try{ await fetchUsersByRole(); }catch{}
  }

  async function fetchUsersByRole(){
    try{
      const res = await fetch('/api/cdl/users/');
      if(!res.ok) return;
      const data = await res.json();
      const roleSel = $('#assignRole');
      const memSel = $('#assignMember');
      const role = roleSel.value;
      const users = data.users||{};
      const group = role.includes('Head') ? users.head : users.employee;
      memSel.innerHTML = '<option value="">Select member…</option>' + (group||[]).map(u=>`<option value="${u.id}">${esc(u.name)}${u.role? ' — '+esc(u.role): ''}</option>`).join('');
    }catch{}
  }
  document.addEventListener('change', e=>{ if(e.target && e.target.id==='assignRole'){ fetchUsersByRole(); }});

  $('#assignSave')?.addEventListener('click', async ()=>{
    const memberId = $('#assignMember')?.value;
    const role = $('#assignRole')?.value || '';
    if(!memberId){ toast('Select a member'); return; }
    try{
      const res = await fetch(`/api/cdl/support/${encodeURIComponent(eventId)}/assign/`, {method:'POST', headers:{'Content-Type':'application/json','X-CSRFToken':getCSRF()}, body:JSON.stringify({member_id: memberId, role})});
      const out = await res.json();
      if(!res.ok || !out.success) throw new Error(out.error||('HTTP '+res.status));
      toast('Assigned successfully');
      setTimeout(()=>location.reload(), 600);
    }catch(e){ toast('Assignment failed: '+(e.message||'Error')); }
  });

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
