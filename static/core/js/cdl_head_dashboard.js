  (function () {
    const $ = (s, r = document) => r.querySelector(s);
    const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
  
    let EVENTS = [];
    let eventIndexByDate = new Map();
    let selectedDate = null;
    let currentFilter = 'all';
    let ASSIGN_LIST = [];

    function computeKPIs(){
      // Fetch dynamic KPI data
      fetchKPIs();
    }

    async function fetchKPIs() {
      try {
        const res = await fetch('/emt/api/head/kpis/', { headers: {'X-Requested-With':'XMLHttpRequest'} });
        const data = await res.json();
        $('#valActive').textContent = data.active || 0;
        $('#valAssetsPending').textContent = data.assets_pending || 0;
        $('#valUnassigned').textContent = data.unassigned || 0;
        $('#valEvents').textContent = data.events_supported || 0;
      } catch {
        // Fallback to computed values
        const totalActive = EVENTS.length;
        const unassignedTasks = ASSIGN_LIST.filter(x=>!x.assignee).length;
        $('#valActive').textContent = totalActive;
        $('#valAssetsPending').textContent = 0;
        $('#valUnassigned').textContent = unassignedTasks;
        $('#valEvents').textContent = 0;
      }
    }

    // KPIs shortcuts
    $('#kpiActive')?.addEventListener('click', ()=> document.querySelector('#cardNotifications')?.scrollIntoView({behavior:'smooth'}));
    $('#kpiUnassigned')?.addEventListener('click', ()=>{ setAMFilter('unassigned'); document.querySelector('#cardAssignAll')?.scrollIntoView({behavior:'smooth'}); });

    // Dynamic event notifications
    async function loadEvents() {
      try {
        const filter = currentFilter === 'support' ? 'support' : 'all';
        const res = await fetch(`/emt/api/calendar/role/?filter=${encodeURIComponent(filter)}`, { headers:{'X-Requested-With':'XMLHttpRequest'} });
        const j = await res.json();
        EVENTS = j.events || j.items || [];
        eventIndexByDate = new Map();
        EVENTS.forEach(e => {
          const date = new Date(e.datetime).toISOString().split('T')[0];
          const arr = eventIndexByDate.get(date) || [];
          arr.push(e);
          eventIndexByDate.set(date, arr);
        });
        renderNotifications();
        buildCalendar();
      } catch {
        EVENTS = [];
        eventIndexByDate = new Map();
        renderNotifications();
        buildCalendar();
      }
    }

    function renderNotifications() {
      const list = $('#notifList');
      const empty = $('#notifEmpty');
      const clearBtn = $('#clearNotifications');
      
      let eventsToShow = [];
      
      if (selectedDate) {
        // Filter events by selected date
        eventsToShow = EVENTS.filter(e => {
          const eventDate = new Date(e.datetime).toISOString().split('T')[0];
          return eventDate === selectedDate;
        });
        $('#notifTitle').textContent = `Events for ${new Date(selectedDate).toLocaleDateString()}`;
        clearBtn.style.display = 'inline-flex';
      } else {
        // Show all events based on current filter
        eventsToShow = EVENTS;
        $('#notifTitle').textContent = currentFilter === 'support' ? 'Support Required Events' : 'All Events';
        clearBtn.style.display = 'none';
      }

      if (eventsToShow.length === 0) {
        list.innerHTML = '';
        empty.style.display = 'block';
        empty.textContent = selectedDate ? 'No events for this date' : 'No events found';
        return;
      }

      empty.style.display = 'none';
      list.innerHTML = eventsToShow.map(e => `
        <article class="list-item" data-id="${e.id}">
          <div class="bullet under_review"><i class="fa-regular fa-calendar"></i></div>
          <div class="list-body">
            <h4>${esc(e.title || 'Event')}</h4>
            <p>${e.venue ? esc(e.venue) + ' · ' : ''}${e.datetime ? new Date(e.datetime).toLocaleDateString() : ''}</p>
          </div>
          <div class="btn-group">
            <button class="chip-btn" data-action="chat" data-id="${e.id}"><i class="fa-regular fa-comment"></i> Chat</button>
            <button class="chip-btn success" data-action="assign" data-id="${e.id}"><i class="fa-solid fa-user-plus"></i> Assign Work</button>
          </div>
        </article>
      `).join('');

      // Add event listeners for the buttons
      list.querySelectorAll('[data-action]').forEach(btn => {
        btn.addEventListener('click', e => {
          const eventId = e.currentTarget.dataset.id;
          const action = e.currentTarget.dataset.action;
          
          if (action === 'chat') {
            openEventChat(eventId);
          } else if (action === 'assign') {
            openAssignModal(eventId);
          }
        });
      });
    }

    // Event filter
    $('#eventViewFilter')?.addEventListener('change', e => {
      currentFilter = e.target.value;
      selectedDate = null; // Reset date selection
      loadEvents();
    });

    // Clear notifications
    $('#clearNotifications')?.addEventListener('click', () => {
      selectedDate = null;
      renderNotifications();
    });

    // Chat functionality
    function openEventChat(eventId) {
      const modal = $('#cdlHeadEventModal');
      const event = EVENTS.find(e => e.id == eventId);
      
      if (!event) return;
      
      currentProposalId = eventId;
      modal.style.display = 'flex';
      $('#cdlHeadMeta').textContent = `${event.title}${event.datetime ? ' · ' + new Date(event.datetime).toLocaleString() : ''}${event.venue ? ' · ' + event.venue : ''}`;
      
      // Hide assignment section, show only chat
      modal.querySelector('.form-row').style.display = 'block';
      modal.querySelector('.form-group:last-child').style.display = 'none';
      
      loadHeadChat();
    }

    // Assignment functionality
    async function openAssignModal(eventId) {
      const modal = $('#cdlHeadEventModal');
      const event = EVENTS.find(e => e.id == eventId);
      
      if (!event) return;
      
      currentProposalId = eventId;
      modal.style.display = 'flex';
      $('#cdlHeadMeta').textContent = `Assign Work: ${event.title}`;
      
      // Show assignment section, hide chat
      modal.querySelector('.form-row').style.display = 'block';
      modal.querySelector('.form-group:first-child').style.display = 'none';
      modal.querySelector('.form-group:last-child').style.display = 'block';
      
      // Load available members
      await loadMembers();
    }

    async function loadMembers() {
      try {
        const res = await fetch('/api/dashboard/people/', { headers: {'X-Requested-With':'XMLHttpRequest'} });
        const data = await res.json();
        
        // Replace user ID input with dropdown
        const assignToInput = $('#cdlAssignTo');
        if (assignToInput) {
          const select = document.createElement('select');
          select.id = 'cdlAssignTo';
          select.innerHTML = '<option value="">Select member...</option>' + 
            data.people
              .filter(p => p.role && p.role.toLowerCase().includes('member'))
              .map(p => `<option value="${p.id}">${p.name} (${p.role})</option>`)
              .join('');
          assignToInput.parentNode.replaceChild(select, assignToInput);
        }
      } catch (error) {
        console.error('Failed to load members:', error);
      }
    }
    
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
        const has = c.iso && eventIndexByDate.has(c.iso);
        return `<div class="day${c.muted?' muted':''}${has?' has-event':''}" data-date="${c.iso||''}">
          <div class="num">${c.t}</div>
        </div>`;
      }).join('');
  
      $$('#calGrid .day[data-date]').forEach(d=> d.addEventListener('click', ()=> openDay(d.dataset.date)));
    }
    async function openDay(iso){
      if(!iso) return;
      selectedDate = iso;
      renderNotifications();
      
      try{
        const res = await fetch(`/emt/api/events/by-date/?date=${encodeURIComponent(iso)}`, { headers:{'X-Requested-With':'XMLHttpRequest'} });
        const j = await res.json();
        const items = j.items||[];
        upcoming.innerHTML = items.length ? items.map(e=>`
          <div class="u-item">
            <div>${e.title}</div>
            <button class="chip-btn" data-open="${e.id}"><i class="fa-regular fa-eye"></i> View</button>
          </div>
        `).join('') : `<div class="empty">No items for this date</div>`;
        upcoming.querySelectorAll('[data-open]')
          .forEach(b=> b.addEventListener('click', ()=> openEventChat(b.getAttribute('data-open'))));
      }catch{
        upcoming.innerHTML = `<div class="empty">No items for this date</div>`;
      }
    }
    $('#calPrev')?.addEventListener('click', ()=>{ calRef = new Date(calRef.getFullYear(), calRef.getMonth()-1, 1); buildCalendar(); });
    $('#calNext')?.addEventListener('click', ()=>{ calRef = new Date(calRef.getFullYear(), calRef.getMonth()+1, 1); buildCalendar(); });
    $('#addEventBtn')?.addEventListener('click', (e)=>{
      const scope = $('#calFilter')?.value || 'all';
      e.currentTarget.href = `/suite/submit/?via=dashboard&scope=${encodeURIComponent(scope)}`;
    });

    // Load calendar data from role-aware endpoint
    async function loadCalendar(){
      try{
        const filter = ($('#calFilter')?.value||'all') === 'support' ? 'support' : 'all';
        const res = await fetch(`/emt/api/calendar/role/?filter=${encodeURIComponent(filter)}`, { headers:{'X-Requested-With':'XMLHttpRequest'} });
        const j = await res.json();
        EVENTS = j.items||[];
        eventIndexByDate = new Map();
        (EVENTS||[]).forEach(e=>{ if(!e.date) return; const arr=eventIndexByDate.get(e.date)||[]; arr.push(e); eventIndexByDate.set(e.date, arr); });
      }catch{ EVENTS=[]; eventIndexByDate=new Map(); }
      buildCalendar(); 
      if (!selectedDate) {
        openDay(new Date().toISOString().slice(0,10));
      }
    }
    $('#calFilter')?.addEventListener('change', loadCalendar);

    // Modal: chat + assign
    let currentProposalId = null;
    function openHeadModal(id){
      openEventChat(id);
    }
    $('#cdlHeadCloseModal')?.addEventListener('click', ()=> $('#cdlHeadEventModal').style.display='none');
    async function loadHeadChat(){
      const chat = $('#cdlHeadChat'); if(!currentProposalId) return;
      try{
        const res = await fetch(`/emt/api/chat/${currentProposalId}/`, { headers:{'X-Requested-With':'XMLHttpRequest'} });
        const j = await res.json();
        chat.innerHTML = (j.items||[]).map(m=>`<div class="msg"><div class="who">${m.sender_role||''}</div><div class="text">${m.message}</div></div>`).join('') || '<div class="empty">No messages</div>';
        chat.scrollTop = chat.scrollHeight;
      }catch{ chat.innerHTML = '<div class="empty">Cannot load chat</div>'; }
    }
    $('#cdlHeadChatSend')?.addEventListener('click', async (e)=>{
      e.preventDefault(); const inp=$('#cdlHeadChatInput'); const msg=(inp.value||'').trim(); if(!msg||!currentProposalId) return;
      try{
        const res = await fetch(`/emt/api/chat/${currentProposalId}/send/`, { method:'POST', headers:{'Content-Type':'application/json','X-Requested-With':'XMLHttpRequest','X-CSRFToken':getCsrfToken()}, body: JSON.stringify({ message: msg }) });
        const j = await res.json(); if(j.success){ inp.value=''; loadHeadChat(); }
      }catch{}
    });
    $('#cdlHeadAssignBtn')?.addEventListener('click', async (e)=>{
      e.preventDefault(); if(!currentProposalId) return;
      const assigned_to=Number($('#cdlAssignTo').value||''); const task_type=($('#cdlTaskType').value||'').trim(); const priority=$('#cdlTaskPriority').value||'normal'; const deadline=$('#cdlTaskDeadline').value||''; const description=($('#cdlTaskDesc').value||'').trim();
      if(!assigned_to || !task_type || !deadline){ alert('Please select member, task type, and deadline'); return; }
      try{
        const res = await fetch(`/emt/api/task/assign/${currentProposalId}/`, { method:'POST', headers:{'Content-Type':'application/json','X-Requested-With':'XMLHttpRequest','X-CSRFToken':getCsrfToken()}, body: JSON.stringify({ assigned_to, task_type, priority, deadline, description }) });
        const j = await res.json(); if(j.success){ alert('Task assigned'); $('#cdlHeadEventModal').style.display='none'; }
        else if(j.error){ alert(j.error); }
      }catch{ alert('Failed to assign task'); }
    });

    function getCsrfToken(){ const name='csrftoken='; const cookies=document.cookie?document.cookie.split(';'):[]; for(let c of cookies){ c=c.trim(); if(c.startsWith(name)) return decodeURIComponent(c.substring(name.length)); } return ''; }
  
    // Utils
    function cap(s){ return s ? s.charAt(0).toUpperCase()+s.slice(1) : s; }
    function fmt(iso){ const d=new Date(iso); return d.toLocaleString(undefined,{month:'short',day:'2-digit'}); }
    function esc(s){ return (s??'').toString().replace(/[&<>"']/g,m=>({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;' }[m])); }
  
    document.addEventListener('DOMContentLoaded', ()=>{
      loadEvents();
      computeKPIs();
      setAMFilter('all');
      renderAssignTable();
      viewWorkload();
      loadCalendar();
    });
  })();
  