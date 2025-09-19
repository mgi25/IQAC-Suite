(function(){
    const $  = (s, r=document)=>r.querySelector(s);
    const $$ = (s, r=document)=>Array.from(r.querySelectorAll(s));
  let INBOX = [];
  let WORK = [];
  let EVENTS_ALL = [];
  let EVENTS_ASSIGNED = [];
  let STATS = {ontime:null, firstpass:null};
  
    // KPIs
    function computeKPIs(){
      setText('#valAssigned', WORK.length);
      setText('#valDueToday', WORK.filter(isDueToday).length);
      setText('#valWaiting',  WORK.filter(r=>r.status==='waiting').length);
      setText('#valRework',   WORK.filter(r=>r.status==='returned').length);
      setText('#pfOntime',    pct(STATS.ontime));
      setText('#pfFirstpass', pct(STATS.firstpass));
    }
    function isDueToday(r){ const d=new Date(r.due_date); const t=new Date(); t.setHours(0,0,0,0); d.setHours(0,0,0,0); return d.getTime()===t.getTime(); }
  
    // Inbox
    function renderInbox(filter='all'){
      const list = $('#inboxList'), empty=$('#inboxEmpty');
      const rows = INBOX.filter(n => filter==='all' ? true : n.type===filter).map(n => `
        <article class="list-item" data-id="${n.id}">
          <div class="bullet under_review"><i class="fa-regular fa-envelope"></i></div>
          <div class="list-body">
            <h4>${esc(n.title || n.event || 'Untitled')}</h4>
            <p>Priority: ${esc(n.priority||'Normal')} · Due: ${fmt(n.due_date)}</p>
          </div>
          <div class="btn-group">
            ${n.accepted ? `<a class="chip-btn" data-act="view" href="/cdl/support/?eventId=${n.id}"><i class="fa-regular fa-eye"></i> View Details</a>` : '<button class="chip-btn success" data-act="accept"><i class="fa-solid fa-check"></i> Accept</button>'}
          </div>
        </article>`).join('');
      list.innerHTML = rows;
      empty.style.display = rows ? 'none' : 'block';
      list.querySelectorAll('[data-act]').forEach(b=>{
        b.addEventListener('click', e=>{
          const id = +e.currentTarget.closest('.list-item').dataset.id;
          const act = e.currentTarget.dataset.act;
          if(act==='accept'){
            acceptAssignment(id).then(res=>{
              if(res && res.success){
                const s = INBOX.find(x=>x.id===id);
                if(s && !WORK.some(w=>w.id===s.id)){
                  WORK.unshift({id:s.id,event:s.event||s.title||'Untitled',type:s.type,priority:s.priority||'Medium',due_date:s.due_date,status:'pending',rev:0});
                }
                if(s){ s.accepted = true; }
                renderInbox(currentFilter); renderWork(); computeKPIs();
              }else{
                alert((res && res.error) ? res.error : 'Could not accept this assignment.');
              }
            });
          }
        });
      });
    }
    let currentFilter='all';
    $$('#cardInbox .seg-btn').forEach(b=>{
      b.addEventListener('click', e=>{
        $$('#cardInbox .seg-btn').forEach(x=>x.classList.remove('active'));
        e.currentTarget.classList.add('active');
        currentFilter = e.currentTarget.dataset.nf;
        renderInbox(currentFilter);
      });
    });
  
    // Progress
    let chart;
    function renderChart(view='workload'){
      const ctx = $('#memberChart'); if(!ctx) return;
      chart?.destroy();
      if(view==='ontime'){
        chart = new Chart(ctx,{type:'line',data:{labels:last7Labels(),datasets:[{data:last7(STATS.ontime_history||[]),tension:.3}]},options:{plugins:{legend:{display:false}},scales:{y:{beginAtZero:true,max:100}}}});
        return;
      }
      if(view==='firstpass'){
        chart = new Chart(ctx,{type:'line',data:{labels:last7Labels(),datasets:[{data:last7(STATS.firstpass_history||[]),tension:.3}]},options:{plugins:{legend:{display:false}},scales:{y:{beginAtZero:true,max:100}}}});
        return;
      }
      const days=['Mon','Tue','Wed','Thu','Fri','Sat','Sun']; const counts=days.map(()=>0);
      (WORK||[]).forEach(w=>{ const d=new Date(w.created_at||w.assigned_at||Date.now()); counts[d.getDay()===0?6:d.getDay()-1]+=1; });
      chart = new Chart(ctx,{type:'bar',data:{labels:days,datasets:[{data:counts}]},options:{plugins:{legend:{display:false}},scales:{y:{beginAtZero:true}}}});
    }
    $$('#cardProgress .seg-btn').forEach(b=>{
      b.addEventListener('click', e=>{
        $$('#cardProgress .seg-btn').forEach(x=>x.classList.remove('active'));
        e.currentTarget.classList.add('active');
        renderChart(e.currentTarget.dataset.view);
      });
    });
  
    // Calendar
  let calRef = new Date();
  let calScope = 'all'; // 'all' | 'assigned'
    $('#calPrev')?.addEventListener('click',()=>{ calRef = new Date(calRef.getFullYear(),calRef.getMonth()-1,1); buildCalendar(); });
    $('#calNext')?.addEventListener('click',()=>{ calRef = new Date(calRef.getFullYear(),calRef.getMonth()+1,1); buildCalendar(); });
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
        const list = (calScope==='assigned'? EVENTS_ASSIGNED : EVENTS_ALL);
        const has = list.some(e=>e.date===c.iso && (e.status||'').toLowerCase()==='finalized');
        const isToday = c.iso===todayISO;
        const klass = has? (calScope==='assigned' ? ' has-meeting' : ' has-event') : '';
        return `<div class="day${klass}${isToday?' today':''}" data-date="${c.iso}">${c.t}</div>`;
      }).join('');
      $$('#calGrid .day[data-date]').forEach(d=> d.addEventListener('click',()=>{
        $$('#calGrid .day.selected').forEach(x=>x.classList.remove('selected'));
        d.classList.add('selected');
        openDay(d.dataset.date);
      }));
      // After build, if first run, lock heights
      requestAnimationFrame(()=>{
        const calCard = document.querySelector('#cardCalendar');
        if(calCard){
          const h = calCard.getBoundingClientRect().height;
          // Cap to a smaller maximum to reduce excess whitespace
          const target = Math.min(h, 420); // shrink if larger
          if(target>0){ document.documentElement.style.setProperty('--calH', target+'px'); }
          ['#cardInbox','#cardProgress','#cardCalendar'].forEach(sel=>{ const el=document.querySelector(sel); if(el && !el.classList.contains('eq-height')) el.classList.add('eq-height'); });
        }
      });
    }
    function iso(base,d){ return `${base.getFullYear()}-${String(base.getMonth()+1).padStart(2,'0')}-${String(d).padStart(2,'0')}`; }
  function openDay(iso){
      const list = (calScope==='assigned'? EVENTS_ASSIGNED : EVENTS_ALL);
      const items=list.filter(e=>e.date===iso && (e.status||'').toLowerCase()==='finalized');
      const wrap = $('#eventDetailsContent');
      if(!items.length){ wrap.innerHTML = `<div class="empty">No events on this date</div>`; $('#clearEventDetails')?.style.setProperty('display','inline-flex'); return; }
      const dateStr = new Date(iso).toLocaleDateString(undefined,{day:'2-digit',month:'2-digit',year:'numeric'});
      wrap.innerHTML = items.map(e=>`
        <div class="event-detail-item">
          <div class="event-detail-title with-actions">
            <span class="title-text">${esc(e.title||'Event')}</span>
            <div class="title-actions"><a class="chip-btn" href="/cdl/support/?eventId=${e.id}">View</a></div>
          </div>
          <div class="event-detail-meta">${dateStr} • Status: ${esc(e.status||'')}${e.assigned_role?` • Role: ${esc(e.assigned_role)}`:''}${e.assigned_by?` • Assigned by: ${esc(e.assigned_by)}`:''}</div>
        </div>`).join('');
      $('#clearEventDetails')?.style.setProperty('display','inline-flex');
    }
    function clearEventDetails(){
      $('#eventDetailsContent').innerHTML = '<div class="empty">Select a date in the calendar to view events</div>';
      $('#clearEventDetails')?.style.setProperty('display','none');
      $$('#calGrid .day.selected').forEach(x=>x.classList.remove('selected'));
    }
  
    // Workboard
    function renderWork(){
      const q=($('#wbSearch').value||'').toLowerCase(); const st=$('#wbStatus').value; const due=$('#wbDue').value;
      const rows=WORK.filter(r=>{
        if(q && !(`${r.event} ${r.type} ${r.status}`.toLowerCase().includes(q))) return false;
        if(st && r.status!==st) return false;
        const d=new Date(r.due_date), t=new Date(); t.setHours(0,0,0,0);
        if(due==='today'  && d.setHours(0,0,0,0)!==t.getTime()) return false;
        if(due==='week'   && !inWeek(d)) return false;
        if(due==='overdue'&& d < t) return false;
        return true;
      });
      const tb=$('#workTable');
      tb.innerHTML = rows.map(r=>{
        const pr=(r.priority||'Medium')==='High'?'danger':((r.priority||'Medium')==='Low'?'success':'amber');
        // Include 'done' status for resource tasks so it renders consistently
        const stc=r.status==='waiting'?'info':(r.status==='in_progress'?'warn':(r.status==='returned'?'danger':(r.status==='done'?'success':'gray')));
        return `<tr data-id="${r.id}">
          <td>${esc(r.event)}</td>
          <td>${cap(r.type||'')}</td>
          <td><span class="chip ${pr}">${esc(r.priority||'Medium')}</span></td>
          <td>${fmt(r.due_date)}</td>
          <td><span class="chip ${stc}">${cap((r.status||'pending').replace('_',' '))}</span></td>
          <td>${r.rev ?? 0}</td>
          <td class="ta-right">${rowActions(r)}</td>
        </tr>`;
      }).join('') || `<tr><td colspan="7">No items</td></tr>`;
      tb.querySelectorAll('[data-act]').forEach(b=>{
        b.addEventListener('click', e=>{
          const tr=e.currentTarget.closest('tr'); const id=+tr.dataset.id; if(!id) return;
          const act=e.currentTarget.dataset.act;
          if(act==='chat'){ window.location.href = `/cdl/communication/?eventId=${id}`; }
          // 'update' is now a direct link (anchor), no JS action needed
        });
      });
    }
    function rowActions(r){
      const view=`<a class="btn xs" href="/cdl/support/?eventId=${r.id}"><i class="fa-regular fa-eye"></i> View</a>`;
      const chat=`<button class="btn xs" data-act="chat"><i class="fa-regular fa-comments"></i> Chat</button>`;
      const update=`<a class="btn xs success" href="/cdl/support/${r.id}/assign/?eventId=${r.id}&mode=employee" data-act="update"><i class="fa-solid fa-pen-to-square"></i> Update Task</a>`;
      return `${view} ${chat} ${update}`;
    }
  
  // Bulk actions removed
  
    // Utilities
    function getJSON(id, fb){ try{ return JSON.parse(document.getElementById(id).textContent)||fb; }catch{ return fb; } }
    function setText(sel,v){ const el=$(sel); if(el) el.textContent=v; }
    function cap(s){ return s? s.charAt(0).toUpperCase()+s.slice(1):s; }
    function esc(s){ return (s??'').toString().replace(/[&<>"']/g,m=>({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;' }[m])); }
    function fmt(iso){ const d=new Date(iso); return isNaN(d)?'—':d.toLocaleString(undefined,{month:'short',day:'2-digit'}); }
    function pct(v){ return (v==null||isNaN(v))?'—':(Math.round(v)+'%'); }
    function last7(arr){ const a=arr.slice(-7); while(a.length<7)a.unshift(null); return a; }
    function last7Labels(){ return ['Mon','Tue','Wed','Thu','Fri','Sat','Sun']; }
    function inWeek(d){ const now=new Date(); const s=new Date(now); s.setDate(now.getDate()-((now.getDay()+6)%7)); s.setHours(0,0,0,0); const e=new Date(s); e.setDate(s.getDate()+7); return d>=s && d<e; }
    function getCookie(name){
      const m=document.cookie.match(new RegExp('(^|; )'+name.replace(/([.$?*|{}()\[\]\\\/\+^])/g,'\\$1')+'=([^;]*)'));
      return m? decodeURIComponent(m[2]): null;
    }
  
    async function bootstrap(){
      try{
        const res = await fetch('/api/cdl/member/data/');
        if(res.ok){ const data=await res.json(); if(data && data.success){
          INBOX = data.inbox||[];
          WORK  = data.work||[];
          STATS = {ontime:data.stats?.ontime ?? null, firstpass:data.stats?.firstpass ?? null};
          EVENTS_ALL = data.events_all||[];
          EVENTS_ASSIGNED = data.events_assigned||[];
        }}
  }catch{}
      computeKPIs(); renderInbox('all'); renderChart('workload'); buildCalendar(); openDay(new Date().toISOString().slice(0,10)); renderWork();
      // Bind clear button
      $('#clearEventDetails')?.addEventListener('click', clearEventDetails);
    }
    // Calendar scope selector
    document.addEventListener('change', e=>{
      if(e.target && e.target.id==='calScope'){ calScope = e.target.value; buildCalendar(); }
    });

    // Boot
    bootstrap();
    // Lightweight realtime: listen for updates signaled from Assign Tasks
    window.addEventListener('storage', (e)=>{
      if(e && e.key==='cdl_tasks_ping'){
        bootstrap();
      }
    });

    async function acceptAssignment(proposalId){
      try{
        const res = await fetch('/api/cdl/member/accept/', {
          method:'POST',
          headers:{'Content-Type':'application/json','Accept':'application/json','X-CSRFToken': getCookie('csrftoken')||''},
          body: JSON.stringify({proposal_id: proposalId})
        });
        const j = await res.json().catch(()=>({success:false,error:'Server error'}));
        if(!res.ok) return j;
        try{ localStorage.setItem('cdl_tasks_ping', String(Date.now())); }catch{}
        return j;
      }catch(e){ return {success:false,error:'Network error'}; }
    }

    // Instant cross-tab sync: refresh when Assign Tasks broadcasts a change
    window.addEventListener('storage', (e)=>{
      if(e && e.key==='cdl_tasks_ping'){
        bootstrap();
      }
    });
  })();
  