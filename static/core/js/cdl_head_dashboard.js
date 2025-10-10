
(function () {
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));

  // State loaded via AJAX
  let EVENTS = [];
  let EVENT_DETAILS = [];
  let WORKLOAD_DATA = {};
  let KPIS = { total_active_requests:0, assets_pending:0, unassigned_tasks:0, total_events_supported:0 };
  let currentScope = 'all'; // all | support
  let selectedMember = '';

  async function loadData(scope='all'){
    try{
      if(window.AppOverlay) AppOverlay.show('Loading dashboard…');
      const res = await fetch(`/api/cdl/head-dashboard/?scope=${encodeURIComponent(scope)}`, {headers:{'Accept':'application/json'}});
      if(!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      KPIS = data.kpis || KPIS;
      EVENTS = (data.events || []).filter(Boolean);
      EVENT_DETAILS = (data.event_details || []).filter(Boolean);
      WORKLOAD_DATA = data.workload || {};
      renderAll();
      populateMemberFilter();
    } catch(err){
      console.warn('Failed to load CDL dashboard data:', err);
      KPIS = { total_active_requests:0, assets_pending:0, unassigned_tasks:0, total_events_supported:0 };
      EVENTS = [];
      EVENT_DETAILS = [];
      WORKLOAD_DATA = {};
      renderAll();
    } finally {
      if(window.AppOverlay) AppOverlay.hide();
    }
  }

  function renderKPIs(){
    $('#valActive').textContent = KPIS.total_active_requests ?? 0;
    $('#valAssetsPending').textContent = KPIS.assets_pending ?? 0;
    $('#valUnassigned').textContent = KPIS.unassigned_tasks ?? 0;
    $('#valEvents').textContent = KPIS.total_events_supported ?? 0;
  }

  // Notifications (Event Details) filtering
  let currentEventFilter = 'all';
  function renderNotifications(filter='all'){
    const list = $('#eventDetailsList');
    if(!list) return;
    let items = EVENT_DETAILS;

    // helper to check other_services keywords
    const hasSrv = (ev, keys=[]) => {
      const arr = Array.isArray(ev.other_services) ? ev.other_services : [];
      const s = arr.map(String).join(' ').toLowerCase();
      return keys.some(k => s.includes(k));
    };

    // Filter by type - only finalized
    if (filter === 'posters') {
      items = items.filter(ev => ev.poster_required && ev.status === 'finalized');
    } else if (filter === 'certificates') {
      items = items.filter(ev => ev.certificates_required && ev.status === 'finalized');
    } else if (filter === 'coverage') {
      // treat "coverage" as photography/media coverage in other_services
      items = items.filter(ev => ev.status === 'finalized' && hasSrv(ev, ['coverage','photography','photo']));
    } else if (filter === 'media') {
      // generic media-related services
      items = items.filter(ev => ev.status === 'finalized' && hasSrv(ev, ['media','video','press']));
    } else {
      items = items.filter(ev => ev.status === 'finalized');
    }

    if(items.length === 0){
      list.innerHTML = '<div class="empty">No finalized notifications</div>';
      return;
    }

    list.innerHTML = items.map(ev => {
      const dateStr = ev.date ? new Date(ev.date).toLocaleDateString(undefined, {month:'short', day:'2-digit'}) : '';
      const org = ev.organization || 'N/A';
      const assigned = ev.assigned_member || 'Unassigned';
      const tags = [
        ev.poster_required ? 'Poster' : null,
        ev.certificates_required ? 'Certificate' : null
      ].filter(Boolean).join(' · ');
      return `<article class="list-item" data-id="${ev.id}">
        <div class="bullet under_review"><i class="fa-regular fa-envelope"></i></div>
        <div class="list-body">
          <h4>${ev.title}</h4>
          <p>Status: ${ev.status}${dateStr?` · Date: ${dateStr}`:''}</p>
          <p>Department: ${org} · Assigned: ${assigned}${tags?` · ${tags}`:''}</p>
        </div>
        <div class="btn-group">
          <a class="chip-btn primary" href="/cdl/support/?eventId=${ev.id}"><i class="fa-regular fa-eye"></i> View</a>
        </div>
      </article>`;
    }).join('');
  }

  // Filter tabs (scoped to Notifications card)
  document.addEventListener('click', e => {
    const t = e.target.closest('#cardNotifications .tab-btn');
    if(!t) return;
    $$('#cardNotifications .tab-btn').forEach(b => b.classList.remove('active'));
    t.classList.add('active');
    currentEventFilter = t.dataset.filter || 'all';
    renderNotifications(currentEventFilter);
  });

  // Assignment Manager - build from EVENT_DETAILS
  function renderAssignmentTable(){
    const tbody = $('#taskList'); 
    if(!tbody) return;
    const tasks = EVENT_DETAILS.filter(ev => (ev.poster_required || ev.certificates_required));
    if(tasks.length === 0){ 
      tbody.innerHTML = '<tr><td colspan="8" class="empty-row">No items</td></tr>'; 
      return; 
    }
    tbody.innerHTML = tasks.map(ev => {
      const dateStr = ev.date ? new Date(ev.date).toLocaleDateString(undefined, {month:'short', day:'2-digit'}) : '';
      const type = [];
      if (ev.poster_required) type.push('Poster');
      if (ev.certificates_required) type.push('Certificate');
      return `<tr data-id="${ev.id}">
        <td><a href="/proposal/${ev.id}/detail/" class="link">${ev.title}</a></td>
        <td>${type.join(', ')}</td>
        <td><span class="priority-badge normal">Normal</span></td>
        <td>${dateStr}</td>
        <td class="assigned-to">${ev.assigned_member || 'Unassigned'}</td>
        <td><span class="status-badge pending">Pending</span></td>
        <td>1</td>
          <td class="ta-right"><a class="chip-btn primary" data-action="open-assign" href="/cdl/support/${ev.id}/assign/"><i class="fa-regular fa-pen-to-square"></i> Assign</a></td>
      </tr>`;
    }).join('');
  }

  // Assignment filters
  document.addEventListener('click', e => {
    const b = e.target.closest('#cardAssignAll .control-btn[data-filter]');
    if(!b) return;
    $$('#cardAssignAll .control-btn[data-filter]').forEach(x=>x.classList.remove('active'));
    b.classList.add('active');
    const filter = b.dataset.filter;
    $$('#taskList tr[data-id]').forEach(row => {
      let show = true;
      if(filter === 'unassigned') show = (row.querySelector('.assigned-to')?.textContent.trim() || '') === '' || row.querySelector('.assigned-to')?.textContent.includes('Unassigned');
      if(filter === 'urgent') show = row.cells[2]?.textContent.includes('Certificate');
      row.style.display = show ? '' : 'none';
    });
  });
  // Row Assign action opens Assign Tasks page (navigate via href)
  // No additional JS needed; link already points to /cdl/support/?eventId=ID

  // Team Analytics
  let teamChart;
  function buildTeamChart(labels, data){
    const ctx = $('#teamChart'); if(!ctx) return;
    teamChart?.destroy();
    teamChart = new Chart(ctx, {
      type: 'bar',
  data: { labels, datasets:[{ data, backgroundColor:'#3384db', borderWidth:0, barPercentage:0.35, categoryPercentage:0.55, maxBarThickness:18 }]},
      options: {
        plugins:{legend:{display:false}},
        responsive:true,
        maintainAspectRatio:false,
        scales:{
          y:{ beginAtZero:true, grid:{ color:'rgba(0,0,0,0.06)', lineWidth:0.7 } },
          x:{ grid:{ color:'rgba(0,0,0,0.03)', lineWidth:0.7 } }
        }
      }
    });
  }
  function getFilteredWorkload(){
    const members = WORKLOAD_DATA.members || [];
    const counts  = WORKLOAD_DATA.assignments || [];
    if(!members.length) return {labels:['No Members'], data:[0]};
    if(!selectedMember){
      return {labels: members, data: counts};
    }
    const idx = members.findIndex(n => (n||'') === selectedMember);
    if(idx === -1) return {labels: members, data: counts};
    return {labels: [members[idx]], data: [counts[idx]||0]};
  }
  function viewWorkload(){
    const {labels, data} = getFilteredWorkload();
    buildTeamChart(labels, data);
  }
  document.addEventListener('click', e => {
    const b = e.target.closest('#cardTeam .control-btn[data-view]');
    if(!b) return;
    $$('#cardTeam .control-btn[data-view]').forEach(x=>x.classList.remove('active'));
    b.classList.add('active');
    const v = b.dataset.view;
    if(v==='workload') viewWorkload();
    if(v==='ontime') buildTeamChart((WORKLOAD_DATA.members||['No Members']), (WORKLOAD_DATA.members||['']).map(()=>0));
    if(v==='firstpass') buildTeamChart((WORKLOAD_DATA.members||['No Members']), (WORKLOAD_DATA.members||['']).map(()=>0));
  });

  // Populate and handle member selector
  function populateMemberFilter(){
    const sel = document.getElementById('memberFilter');
    if(!sel) return;
    const members = WORKLOAD_DATA.members || [];
    // Preserve current selection if possible
    const prev = selectedMember;
    sel.innerHTML = '<option value="">All employees</option>' + members.map(n=>`<option value="${String(n)}">${String(n)}</option>`).join('');
    // Restore selection
    if(prev && members.includes(prev)){
      sel.value = prev;
    }else{
      sel.value = '';
      selectedMember = '';
    }
  }
  document.addEventListener('change', e => {
    const sel = e.target.closest('#memberFilter');
    if(!sel) return;
    selectedMember = sel.value;
    viewWorkload();
  });

  // Calendar
  let calRef = new Date();
  let currentCalFilter = 'all';
  const fmt2 = v => String(v).padStart(2,'0');
  const titleEl = $('#calTitle'), gridEl = $('#calGrid');
  function buildCalendar(){
    if(!gridEl || !titleEl) return;
    titleEl.textContent = calRef.toLocaleString(undefined, {month:'long', year:'numeric'});
    const first = new Date(calRef.getFullYear(), calRef.getMonth(), 1);
    const last  = new Date(calRef.getFullYear(), calRef.getMonth()+1, 0);
    const startIdx = first.getDay();
    const prevLast = new Date(calRef.getFullYear(), calRef.getMonth(), 0).getDate();
    const cells = [];
    for(let i = startIdx-1; i >= 0; i--) cells.push({t: prevLast - i, iso:null, muted:true});
    for(let d = 1; d <= last.getDate(); d++){
      const iso = `${calRef.getFullYear()}-${fmt2(calRef.getMonth()+1)}-${fmt2(d)}`;
      cells.push({t:d, iso, muted:false});
    }
    while(cells.length % 7 !== 0) cells.push({t:'', iso:null, muted:true});
    gridEl.innerHTML = cells.map(c => {
      if (!c.iso) return `<div class="day muted" data-date="">${c.t}</div>`;
      const isToday = c.iso === new Date().toISOString().slice(0,10);
      const dayAll = EVENTS.filter(e => e.date === c.iso);
      const count = dayAll.length;
      const hasSupport = dayAll.some(e => e.type === 'cdl_support');
      let markClass = '';
      if (count > 0) {
        markClass = (currentCalFilter === 'support') ? ' has-meeting' : (hasSupport ? ' has-meeting' : ' has-event');
      }
      return `<div class="day${markClass}${isToday ? ' today' : ''}" data-date="${c.iso}">${c.t}</div>`;
    }).join('');
    $$('.day[data-date]').forEach(d => d.addEventListener('click', () => {
      $$('.day.selected').forEach(x => x.classList.remove('selected'));
      d.classList.add('selected');
      openDay(d.dataset.date);
    }));
  }
  function openDay(iso){
    let items = EVENTS.filter(e => e.date === iso);
    if (currentCalFilter === 'support') items = items.filter(e => e.type === 'cdl_support');
    const wrap = $('#eventDetailsContent');
    const dateStr = new Date(iso).toLocaleDateString(undefined, {day:'2-digit', month:'2-digit', year:'numeric'});
    wrap.innerHTML = items.length ? items.map(e => `
      <div class="event-detail-item">
        <div class="event-detail-title with-actions">
          <span class="title-text">${e.title}</span>
          <div class="title-actions"><a class="chip-btn" href="/cdl/support/?eventId=${e.id}">View</a></div>
        </div>
        <div class="event-detail-meta">${dateStr} • Status: ${e.status} • Org: ${e.organization||'N/A'}</div>
      </div>
    `).join('') : `<div class="empty">No events on this date</div>`;
  }
  $('#calFilter')?.addEventListener('change', e => {
    currentCalFilter = e.target.value;
    currentScope = currentCalFilter;
      try{ localStorage.setItem('iqac:cdl:scope', currentScope); }catch(_e){}
    loadData(currentScope);
  });
  $('#calPrev')?.addEventListener('click', () => { calRef = new Date(calRef.getFullYear(), calRef.getMonth()-1, 1); buildCalendar(); });
  $('#calNext')?.addEventListener('click', () => { calRef = new Date(calRef.getFullYear(), calRef.getMonth()+1, 1); buildCalendar(); });

  function renderAll(){
    renderKPIs();
    renderNotifications(currentEventFilter);
    renderAssignmentTable();
    viewWorkload();
    buildCalendar();
    const today = new Date().toISOString().slice(0,10);
    const todayCell = $(`.day[data-date="${today}"]`);
    if (todayCell) { todayCell.classList.add('selected'); openDay(today); }
  }

  document.addEventListener('DOMContentLoaded', () => {
     try{ const saved = localStorage.getItem('iqac:cdl:scope'); if(saved){ currentScope = saved; currentCalFilter = saved; const sel = document.getElementById('calFilter'); if(sel) sel.value = saved; } }catch(_e){}
     loadData(currentScope);
  });
})();
