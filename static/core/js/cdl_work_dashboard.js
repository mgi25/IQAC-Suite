(function(){
    const $  = (s, r=document)=>r.querySelector(s);
    const $$ = (s, r=document)=>Array.from(r.querySelectorAll(s));
    
    let EVENTS = [];
    let eventIndexByDate = new Map();
    let selectedDate = null;
    let currentFilter = 'assigned'; // Default to assigned events for members
    let WORK = [];

    // Dynamic data loading
    async function loadMemberData() {
      try {
        const res = await fetch('/emt/api/task/member/', { headers: {'X-Requested-With':'XMLHttpRequest'} });
        const data = await res.json();
        WORK = data.items || [];
        computeKPIs();
        renderInbox();
        renderWork();
      } catch {
        WORK = [];
        computeKPIs();
        renderInbox();
        renderWork();
      }
    }

    // KPIs
    function computeKPIs(){
      setText('#valAssigned', WORK.length);
      setText('#valDueToday', WORK.filter(isDueToday).length);
      setText('#valWaiting',  WORK.filter(r=>r.status==='waiting').length);
      setText('#valRework',   WORK.filter(r=>r.status==='returned').length);
    }
    function isDueToday(r){ 
      if (!r.deadline) return false;
      const d=new Date(r.deadline); 
      const t=new Date(); 
      t.setHours(0,0,0,0); 
      d.setHours(0,0,0,0); 
      return d.getTime()===t.getTime(); 
    }

    // Event display
    function renderInbox() {
      const list = $('#inboxList');
      const empty = $('#inboxEmpty');
      const clearBtn = $('#clearInbox');
      
      let eventsToShow = [];
      
      if (selectedDate) {
        // Filter events by selected date
        eventsToShow = EVENTS.filter(e => {
          const eventDate = new Date(e.datetime).toISOString().split('T')[0];
          return eventDate === selectedDate;
        });
        $('#inboxTitle').textContent = `Events for ${new Date(selectedDate).toLocaleDateString()}`;
        clearBtn.style.display = 'inline-flex';
      } else {
        // Show events based on current filter
        eventsToShow = EVENTS;
        const filterValue = $('#eventViewFilter')?.value || 'assigned';
        $('#inboxTitle').textContent = filterValue === 'assigned' ? 'Assigned to Me' : 'All Events';
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
            <button class="chip-btn success" data-action="progress" data-id="${e.id}"><i class="fa-solid fa-tasks"></i> Update Progress</button>
          </div>
        </article>
      `).join('');

      // Add event listeners
      list.querySelectorAll('[data-action]').forEach(btn => {
        btn.addEventListener('click', e => {
          const eventId = e.currentTarget.dataset.id;
          const action = e.currentTarget.dataset.action;
          
          if (action === 'chat') {
            openEventChat(eventId);
          } else if (action === 'progress') {
            openProgressModal(eventId);
          }
        });
      });
    }

    // Event filter
    $('#eventViewFilter')?.addEventListener('change', e => {
      currentFilter = e.target.value;
      selectedDate = null; // Reset date selection
      loadCalendar();
    });

    // Clear inbox
    $('#clearInbox')?.addEventListener('click', () => {
      selectedDate = null;
      renderInbox();
    });

    // Chat functionality
    function openEventChat(eventId) {
      const modal = $('#cdlWorkEventModal');
      const event = EVENTS.find(e => e.id == eventId);
      
      if (!event) return;
      
      currentProposalId = eventId;
      modal.style.display = 'flex';
      $('#cdlWorkMeta').textContent = `${event.title}${event.datetime ? ' · ' + new Date(event.datetime).toLocaleString() : ''}${event.venue ? ' · ' + event.venue : ''}`;
      
      loadMemberChat();
    }

    // Progress update functionality
    function openProgressModal(eventId) {
      const task = WORK.find(w => w.proposal_id == eventId);
      if (!task) return;
      
      const progress = prompt(`Update progress for "${task.event_title}" (0-100):`, task.progress || 0);
      if (progress === null) return;
      
      const progressNum = parseInt(progress);
      if (isNaN(progressNum) || progressNum < 0 || progressNum > 100) {
        alert('Please enter a valid progress percentage (0-100)');
        return;
      }
      
      updateTaskProgress(task.id, progressNum);
    }

    async function updateTaskProgress(taskId, progress) {
      try {
        const res = await fetch('/emt/api/task/member/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': getCsrfToken()
          },
          body: JSON.stringify({
            task_id: taskId,
            action: 'progress',
            progress: progress
          })
        });
        
        const data = await res.json();
        if (data.success) {
          loadMemberData(); // Reload data
          alert('Progress updated successfully');
        } else {
          alert('Failed to update progress');
        }
      } catch {
        alert('Failed to update progress');
      }
    }

    // Calendar functionality
    let today = new Date(), calMonth = today.getMonth(), calYear = today.getFullYear();
    let isCalendarLazyLoaded = false;
    
    function lazyLoadCalendar() {
      if (!isCalendarLazyLoaded) {
        isCalendarLazyLoaded = true;
        loadCalendar();
      }
    }

    function loadCalendar() {
      const filter = $('#eventViewFilter')?.value || 'assigned';
      
      fetch(`/emt/api/calendar/role/?filter=${filter}`, { headers: {'X-Requested-With':'XMLHttpRequest'} })
        .then(res => res.json())
        .then(data => {
          EVENTS = data.events || [];
          eventIndexByDate.clear();
          EVENTS.forEach(e => {
            const date = new Date(e.datetime).toISOString().split('T')[0];
            if (!eventIndexByDate.has(date)) eventIndexByDate.set(date, []);
            eventIndexByDate.get(date).push(e);
          });
          showCal();
          renderInbox();
        })
        .catch(() => {
          EVENTS = [];
          eventIndexByDate.clear();
          showCal();
          renderInbox();
        });
    }

    function showCal() {
      const firstDay = new Date(calYear, calMonth, 1).getDay();
      const daysInMonth = new Date(calYear, calMonth + 1, 0).getDate();
      const tbl = $('#calendarTable tbody');
      
      tbl.innerHTML = '';
      $('#currentMonthYear').textContent = new Date(calYear, calMonth).toLocaleDateString('default', {month: 'long', year: 'numeric'});
      
      let date = 1;
      for (let i = 0; i < 6; i++) {
        const row = tbl.insertRow();
        for (let j = 0; j < 7; j++) {
          const cell = row.insertCell();
          if (i === 0 && j < firstDay) {
            cell.innerHTML = '';
          } else if (date > daysInMonth) {
            break;
          } else {
            const dateKey = `${calYear}-${String(calMonth + 1).padStart(2, '0')}-${String(date).padStart(2, '0')}`;
            const hasEvents = eventIndexByDate.has(dateKey);
            
            cell.className = 'clickable-date';
            cell.innerHTML = `<span class="${hasEvents ? 'has-events' : ''}">${date}</span>`;
            cell.onclick = () => openDay(dateKey);
            
            if (today.getDate() === date && today.getMonth() === calMonth && today.getFullYear() === calYear) {
              cell.querySelector('span').className += ' today';
            }
            date++;
          }
        }
      }
    }

    function openDay(dateKey) {
      selectedDate = dateKey;
      renderInbox();
    }

    function prevMonth() {
      calMonth = calMonth === 0 ? 11 : calMonth - 1;
      if (calMonth === 11) calYear--;
      showCal();
    }

    function nextMonth() {
      calMonth = calMonth === 11 ? 0 : calMonth + 1;
      if (calMonth === 0) calYear++;
      showCal();
    }

    // Event listeners for calendar navigation
    $('#prevMonth')?.addEventListener('click', prevMonth);
    $('#nextMonth')?.addEventListener('click', nextMonth);

    // Chat functionality (moved from below)
    let currentProposalId = null;
    const chatPollingInterval = 3000;
    let chatTimer = null;

    async function loadMemberChat() {
      if (!currentProposalId) return;
      
      try {
        const res = await fetch(`/emt/api/chat/list/${currentProposalId}/`, { headers: {'X-Requested-With':'XMLHttpRequest'} });
        const data = await res.json();
        
        const messages = data.messages || [];
        const container = $('#cdlWorkChatMessages');
        
        if (messages.length === 0) {
          container.innerHTML = '<div class="no-messages">No messages yet. Start the conversation!</div>';
        } else {
          container.innerHTML = messages.map(m => {
            const isOwn = m.user_id === getCurrentUserId();
            return `
              <div class="message ${isOwn ? 'own' : 'other'}">
                <div class="message-author">${esc(m.user_name)}</div>
                <div class="message-content">${esc(m.message)}</div>
                <div class="message-time">${new Date(m.timestamp).toLocaleString()}</div>
              </div>`;
          }).join('');
        }
        
        container.scrollTop = container.scrollHeight;
      } catch {
        $('#cdlWorkChatMessages').innerHTML = '<div class="error-message">Failed to load messages</div>';
      }
    }

    async function sendMemberChat() {
      const input = $('#cdlWorkChatInput');
      const message = input.value.trim();
      
      if (!message || !currentProposalId) return;
      
      try {
        const res = await fetch('/emt/api/chat/send/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': getCsrfToken()
          },
          body: JSON.stringify({
            proposal_id: currentProposalId,
            message: message
          })
        });
        
        const data = await res.json();
        if (data.success) {
          input.value = '';
          loadMemberChat();
        }
      } catch {
        // Ignore error
      }
    }

    // Chat event listeners
    $('#cdlWorkChatSend')?.addEventListener('click', sendMemberChat);
    $('#cdlWorkChatInput')?.addEventListener('keypress', e => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMemberChat();
      }
    });

    // Modal close handlers
    $('#cdlWorkEventModal .modal-close')?.addEventListener('click', () => {
      $('#cdlWorkEventModal').style.display = 'none';
      if (chatTimer) clearInterval(chatTimer);
      currentProposalId = null;
    });

    // Start chat polling when modal opens
    function startChatPolling() {
      if (chatTimer) clearInterval(chatTimer);
      chatTimer = setInterval(loadMemberChat, chatPollingInterval);
    }

    // Update openEventChat to start polling
    const originalOpenEventChat = openEventChat;
    openEventChat = function(eventId) {
      originalOpenEventChat(eventId);
      startChatPolling();
    };    // Progress
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
  $('#cdlWorkCalFilter')?.addEventListener('change', loadCalendar);
    function buildCalendar(){
      $('#calTitle').textContent = calRef.toLocaleString(undefined,{month:'long',year:'numeric'});
      const first=new Date(calRef.getFullYear(),calRef.getMonth(),1), last=new Date(calRef.getFullYear(),calRef.getMonth()+1,0);
      const startIdx=first.getDay(), prevLast=new Date(calRef.getFullYear(),calRef.getMonth(),0).getDate();
      const cells=[];
      for(let i=startIdx-1;i>=0;i--) cells.push({t:prevLast-i, muted:true});
      for(let d=1; d<=last.getDate(); d++) cells.push({t:d, iso:iso(calRef,d)});
      while(cells.length%7!==0) cells.push({t:'', muted:true});
  $('#calGrid').innerHTML = cells.map(c=>`<div class="day${c.muted?' muted':''}${c.iso && eventIndexByDate.has(c.iso)?' has-event':''}" data-date="${c.iso||''}"><div class="num">${c.t}</div></div>`).join('');
      $$('#calGrid .day[data-date]').forEach(d=> d.addEventListener('click',()=>openDay(d.dataset.date)));
    }
    function iso(base,d){ return `${base.getFullYear()}-${String(base.getMonth()+1).padStart(2,'0')}-${String(d).padStart(2,'0')}`; }
    async function openDay(iso){
      if(!iso) return; const wrap=$('#upcomingWrap');
      try{
        const res = await fetch(`/emt/api/events/by-date/?date=${encodeURIComponent(iso)}`, { headers:{'X-Requested-With':'XMLHttpRequest'} });
        const j = await res.json(); const items=j.items||[];
        wrap.innerHTML = items.length? items.map(e=>`<div class="u-item"><div>${esc(e.title||'Event')}</div><button class="chip-btn" data-open="${e.id}"><i class="fa-regular fa-eye"></i> View</button></div>`).join('') : `<div class="empty">No items for this date</div>`;
        wrap.querySelectorAll('[data-open]').forEach(b=> b.addEventListener('click', ()=> openMemberModal(b.getAttribute('data-open'))));
      }catch{ wrap.innerHTML = `<div class="empty">No items for this date</div>`; }
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
    function getCsrfToken(){ const name='csrftoken='; const cookies=document.cookie?document.cookie.split(';'):[]; for(let c of cookies){ c=c.trim(); if(c.startsWith(name)) return decodeURIComponent(c.substring(name.length)); } return ''; }
    function getCurrentUserId(){ const el = document.querySelector('[data-user-id]'); return el ? parseInt(el.dataset.userId) : null; }

    // Boot
    computeKPIs(); 
    renderInbox(); 
    renderChart('workload'); 
    loadMemberData();
    lazyLoadCalendar(); 
    renderWork();
  })();
  