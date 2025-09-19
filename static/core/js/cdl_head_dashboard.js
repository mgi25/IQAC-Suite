
(function(){
  // Simple DOM helpers
  const $  = (s, r=document)=>r.querySelector(s);
  const $$ = (s, r=document)=>Array.from(r.querySelectorAll(s));

  // State
  let DASH = { kpis:{}, events:[], event_details:[], workload:{members:[], assignments:[]} };
  let calRef = new Date();
  let chart;

  // Boot
  init();

  async function init(){
    bindUI();
    await loadData($('#calFilter')?.value || 'all');
    renderAll();
  }

  function bindUI(){
    // KPI cards are display-only

    // Notifications filter tabs
    $$('#cardNotifications .tab-btn').forEach(btn=>{
      btn.addEventListener('click', e=>{
        $$('#cardNotifications .tab-btn').forEach(b=>b.classList.remove('active'));
        e.currentTarget.classList.add('active');
        renderNotifications(e.currentTarget.dataset.filter || 'all');
      });
    });

    // Team chart controls
    $$('#cardTeam .control-btn').forEach(btn=>{
      btn.addEventListener('click', e=>{
        $$('#cardTeam .control-btn').forEach(b=>b.classList.remove('active'));
        e.currentTarget.classList.add('active');
        renderChart(e.currentTarget.dataset.view || 'workload');
      });
    });
    $$('#cardTeam .time-btn').forEach(btn=>{
      btn.addEventListener('click', e=>{
        $$('#cardTeam .time-btn').forEach(b=>b.classList.remove('active'));
        e.currentTarget.classList.add('active');
        // Time range is cosmetic for now
      });
    });

    // Calendar navigation
    $('#calPrev')?.addEventListener('click',()=>{ calRef = new Date(calRef.getFullYear(), calRef.getMonth()-1, 1); buildCalendar(); });
    $('#calNext')?.addEventListener('click',()=>{ calRef = new Date(calRef.getFullYear(), calRef.getMonth()+1, 1); buildCalendar(); });
    $('#calFilter')?.addEventListener('change', ()=> loadData($('#calFilter').value).then(()=>{ buildCalendar(); clearEventDetails(); }));

    // Clear event details
    $('#clearEventDetails')?.addEventListener('click', ()=> clearEventDetails());
  }

  async function loadData(scope){
    try{
      const data = await fetchJSON(`/api/cdl/head-dashboard/?scope=${encodeURIComponent(scope||'all')}`);
      DASH = data || DASH;
    }catch(e){
      // keep UI usable
    }
  }

  function renderAll(){
    renderKPIs();
    renderNotifications('all');
    renderChart('workload');
    buildCalendar();
    // Try opening today's date if there are entries
    const todayISO = new Date().toISOString().slice(0,10);
    const hasToday = (DASH.events||[]).some(e=>e.date===todayISO);
    if(hasToday) openDate(todayISO); else clearEventDetails();
  }

  // KPIs
  function renderKPIs(){
    const k = DASH.kpis || {};
    setText('#valActive', k.total_active_requests ?? 0);
    setText('#valAssetsPending', k.assets_pending ?? 0);
    setText('#valUnassigned', k.unassigned_tasks ?? 0);
    setText('#valEvents', k.total_events_supported ?? 0);
  }

  // Notifications list
  function renderNotifications(filter='all'){
    const container = $('#eventDetailsList');
    const all = DASH.event_details?.length ? DASH.event_details : (DASH.events||[]);

    const items = all.filter(e=>{
      if(filter==='all') return true;
      if(filter==='posters') return !!e.poster_required;
      if(filter==='certificates') return !!e.certificates_required;
      // coverage/media not present in API yet → return false
      if(filter==='coverage' || filter==='media') return false;
      return true;
    });

    if(!items.length){ container.innerHTML = '<div class="empty">No notifications</div>'; return; }
    container.innerHTML = items.map(e=>{
      const dateStr = e.date ? new Date(e.date).toLocaleDateString(undefined,{day:'2-digit',month:'short'}) : '—';
      const org = e.organization ? ` • ${esc(e.organization)}` : '';
      const link = `/cdl/support/?eventId=${e.id}`;
      return `<article class="list-item">
        <div class="bullet under_review"><i class="fa-regular fa-bell"></i></div>
        <div class="list-body">
          <h4>${esc(e.title||'Event')}</h4>
          <p>${dateStr}${org}</p>
        </div>
        <div class="btn-group"><a class="chip-btn" href="${link}"><i class="fa-regular fa-eye"></i> View</a></div>
      </article>`;
    }).join('');
  }

  // Team/Workload chart
  function renderChart(view='workload'){
    const ctx = $('#teamChart'); if(!ctx) return;
    chart?.destroy();
    if(view!=='workload'){
      chart = new Chart(ctx, {
        type: 'line',
        data: {
          labels: ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'],
          datasets: [{ data: [null,null,null,null,null,null,null], tension: 0.3 }]
        },
        options: {
          plugins: { legend: { display: false } },
          scales: { y: { beginAtZero: true, max: 100 } }
        }
      });
      return;
    }
    const labels = (DASH.workload?.members || []).map(n=> (n&&n.length>12)? (n.slice(0,11)+'…'): n);
    const data = DASH.workload?.assignments || [];
    chart = new Chart(ctx, { type:'bar', data:{ labels, datasets:[{ data, backgroundColor:'#4169e1' }] }, options:{ plugins:{legend:{display:false}}, scales:{y:{beginAtZero:true, precision:0}} } });
  }

  // Calendar
  function buildCalendar(){
    $('#calTitle').textContent = calRef.toLocaleString(undefined,{month:'long',year:'numeric'});
    const first=new Date(calRef.getFullYear(),calRef.getMonth(),1), last=new Date(calRef.getFullYear(),calRef.getMonth()+1,0);
    const startIdx=first.getDay(), prevLast=new Date(calRef.getFullYear(),calRef.getMonth(),0).getDate();
    const cells=[];
    for(let i=startIdx-1;i>=0;i--) cells.push({t:prevLast-i, iso:null, muted:true});
    for(let d=1; d<=last.getDate(); d++) cells.push({t:d, iso:iso(calRef,d), muted:false});
    while(cells.length%7!==0) cells.push({t:'', iso:null, muted:true});
    const todayISO = new Date().toISOString().slice(0,10);
    $('#calGrid').innerHTML = cells.map(c=>{
      if(!c.iso){ return `<div class="day muted" data-date="">${c.t}</div>`; }
      const has = (DASH.events||[]).some(e=>e.date===c.iso);
      const isToday = c.iso===todayISO;
      return `<div class="day${has?' has-event':''}${isToday?' today':''}" data-date="${c.iso}">${c.t}</div>`;
    }).join('');
    $$('#calGrid .day[data-date]').forEach(d=> d.addEventListener('click',()=>{
      $$('#calGrid .day.selected').forEach(x=>x.classList.remove('selected'));
      d.classList.add('selected');
      openDate(d.dataset.date);
    }));
  }
  function iso(base,d){ return `${base.getFullYear()}-${String(base.getMonth()+1).padStart(2,'0')}-${String(d).padStart(2,'0')}`; }

  function openDate(iso){
    const items = (DASH.event_details||[]).filter(e=>e.date===iso);
    const wrap = $('#eventDetailsContent');
    if(!items.length){ wrap.innerHTML = '<div class="empty">No events on this date</div>'; $('#clearEventDetails')?.style.setProperty('display','inline-flex'); return; }
    const dateStr = new Date(iso).toLocaleDateString(undefined,{day:'2-digit',month:'2-digit',year:'numeric'});
    wrap.innerHTML = items.map(e=>`
      <div class="event-detail-item">
        <div class="event-detail-title with-actions">
          <span class="title-text">${esc(e.title||'Event')}</span>
          <div class="title-actions"><a class="chip-btn" href="/cdl/support/?eventId=${e.id}">View</a></div>
        </div>
        <div class="event-detail-meta">${dateStr} • Status: ${esc(e.status||'')}${e.organization?` • ${esc(e.organization)}`:''}${e.assigned_member?` • Assigned to: ${esc(e.assigned_member)}`:''}</div>
      </div>
    `).join('');
    $('#clearEventDetails')?.style.setProperty('display','inline-flex');
  }

  function clearEventDetails(){
    $('#eventDetailsContent').innerHTML = '<div class="empty">Select a date in the calendar to view events</div>';
    $('#clearEventDetails')?.style.setProperty('display','none');
    $$('#calGrid .day.selected').forEach(x=>x.classList.remove('selected'));
  }

  // Utilities
  function setText(sel,v){ const el=$(sel); if(el) el.textContent = v; }
  function esc(s){ return (s??'').toString().replace(/[&<>"']/g,m=>({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;' }[m])); }

  async function fetchJSON(url, options={}){
    const res = await fetch(url, { credentials:'same-origin', headers:{ 'Accept':'application/json', ...(options.headers||{}) }, ...options });
    if(res.status===401 || res.status===403){ window.location.href = '/accounts/login/?next='+encodeURIComponent(location.pathname); throw new Error('auth'); }
    const ct = res.headers.get('content-type')||'';
    if(!ct.includes('application/json')){ window.location.href = '/accounts/login/?next='+encodeURIComponent(location.pathname); throw new Error('non-json'); }
    return res.json();
  }
})();
