(function () {
    const $ = (s, r = document) => r.querySelector(s);
    const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
  
    // State loaded via AJAX
    let EVENTS = [];
    let EVENT_DETAILS = [];
    let WORKLOAD_DATA = {};
    let KPIS = { total_active_requests:0, assets_pending:0, unassigned_tasks:0, total_events_supported:0 };
  let currentScope = 'all'; // all | support

    async function loadData(scope='all'){
      try{
        const res = await fetch(`/api/cdl/head-dashboard/?scope=${encodeURIComponent(scope)}`, {headers:{'Accept':'application/json'}});
        if(!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        KPIS = data.kpis || KPIS;
        EVENTS = (data.events || []).filter(Boolean);
        EVENT_DETAILS = (data.event_details || []).filter(Boolean);
        WORKLOAD_DATA = data.workload || {};
        renderAll();
      }catch(err){
        console.warn('Failed to load CDL dashboard data:', err);
        // Keep UI with zeros as per requirement
        KPIS = { total_active_requests:0, assets_pending:0, unassigned_tasks:0, total_events_supported:0 };
        EVENTS = [];
        EVENT_DETAILS = [];
        WORKLOAD_DATA = {};
        renderAll();
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
      
      // Always show only finalized events
      let items = EVENT_DETAILS.filter(ev => (ev.status || '').toLowerCase() === 'finalized');
      
      // Filter by type
      if (filter === 'posters') {
        items = items.filter(ev => ev.poster_required);
      } else if (filter === 'certificates') {
        items = items.filter(ev => ev.certificates_required);
      } else if (filter === 'coverage') {
        // Keep finalized; treat "coverage" as events (finalized) regardless of support
        items = items;
      } else if (filter === 'media') {
        items = items.filter(ev => ev.poster_required || ev.certificates_required);
      }
      // If calendar scope is support, ensure only support-needed items are shown
      if (currentScope === 'support') {
        items = items.filter(ev => ev.poster_required || ev.certificates_required);
      }
      
      if(items.length === 0){
        list.innerHTML = '<div class="empty-state">No notifications</div>';
        return;
      }
      
      list.innerHTML = items.map(ev => {
        const dateStr = ev.date ? new Date(ev.date).toLocaleDateString(undefined, {month:'short', day:'2-digit', year:'numeric'}) : '';
        const org = ev.organization || 'N/A';
        const assigned = ev.assigned_member || 'Unassigned';
        const viewHref = (currentScope === 'support') ? `/cdl/support/?eventId=${ev.id}` : `/proposal/${ev.id}/detail/`;
        
        return `<div class="notification-item" data-id="${ev.id}">
          <div class="notification-content">
            <h4>${ev.title}</h4>
            <p>Status: ${ev.status} ${dateStr?`• Date: ${dateStr}`:''}</p>
            <p>Department: ${org} • Assigned: ${assigned}</p>
            <div class="notification-tags">
              ${ev.poster_required?'<span class="tag poster">Poster</span>':''}
              ${ev.certificates_required?'<span class="tag certificate">Certificate</span>':''}
            </div>
          </div>
          <a class="view-btn" href="${viewHref}">View</a>
        </div>`;
      }).join('');
    }

    // Filter tabs event handling
  $$('.tab-btn').forEach(btn => {
      btn.addEventListener('click', e => {
    $$('.tab-btn').forEach(b => b.classList.remove('active'));
    e.currentTarget.classList.add('active');
        currentEventFilter = e.currentTarget.dataset.filter;
        renderNotifications(currentEventFilter);
      });
    });

    // Event details view button
    document.addEventListener('click', e => {
      if (e.target.closest('[data-event-id]')) {
        const eventId = e.target.closest('[data-event-id]').dataset.eventId;
        viewEventDetails(eventId);
      }
    });

    function viewEventDetails(eventId) {
      // Open CDL Support details page with query param for dynamic fetch
      window.location.href = `/cdl/support/?eventId=${encodeURIComponent(eventId)}`;
    }

    // Assignment Manager - build from EVENT_DETAILS
    function renderAssignmentTable(){
      const tbody = $('#taskList'); 
      if(!tbody) return;
      
      const tasks = EVENT_DETAILS.filter(ev => ev.poster_required || ev.certificates_required);
      
      if(tasks.length === 0){ 
        tbody.innerHTML = '<tr><td colspan="9" class="empty-row">No items</td></tr>'; 
        return; 
      }
      
      tbody.innerHTML = tasks.map((ev, index) => {
        const dateStr = ev.date ? new Date(ev.date).toLocaleDateString(undefined, {month:'short', day:'2-digit'}) : '';
        const org = ev.organization || 'N/A';
        const type = [];
        if (ev.poster_required) type.push('Poster');
        if (ev.certificates_required) type.push('Certificate');
        
        return `<tr data-id="${ev.id}">
          <td><input type="checkbox" /></td>
          <td>${ev.title}</td>
          <td>${type.join(', ')}</td>
          <td><span class="priority-badge normal">Normal</span></td>
          <td>${dateStr}</td>
          <td>
            <select class="assignee-select">
              <option value="">Unassigned</option>
              ${WORKLOAD_DATA.members ? WORKLOAD_DATA.members.map(member => 
                `<option value="${member.toLowerCase()}">${member}</option>`
              ).join('') : ''}
            </select>
          </td>
          <td><span class="status-badge pending">Pending</span></td>
          <td>1</td>
          <td>
            <button class="action-btn" data-action="assign">Assign</button>
          </td>
        </tr>`;
      }).join('');
    }

    // Assignment Manager controls
    $$('.control-btn[data-filter]').forEach(btn => {
      btn.addEventListener('click', e => {
        $$('.control-btn[data-filter]').forEach(b => b.classList.remove('active'));
        e.currentTarget.classList.add('active');
        
        const filter = e.currentTarget.dataset.filter;
        const rows = $$('#taskList tr[data-id]');
        
        rows.forEach(row => {
          let show = true;
          
          if (filter === 'unassigned') {
            const select = row.querySelector('.assignee-select');
            show = !select.value || select.value === '';
          } else if (filter === 'urgent') {
            // For demo, mark items with certificates as urgent
            const typeCell = row.cells[2];
            show = typeCell.textContent.includes('Certificate');
          }
          
          row.style.display = show ? '' : 'none';
        });
      });
    });

    // Task assign handler
    document.addEventListener('click', e => {
      if (e.target.dataset.action === 'assign') {
        const row = e.target.closest('tr');
        const select = row.querySelector('.assignee-select');
        const assignee = select.value;
        
        if (!assignee) {
          alert('Please select an assignee first');
          return;
        }
        
        console.log('Assigning task to:', assignee);
        alert(`Task assigned to ${assignee}`);
        
        // Update UI
        const statusCell = row.querySelector('.status-badge');
        statusCell.textContent = 'Assigned';
        statusCell.className = 'status-badge assigned';
        e.target.textContent = 'Assigned';
        e.target.disabled = true;
      }
    });

    // Team Analytics - updated to use workload data
    let teamChart;
    function buildTeamChart(labels, data, title){
      const ctx = $('#teamChart'); 
      if(!ctx) return;
      
      teamChart?.destroy();
      teamChart = new Chart(ctx, {
        type: 'bar',
        data: { 
          labels, 
          datasets: [{ 
            data, 
            borderWidth: 0,
            backgroundColor: ['#4f46e5', '#3b82f6', '#22c55e', '#f59e0b', '#ef4444']
          }] 
        },
        options: { 
          plugins: { legend: { display: false } }, 
          responsive: true, 
          maintainAspectRatio: false, 
          scales: { y: { beginAtZero: true } } 
        }
      });
    }
    
    function viewWorkload(){ 
      if (WORKLOAD_DATA.members && WORKLOAD_DATA.assignments && WORKLOAD_DATA.members.length) {
        buildTeamChart(WORKLOAD_DATA.members, WORKLOAD_DATA.assignments, 'Workload Distribution');
      } else {
        buildTeamChart(['No Members'], [0], 'Workload Distribution');
      }
    }
    
    function viewOnTime(){ 
      const members = WORKLOAD_DATA.members && WORKLOAD_DATA.members.length ? WORKLOAD_DATA.members : ['No Members'];
      const onTimeData = members.map(() => 0);
      buildTeamChart(members, onTimeData, 'On-time %'); 
    }
    
    function viewFirstPass(){ 
      const members = WORKLOAD_DATA.members && WORKLOAD_DATA.members.length ? WORKLOAD_DATA.members : ['No Members'];
      const firstPassData = members.map(() => 0);
      buildTeamChart(members, firstPassData, 'First-pass %'); 
    }
    
    $$('.control-btn[data-view]').forEach(b => {
      b.addEventListener('click', e => {
        $$('.control-btn[data-view]').forEach(x => x.classList.remove('active'));
        e.currentTarget.classList.add('active');
        const v = e.currentTarget.dataset.view;
        if(v === 'workload') viewWorkload();
        if(v === 'ontime') viewOnTime();
        if(v === 'firstpass') viewFirstPass();
      });
    });

    // Calendar - updated to work with proposal events
    let calRef = new Date();
  let currentCalFilter = 'all'; // all | support
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
        if (!c.iso) {
          return `<div class="day muted" data-date="">${c.t}</div>`;
        }
        const isToday = c.iso === new Date().toISOString().slice(0,10);
        // Only finalized events are provided by API; keep an extra guard
        let dayEvents = EVENTS.filter(e => e.date === c.iso && (e.status || '').toLowerCase() === 'finalized');
        if (currentCalFilter === 'support') {
          dayEvents = dayEvents.filter(e => e.type === 'cdl_support');
        }
  const hasEvents = dayEvents.length > 0;
  // use 'has-event' (singular) to match CSS red dot style
  return `<div class="day${hasEvents ? ' has-event' : ''}${isToday ? ' today' : ''}" data-date="${c.iso}">${c.t}</div>`;
      }).join('');

      $$('.day[data-date]').forEach(d => d.addEventListener('click', () => {
        $$('.day.selected').forEach(x => x.classList.remove('selected'));
        d.classList.add('selected');
        openDay(d.dataset.date);
      }));
    }

    function openDay(iso){
      // Only finalized events on day open
      let items = EVENTS.filter(e => e.date === iso && (e.status || '').toLowerCase() === 'finalized');
      if (currentCalFilter === 'support') {
        items = items.filter(e => e.type === 'cdl_support');
      }

      const box = $('#eventDetailsContent');
      const clearBtn = $('#clearEventDetails');
      if (!box) return;
      const dateStr = new Date(iso).toLocaleDateString(undefined, {day:'2-digit', month:'2-digit', year:'numeric'});
      if (!items.length){
        box.innerHTML = `<div class="empty">No events for ${dateStr}</div>`;
        clearBtn && (clearBtn.style.display = 'none');
        return;
      }
  box.innerHTML = items.map(e => `
        <div class="event-detail-item">
          <div class="event-detail-title with-actions">
            <span class="title-text">${e.title}</span>
            <div class="title-actions">
      ${currentCalFilter === 'support' ? `<a class="chip-btn" href="/cdl/support/?eventId=${e.id}">View</a>` : `<a class="chip-btn" href="/proposal/${e.id}/detail/">View</a>`}
            </div>
          </div>
          <div class="event-detail-meta">${dateStr} • Org: ${e.organization || 'N/A'} • Status: ${e.status}</div>
        </div>
      `).join('');
      if (clearBtn){
        clearBtn.style.display = 'inline-flex';
        clearBtn.onclick = () => {
          box.innerHTML = '<div class="empty">Select a date in the calendar to view events</div>';
          clearBtn.style.display = 'none';
          $$('.day.selected').forEach(x => x.classList.remove('selected'));
        };
      }
    }

    // Calendar filter
  $('#calFilter')?.addEventListener('change', e => {
      currentCalFilter = e.target.value;
      currentScope = currentCalFilter;
      loadData(currentScope);
    });

  $('#calPrev')?.addEventListener('click', () => { 
      calRef = new Date(calRef.getFullYear(), calRef.getMonth()-1, 1); 
      buildCalendar(); 
    });
    
  $('#calNext')?.addEventListener('click', () => { 
      calRef = new Date(calRef.getFullYear(), calRef.getMonth()+1, 1); 
      buildCalendar(); 
    });

    function renderAll(){
      renderKPIs();
      renderNotifications(currentEventFilter);
      renderAssignmentTable();
      viewWorkload();
      buildCalendar();
  // Do not auto-open; let user pick date to populate Event Details
    }

    document.addEventListener('DOMContentLoaded', () => {
      loadData('all');
    });
  })();  