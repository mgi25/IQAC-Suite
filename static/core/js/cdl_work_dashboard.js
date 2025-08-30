(function(){
    const $  = (s, r=document)=>r.querySelector(s);
    const $$ = (s, r=document)=>Array.from(r.querySelectorAll(s));
  const INBOX  = getJSON('memberInboxJson', []);
  const WORK   = getJSON('memberWorkJson', []);
    const EVENTS = getJSON('memberEventsJson', []);
    const STATS  = getJSON('memberStatsJson', {ontime:null, firstpass:null});
  
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
            <button class="chip-btn success" data-act="accept"><i class="fa-solid fa-check"></i> Accept</button>
            <button class="chip-btn warn" data-act="decline"><i class="fa-solid fa-xmark"></i> Decline</button>
          </div>
        </article>`).join('');
      list.innerHTML = rows;
      empty.style.display = rows ? 'none' : 'block';
      list.querySelectorAll('[data-act]').forEach(b=>{
        b.addEventListener('click', e=>{
          const id = +e.currentTarget.closest('.list-item').dataset.id;
          if(e.currentTarget.dataset.act==='accept'){
            const s = INBOX.find(x=>x.id===id);
            if(s && !WORK.some(w=>w.id===s.id)){
              WORK.unshift({id:s.id,event:s.event||s.title||'Untitled',type:s.type,priority:s.priority||'Medium',due_date:s.due_date,status:'pending',rev:0});
            }
          }
          const i = INBOX.findIndex(x=>x.id===id); if(i>-1) INBOX.splice(i,1);
          renderInbox(currentFilter); renderWork(); computeKPIs();
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
    $('#calPrev')?.addEventListener('click',()=>{ calRef = new Date(calRef.getFullYear(),calRef.getMonth()-1,1); buildCalendar(); });
    $('#calNext')?.addEventListener('click',()=>{ calRef = new Date(calRef.getFullYear(),calRef.getMonth()+1,1); buildCalendar(); });
    function buildCalendar(){
      $('#calTitle').textContent = calRef.toLocaleString(undefined,{month:'long',year:'numeric'});
      const first=new Date(calRef.getFullYear(),calRef.getMonth(),1), last=new Date(calRef.getFullYear(),calRef.getMonth()+1,0);
      const startIdx=first.getDay(), prevLast=new Date(calRef.getFullYear(),calRef.getMonth(),0).getDate();
      const cells=[];
      for(let i=startIdx-1;i>=0;i--) cells.push({t:prevLast-i, muted:true});
      for(let d=1; d<=last.getDate(); d++) cells.push({t:d, iso:iso(calRef,d)});
      while(cells.length%7!==0) cells.push({t:'', muted:true});
      $('#calGrid').innerHTML = cells.map(c=>`<div class="day${c.muted?' muted':''}" data-date="${c.iso||''}"><div class="num">${c.t}</div><div class="dots">${buildDots(c.iso)}</div></div>`).join('');
      $$('#calGrid .day[data-date]').forEach(d=> d.addEventListener('click',()=>{
        $$('#calGrid .day.selected').forEach(x=>x.classList.remove('selected'));
        d.classList.add('selected');
        openDay(d.dataset.date);
      }));
    }
    function iso(base,d){ return `${base.getFullYear()}-${String(base.getMonth()+1).padStart(2,'0')}-${String(d).padStart(2,'0')}`; }
    function buildDots(iso){ if(!iso) return ''; const list=EVENTS.filter(e=>e.date===iso); return list.map(e=>`<span class="dot ${e.type==='coverage'?'blue':'green'}"></span>`).join(''); }
    function openDay(iso){ const items=EVENTS.filter(e=>e.date===iso); $('#upcomingWrap').innerHTML = items.length? items.map(e=>`<div class="u-item"><div>${esc(e.title||'Event')}</div></div>`).join('') : `<div class="empty">No items</div>`; }
  
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
        const stc=r.status==='waiting'?'info':(r.status==='in_progress'?'warn':(r.status==='returned'?'danger':'gray'));
        return `<tr data-id="${r.id}">
          <td><input type="checkbox" class="wbRow"></td>
          <td>${esc(r.event)}</td>
          <td>${cap(r.type||'')}</td>
          <td><span class="chip ${pr}">${esc(r.priority||'Medium')}</span></td>
          <td>${fmt(r.due_date)}</td>
          <td><span class="chip ${stc}">${cap((r.status||'pending').replace('_',' '))}</span></td>
          <td>${r.rev ?? 0}</td>
          <td class="ta-right">${rowActions(r)}</td>
        </tr>`;
      }).join('') || `<tr><td colspan="8">No items</td></tr>`;
      tb.querySelectorAll('[data-act]').forEach(b=>{
        b.addEventListener('click', e=>{
          const tr=e.currentTarget.closest('tr'); const id=+tr.dataset.id; const row=WORK.find(x=>x.id===id); if(!row) return;
          const act=e.currentTarget.dataset.act;
          if(act==='start') row.status='in_progress';
          if(act==='pause') row.status='pending';
          if(act==='submit') row.status='waiting';
          if(act==='help') {/* hook help endpoint */}
          renderWork(); computeKPIs();
        });
      });
    }
    function rowActions(r){
      const toggle=r.status==='in_progress'
        ? `<button class="btn xs" data-act="pause"><i class="fa-regular fa-circle-pause"></i> Pause</button>`
        : `<button class="btn xs" data-act="start"><i class="fa-regular fa-circle-play"></i> Start</button>`;
      return `${toggle}
        <button class="btn xs success" data-act="submit"><i class="fa-solid fa-paper-plane"></i> Submit</button>
        <button class="btn xs warn" data-act="help"><i class="fa-regular fa-circle-question"></i> Help</button>`;
    }
  
    // Bulk
    $('#wbAll')?.addEventListener('change', e=> $$('#workTable .wbRow').forEach(cb=> cb.checked=e.target.checked));
    $('#bulkSubmit')?.addEventListener('click', ()=>{ $$('#workTable .wbRow:checked').forEach(cb=>{ const id=+cb.closest('tr').dataset.id; const r=WORK.find(x=>x.id===id); if(r) r.status='waiting';}); renderWork(); computeKPIs(); });
    $('#bulkUpload')?.addEventListener('click', ()=> alert('Open bulk uploader'));
    $('#bulkHelp')?.addEventListener('click', ()=> alert('Help requested'));
  
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
  
    async function bootstrap(){
      try{
        const res = await fetch('/api/cdl/member/work/');
        if(res.ok){ const data=await res.json(); if(data && data.items){
          // Merge unique by id at the front
          const ids = new Set(WORK.map(w=>w.id));
          (data.items||[]).forEach(it=>{ if(!ids.has(it.id)) WORK.unshift(it); });
        } }
      }catch{}
      computeKPIs(); renderInbox('all'); renderChart('workload'); buildCalendar(); openDay(new Date().toISOString().slice(0,10)); renderWork();
    }
    // Boot
    bootstrap();
  })();
  