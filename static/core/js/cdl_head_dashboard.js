(function () {
    const $ = (s, r = document) => r.querySelector(s);
    const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
  
    const NOTIFS = [
      {id:101, type:'poster',       title:'Business Summit — Poster',       priority:'Urgent',  due:'2025-08-18'},
      {id:102, type:'certificate',  title:'Tech Fest — Certificates',       priority:'Normal',  due:'2025-08-20'},
      {id:103, type:'coverage',     title:'AI Workshop — Coverage',         priority:'Normal',  due:'2025-08-19'},
      {id:104, type:'media',        title:'Cultural Night — Media Upload',  priority:'Urgent',  due:'2025-08-17'},
    ];
    let ASSIGN_LIST = [];
  
    const EVENTS = (()=>{
      try { return JSON.parse(document.getElementById('calendarEventsJson').textContent) || []; }
      catch { return [
        {id:1, title:'Coverage: Business Summit', date:'2025-08-18', type:'coverage', member:'Priya'},
        {id:2, title:'Poster Approval: Tech Fest', date:'2025-08-20', type:'approval'},
        {id:3, title:'Coverage: Cultural Night', date:'2025-08-17', type:'coverage', member:'John'},
      ]; }
    })();
  
    function computeKPIs(){
      const totalActive = NOTIFS.length + ASSIGN_LIST.length;
      const assetsPending = 0;
      const unassignedTasks = ASSIGN_LIST.filter(x=>!x.assignee).length;
      const eventsSupported = 0;
      $('#valActive').textContent = totalActive;
      $('#valAssetsPending').textContent = assetsPending;
      $('#valUnassigned').textContent = unassignedTasks;
      $('#valEvents').textContent = eventsSupported;
    }
  
    // KPIs shortcuts
    $('#kpiActive')?.addEventListener('click', ()=> document.querySelector('#cardNotifications')?.scrollIntoView({behavior:'smooth'}));
    $('#kpiUnassigned')?.addEventListener('click', ()=>{ setAMFilter('unassigned'); document.querySelector('#cardAssignAll')?.scrollIntoView({behavior:'smooth'}); });
  
    // Notifications
    let currentNotifFilter = 'all';
    function renderNotifications(filter='all'){
      const list = $('#notifList');
      const empty = $('#notifEmpty');
      const rows = NOTIFS
        .filter(n => filter==='all' ? true : n.type === filter.slice(0,-1))
        .map(n => `
          <article class="list-item" data-id="${n.id}" data-type="${n.type}">
            <div class="bullet under_review"><i class="fa-regular fa-bell"></i></div>
            <div class="list-body">
              <h4>${n.title}</h4>
              <p>Priority: ${n.priority} · Due: ${fmt(n.due)}</p>
            </div>
            <div class="btn-group">
              <button class="chip-btn success" data-nact="approve"><i class="fa-solid fa-check"></i> Approve</button>
              <button class="chip-btn warn" data-nact="decline"><i class="fa-solid fa-xmark"></i> Decline</button>
            </div>
          </article>
        `).join('');
      list.innerHTML = rows;
      empty.style.display = rows ? 'none' : 'block';
  
      list.querySelectorAll('[data-nact]').forEach(btn=>{
        btn.addEventListener('click', e=>{
          const item = e.currentTarget.closest('.list-item');
          const id = +item.dataset.id;
          const act = e.currentTarget.dataset.nact;
  
          if (act==='approve') {
            const n = NOTIFS.find(x=>x.id===id);
            if (n) {
              ASSIGN_LIST.unshift({
                id:n.id, event:n.title.split(' — ')[0],
                type:n.type, priority:n.priority, due:n.due,
                assignee:null, status:'Pending', rev:0
              });
            }
            const idx = NOTIFS.findIndex(x=>x.id===id);
            if (idx>-1) NOTIFS.splice(idx,1);
            renderNotifications(currentNotifFilter);
            renderAssignTable();
            computeKPIs();
          }
  
          if (act==='decline') {
            const idx = NOTIFS.findIndex(x=>x.id===id);
            if (idx>-1) NOTIFS.splice(idx,1);
            renderNotifications(currentNotifFilter);
            computeKPIs();
          }
        });
      });
    }
    $$('.seg-btn[data-nf]').forEach(b=>{
      b.addEventListener('click', e=>{
        $$('.seg-btn[data-nf]').forEach(x=>x.classList.remove('active'));
        e.currentTarget.classList.add('active');
        currentNotifFilter = e.currentTarget.dataset.nf;
        renderNotifications(currentNotifFilter);
      });
    });
  
    // Assignment Manager
    let amFilter = 'all';
    function setAMFilter(f){ amFilter = f; $$('.seg-btn[data-am]').forEach(b=> b.classList.toggle('active', b.dataset.am===f)); renderAssignTable(); }
  
    function renderAssignTable(){
      const tb = $('#assignBody');
      const now = new Date();
      const rows = ASSIGN_LIST
        .filter(r=>{
          if (amFilter==='all') return true;
          if (amFilter==='unassigned') return !r.assignee;
          if (amFilter==='urgent') return r.priority==='Urgent';
          if (amFilter==='due24'){ const ms = new Date(r.due) - now; return ms>=0 && ms<=24*60*60*1000; }
          return true;
        })
        .map(r=>{
          const pr = r.priority==='Urgent' ? 'danger' : 'amber';
          const st = r.status==='Pending' ? 'warn' : (r.status==='In Review' ? 'info' : (r.status==='Approved'?'success':'gray'));
          const ass = r.assignee ? r.assignee : '<span class="chip gray">Unassigned</span>';
          return `
          <tr data-id="${r.id}">
            <td><input type="checkbox" class="amRow"></td>
            <td>${r.event}</td>
            <td>${cap(r.type)}</td>
            <td><span class="chip ${pr}">${r.priority}</span></td>
            <td>${fmt(r.due)}</td>
            <td>${ass}</td>
            <td><span class="chip ${st}">${r.status}</span></td>
            <td>${r.rev}</td>
            <td class="ta-right">
              <button class="btn xs" data-am="assign">Assign</button>
              <button class="btn xs success" data-am="approve">Approve</button>
              <button class="btn xs warn" data-am="return">Return</button>
            </td>
          </tr>`;
        }).join('');
      tb.innerHTML = rows || `<tr><td colspan="9">No items</td></tr>`;
  
      tb.querySelectorAll('[data-am]').forEach(b=>{
        b.addEventListener('click', e=>{
          const tr = e.currentTarget.closest('tr');
          const id = +tr.dataset.id;
          const act = e.currentTarget.dataset.am;
          const row = ASSIGN_LIST.find(x=>x.id===id);
          if (!row) return;
          if (act==='assign'){ row.assignee = prompt('Assign to (name)?') || row.assignee; }
          if (act==='approve'){ row.status = 'Approved'; }
          if (act==='return'){ row.status = 'Returned'; row.rev += 1; }
          renderAssignTable(); computeKPIs();
        });
      });
    }
  
    $$('.seg-btn[data-am]').forEach(b=> b.addEventListener('click', ()=> setAMFilter(b.dataset.am)));
    $('#amSelectAll')?.addEventListener('change', e=> $$('#assignBody .amRow').forEach(cb=> cb.checked = e.target.checked));
    $('#amBulkAssign')?.addEventListener('click', ()=>{ const name = prompt('Assign selected to (name)?'); if(!name) return; getSel().forEach(id=>{ const r=ASSIGN_LIST.find(x=>x.id===id); if(r) r.assignee=name; }); renderAssignTable(); computeKPIs(); });
    $('#amBulkApprove')?.addEventListener('click', ()=>{ getSel().forEach(id=>{ const r=ASSIGN_LIST.find(x=>x.id===id); if(r) r.status='Approved'; }); renderAssignTable(); computeKPIs(); });
    $('#amBulkReturn')?.addEventListener('click', ()=>{ getSel().forEach(id=>{ const r=ASSIGN_LIST.find(x=>x.id===id); if(r){ r.status='Returned'; r.rev+=1; } }); renderAssignTable(); computeKPIs(); });
    const getSel = ()=> $$('#assignBody .amRow:checked').map(cb=> +cb.closest('tr').dataset.id);
  
    // Team Analytics
    let teamChart;
    function buildTeamChart(labels, data, title){
      const ctx = $('#teamChart'); if(!ctx) return;
      teamChart?.destroy();
      teamChart = new Chart(ctx, {
        type: 'bar',
        data: { labels, datasets:[{ data, borderWidth:0 }] },
        options: { plugins:{legend:{display:false}}, responsive:true, maintainAspectRatio:false, scales:{y:{beginAtZero:true}} }
      });
      $('#teamTitle').textContent = title;
    }
    function viewWorkload(){ buildTeamChart(['John','Priya','Aarav','Meera'], [5,8,3,6], 'Workload Distribution'); }
    function viewOnTime(){ buildTeamChart(['John','Priya','Aarav','Meera'], [82,74,91,69], 'On-time Completion (%)'); }
    function viewFirstPass(){ buildTeamChart(['John','Priya','Aarav','Meera'], [64,71,55,77], 'First-pass Approval (%)'); }
    $$('.seg-btn[data-view]').forEach(b=>{
      b.addEventListener('click', e=>{
        $$('.seg-btn[data-view]').forEach(x=>x.classList.remove('active'));
        e.currentTarget.classList.add('active');
        const v = e.currentTarget.dataset.view;
        if(v==='workload') viewWorkload();
        if(v==='ontime') viewOnTime();
        if(v==='firstpass') viewFirstPass();
      });
    });
  
    // Calendar
    let calRef = new Date();
    const fmt2 = v => String(v).padStart(2,'0');
    const titleEl = $('#calTitle'), gridEl = $('#calGrid'), upcoming = $('#upcomingWrap');
  
    function buildCalendar(){
      if(!gridEl||!titleEl) return;
      titleEl.textContent = calRef.toLocaleString(undefined,{month:'long',year:'numeric'});
      const first = new Date(calRef.getFullYear(), calRef.getMonth(), 1);
      const last  = new Date(calRef.getFullYear(), calRef.getMonth()+1, 0);
      const startIdx = first.getDay();
      const prevLast = new Date(calRef.getFullYear(), calRef.getMonth(), 0).getDate();
      const cells = [];
      for(let i=startIdx-1;i>=0;i--) cells.push({t: prevLast - i, iso:null, muted:true});
      for(let d=1; d<=last.getDate(); d++){
        const iso = `${calRef.getFullYear()}-${fmt2(calRef.getMonth()+1)}-${fmt2(d)}`;
        cells.push({t:d, iso, muted:false});
      }
      while(cells.length%7!==0) cells.push({t:'',iso:null, muted:true});
  
      gridEl.innerHTML = cells.map(c=>{
        const dots = buildDots(c.iso);
        return `<div class="day${c.muted?' muted':''}" data-date="${c.iso||''}">
          <div class="num">${c.t}</div>
          <div class="dots">${dots}</div>
        </div>`;
      }).join('');
  
      $$('#calGrid .day[data-date]').forEach(d=> d.addEventListener('click', ()=> {
        // highlight selection
        $$('#calGrid .day.selected').forEach(x=>x.classList.remove('selected'));
        d.classList.add('selected');
        openDay(d.dataset.date);
      }));
    }
    function buildDots(iso){
      if(!iso) return '';
      const list = EVENTS.filter(e=>e.date===iso);
      const hasConflict = (()=>{ const m={}; list.forEach(e=>{ if(e.member){ m[e.member]=(m[e.member]||0)+1; }}); return Object.values(m).some(v=>v>1); })();
      return list.map(e=>`<span class="dot ${e.type==='coverage'?'blue':'green'}"></span>`).join('') + (hasConflict? `<span class="dot red" title="Conflict"></span>`:'');
    }
    function openDay(iso){
      const items = EVENTS.filter(e=>e.date===iso);
      upcoming.innerHTML = items.length ? items.map(e=>`
        <div class="u-item">
          <div>${e.title}</div>
          <a class="chip-btn" href="/proposal/${e.id}/detail/"><i class="fa-regular fa-eye"></i> View</a>
        </div>
      `).join('') : `<div class="empty">No items for ${new Date(iso).toLocaleDateString()}</div>`;
    }
    $('#calPrev')?.addEventListener('click', ()=>{ calRef = new Date(calRef.getFullYear(), calRef.getMonth()-1, 1); buildCalendar(); });
    $('#calNext')?.addEventListener('click', ()=>{ calRef = new Date(calRef.getFullYear(), calRef.getMonth()+1, 1); buildCalendar(); });
    $('#addEventBtn')?.addEventListener('click', (e)=>{
      const scope = $('#calFilter')?.value || 'all';
      e.currentTarget.href = `/suite/submit/?via=dashboard&scope=${encodeURIComponent(scope)}`;
    });
  
    // Utils
    function cap(s){ return s ? s.charAt(0).toUpperCase()+s.slice(1) : s; }
    function fmt(iso){ const d=new Date(iso); return d.toLocaleString(undefined,{month:'short',day:'2-digit'}); }
  
    document.addEventListener('DOMContentLoaded', ()=>{
      computeKPIs();
      renderNotifications('all');
      setAMFilter('all');
      renderAssignTable();
      viewWorkload();
      buildCalendar();
      openDay(new Date().toISOString().slice(0,10));
    });
  })();
  