/* Student Dashboard – frontend only */
(function () {
    const $  = (s, r=document)=>r.querySelector(s);
    const $$ = (s, r=document)=>Array.from(r.querySelectorAll(s));
  
    // KPI clicks (student tabs/routes)
    $('#kpiEvents')?.addEventListener('click', ()=> location.hash = '#events&type=participated');
    $('#kpiAchievements')?.addEventListener('click', ()=> location.hash = '#achievements');
    $('#kpiClubs')?.addEventListener('click', ()=> location.hash = '#profile&tab=clubs');
    $('#kpiActivityScore')?.addEventListener('click', ()=> location.hash = '#profile&tab=score');

    // Performance/Contribution tab switching
    document.addEventListener('click', (e) => {
      if (e.target.matches('[data-view="performance"]')) {
        e.preventDefault();
        document.querySelectorAll('[data-view]').forEach(btn => btn.classList.remove('active'));
        e.target.classList.add('active');
        $('#perfTitle').textContent = 'Performance Analytics';
        loadPerformance();
      } else if (e.target.matches('[data-view="contribution"]')) {
        e.preventDefault();
        document.querySelectorAll('[data-view]').forEach(btn => btn.classList.remove('active'));
        e.target.classList.add('active');
        $('#perfTitle').textContent = 'Event Contributions';
        loadContribution();
      }
    });
  
    // Donut
    let donut;
    const ctx = $('#donutChart')?.getContext('2d');
    const COLORS = ['#6366f1','#0ea5e9','#10b981','#f59e0b'];
  
    function renderDonut(labels, data) {
      if (!ctx) return;
      donut?.destroy();
      donut = new Chart(ctx, {
        type: 'doughnut',
        data: { labels, datasets: [{ data, backgroundColor: COLORS, borderWidth: 0, cutout: '70%' }] },
        options: { plugins: { legend: { display:false } }, responsive:true, maintainAspectRatio:true, layout:{padding:10} }
      });
      const legend = $('#donutLegend');
      if (legend) legend.innerHTML = labels.map((l,i)=>{
        const val = typeof data[i] === 'number' ? Math.round(data[i]*10)/10 : data[i];
        return `<div class="legend-row"><span class="legend-dot" style="background:${COLORS[i]}"></span><span>${l}</span><strong style="margin-left:auto">${val}%</strong></div>`;
      }).join('');
    }
  
    async function loadPerformance(){
      try{
        const res = await fetch('/api/student/performance-data/', { headers:{'X-Requested-With':'XMLHttpRequest'} });
        const j = await res.json();
        
        // Update performance statistics in the UI if needed
        if (j.total_events !== undefined) {
          // You can update KPI cards here if they exist
          const totalEventsEl = $('#totalEvents');
          if (totalEventsEl) totalEventsEl.textContent = j.total_events;
          
          const participationRateEl = $('#participationRate');
          if (participationRateEl) participationRateEl.textContent = j.participation_rate + '%';
        }
        
        // Use actual participation data for donut chart
        const labels = ['Participated', 'Not Participated'];
        const data = [j.participation_rate, 100 - j.participation_rate];
        renderDonut(labels, data);
      }catch{
        renderDonut(['Critical Thinking','Leadership','Communication','Teamwork'], [30,30,25,15]);
      }
    }

    async function loadRecentActivity() {
      try {
        const res = await fetch('/api/user/events-data/', { headers: {'X-Requested-With': 'XMLHttpRequest'} });
        const j = await res.json();
        
        const actionsCard = document.querySelector('#cardActions .list');
        if (actionsCard && j.events) {
          if (j.events.length > 0) {
            actionsCard.innerHTML = j.events.slice(0, 5).map(event => `
              <article class="list-item">
                <div class="bullet"><i class="fa-solid fa-circle-check"></i></div>
                <div class="list-body">
                  <h4>${event.title}</h4>
                  <p>${event.description} - ${event.created_at}</p>
                  <small>Status: ${event.status}</small>
                </div>
              </article>
            `).join('');
          } else {
            actionsCard.innerHTML = '<div class="empty">No recent activity.</div>';
          }
        }
      } catch (error) {
        console.error('Failed to load recent activity:', error);
      }
    }
  
    async function loadContribution(){
      try{
        const res = await fetch('/api/student/contributions/', { headers:{'X-Requested-With':'XMLHttpRequest'} });
        const j = await res.json();
        
        // Render GitHub-style contribution heatmap
        renderGitHubStyleHeatmap(j.contributions);
      }catch{
        renderDonut(['Events','Roles','Leadership','Other'], [55,25,15,5]);
      }
    }

    function renderGitHubStyleHeatmap(contributions) {
      const wrap = $('#heatmapContainer'); 
      if (!wrap || !contributions) return;
      
      const cols = 53, rows = 7;
      const grid = document.createElement('div'); 
      grid.className = 'hm-grid';
      
      // Create contribution map for quick lookup
      const contribMap = {};
      contributions.forEach(c => {
        contribMap[c.date] = c.level;
      });
      
      // Calculate start date (52 weeks ago)
      const today = new Date();
      const startDate = new Date(today);
      startDate.setDate(today.getDate() - (52 * 7));
      
      let currentDate = new Date(startDate);
      
      for (let c = 0; c < cols; c++) {
        const col = document.createElement('div'); 
        col.className = 'hm-col';
        
        for (let r = 0; r < rows; r++) {
          const cell = document.createElement('div'); 
          cell.className = 'hm-cell';
          
          const dateStr = currentDate.toISOString().split('T')[0];
          const level = contribMap[dateStr] || 0;
          
          if (level > 0) {
            cell.classList.add(`l${level}`);
            cell.title = `${dateStr}: ${level} contribution${level > 1 ? 's' : ''}`;
          } else {
            cell.title = `${dateStr}: No contributions`;
          }
          
          col.appendChild(cell);
          currentDate.setDate(currentDate.getDate() + 1);
        }
        grid.appendChild(col);
      }
      
      wrap.innerHTML = '';
      wrap.appendChild(grid);
      fitHeatmap();
    }
  
    $$('.seg-btn').forEach(b=>b.addEventListener('click',e=>{
      $$('.seg-btn').forEach(x=>x.classList.remove('active'));
      e.currentTarget.classList.add('active');
      const v = e.currentTarget.dataset.view;
      $('#perfTitle').textContent = v==='performance' ? 'Graduate Attributes' : 'Contribution';
      (v==='performance'? loadPerformance(): loadContribution()).then(syncHeights);
    }));
  
  // Calendar
  let calRef = new Date();
  let currentCategory = 'all';
  let privateTasksKey = 'ems.privateTasks';
  let eventIndexByDate = new Map();
  let selectedDateStr = null;
    const fmt2 = v => String(v).padStart(2,'0');
    const isSame = (a,b)=>a.getFullYear()==b.getFullYear()&&a.getMonth()==b.getMonth()&&a.getDate()==b.getDate();
  
  function buildCalendar(){
      const headTitle = $('#calTitle'), grid = $('#calGrid');
      if(!grid||!headTitle) return;
      headTitle.textContent = calRef.toLocaleString(undefined,{month:'long', year:'numeric'});
  
      const first = new Date(calRef.getFullYear(), calRef.getMonth(), 1);
      const last  = new Date(calRef.getFullYear(), calRef.getMonth()+1, 0);
      const startIdx = first.getDay();
      const prevLast = new Date(calRef.getFullYear(), calRef.getMonth(), 0).getDate();
  
      const cells=[];
      for(let i=startIdx-1;i>=0;i--){ cells.push({text: prevLast - i, date:null, muted:true}); }
      for(let d=1; d<=last.getDate(); d++){
        const dt = new Date(calRef.getFullYear(), calRef.getMonth(), d);
        cells.push({text:d, date:dt, muted:false});
      }
      while(cells.length % 7 !== 0){ cells.push({text: cells.length%7+1, date:null, muted:true}); }
  
      const eventDates = new Set(eventIndexByDate.keys());
      const privateTasks = new Set(JSON.parse(localStorage.getItem(privateTasksKey)||'[]'));
      grid.innerHTML = cells.map(c=>{
        const today = c.date && isSame(c.date, new Date());
        const iso = c.date ? `${c.date.getFullYear()}-${fmt2(c.date.getMonth()+1)}-${fmt2(c.date.getDate())}` : '';
        const hasEvent = iso && (eventDates.has(iso) || (currentCategory==='private' && privateTasks.has(iso)));
        const selected = iso && selectedDateStr === iso ? ' selected' : '';
        return `<div class="day${c.muted?' muted':''}${today?' today':''}${hasEvent?' has-event':''}${selected}" data-date="${iso}" tabindex="0" role="button">${c.text}</div>`;
      }).join('');
  
      grid.querySelectorAll('.day[data-date]').forEach(el=>{
        const date = new Date(el.dataset.date);
        el.addEventListener('click', ()=> {
          selectedDateStr = el.dataset.date;
          grid.querySelectorAll('.day.selected').forEach(x=>x.classList.remove('selected'));
          el.classList.add('selected');
          onDayClick(date);
        });
      });
    }
  
    function openDay(day){
      const yyyy=day.getFullYear(), mm=String(day.getMonth()+1).padStart(2,'0'), dd=String(day.getDate()).padStart(2,'0');
      const dateStr = `${yyyy}-${mm}-${dd}`;
      const list = $('#upcomingWrap'); if(!list) return;
      const items = (window.DASHBOARD_EVENTS||[]).filter(e => e.date === dateStr && (e.status||'').toLowerCase()==='finalized');
      list.innerHTML = items.length
        ? items.map(e => {
            const viewBtn = e.view_url ? `<a class="chip-btn" href="${e.view_url}"><i class="fa-regular fa-eye"></i> View</a>` : '';
            const addBtn = !e.past && e.gcal_url ? `<a class="chip-btn" target="_blank" rel="noopener" href="${e.gcal_url}"><i class="fa-regular fa-calendar-plus"></i> Add to Google</a>` : '';
            return `<div class="u-item"><div>${e.title}</div><div style="display:flex;gap:8px;">${viewBtn}${addBtn}</div></div>`;
          }).join('')
        : `<div class="empty">No events for ${day.toLocaleDateString()}</div>`;
    }

    function onDayClick(day){
      const yyyy=day.getFullYear(), mm=String(day.getMonth()+1).padStart(2,'0'), dd=String(day.getDate()).padStart(2,'0');
      const dateStr = `${yyyy}-${mm}-${dd}`;
      if (currentCategory === 'private'){
        // Show confirmation modal first
        showPrivateCalendarConfirmation(day);
        return;
      }
      // Show event details and highlight in event viewer
      showEventDetails(day);
      openDay(day);
    }

    function showPrivateCalendarConfirmation(day) {
      const modal = $('#confirmationModal');
      modal.style.display = 'flex';
      
      $('#cancelConfirm').onclick = () => {
        modal.style.display = 'none';
        showEventDetails(day);
        openDay(day);
      };
      
      $('#confirmOpen').onclick = () => {
        modal.style.display = 'none';
        const yyyy = day.getFullYear(), mm = String(day.getMonth()+1).padStart(2,'0'), dd = String(day.getDate()).padStart(2,'0');
        const dateStr = `${yyyy}-${mm}-${dd}`;
        const ymd = `${yyyy}${mm}${dd}`;
        const url = `https://www.google.com/calendar/render?action=TEMPLATE&dates=${ymd}/${ymd}&sf=true&output=xml`;
        window.open(url, '_blank', 'noopener');
        
        const tasks = new Set(JSON.parse(localStorage.getItem(privateTasksKey)||'[]'));
        tasks.add(dateStr);
        localStorage.setItem(privateTasksKey, JSON.stringify(Array.from(tasks)));
        buildCalendar();
        showEventDetails(day);
        openDay(day);
      };
    }

    function showEventDetails(day) {
      const yyyy = day.getFullYear(), mm = String(day.getMonth()+1).padStart(2,'0'), dd = String(day.getDate()).padStart(2,'0');
      const dateStr = `${yyyy}-${mm}-${dd}`;
      const content = $('#eventDetailsContent');
      const clearBtn = $('#clearEventDetails');
      
      if (!content) return;
      
      const events = (window.DASHBOARD_EVENTS||[]).filter(e => e.date === dateStr && (e.status||'').toLowerCase()==='finalized');

  // Removed ICS export; only Google Calendar supported
      if (events.length > 0) {
        content.innerHTML = events.map(e => `
          <div class="event-detail-item">
            <div class="row">
              <h4>${e.title}</h4>
              <div class="actions">
                ${e.view_url ? `<a class="chip-btn" href="${e.view_url}"><i class="fa-regular fa-eye"></i> View Details</a>` : ''}
                ${!e.past && e.gcal_url ? `<a class="chip-btn" target="_blank" href="${e.gcal_url}"><i class="fa-regular fa-calendar-plus"></i> Google</a>` : ''}
              </div>
            </div>
            <div class="event-detail-meta">
              <i class="fa-regular fa-clock"></i> ${e.datetime ? new Date(e.datetime).toLocaleString() : 'All day'}
              ${e.venue ? `<br><i class="fa-solid fa-location-dot"></i> ${e.venue}` : ''}
            </div>
          </div>
        `).join('');
        clearBtn.style.display = 'inline-flex';
      } else {
        content.innerHTML = `<div class="empty">No events for ${day.toLocaleDateString()}</div>`;
        clearBtn.style.display = 'none';
      }
    }
  
    $('#calPrev')?.addEventListener('click', ()=>{ calRef = new Date(calRef.getFullYear(), calRef.getMonth()-1, 1); buildCalendar(); syncHeights(); });
    $('#calNext')?.addEventListener('click', ()=>{ calRef = new Date(calRef.getFullYear(), calRef.getMonth()+1, 1); buildCalendar(); syncHeights(); });

    // Add event button - now opens modal instead
    $('#addEventBtn')?.addEventListener('click', (e) => {
      e.preventDefault();
      showEventCreationModal();
    });

    // Clear event details
    $('#clearEventDetails')?.addEventListener('click', () => {
      $('#eventDetailsContent').innerHTML = '<div class="empty">Click on an event in the calendar to view details</div>';
      $('#clearEventDetails').style.display = 'none';
    });

    function showEventCreationModal() {
      const modal = $('#eventCreationModal');
      modal.style.display = 'flex';
      
      // Load places
      loadPlaces('#eventVenue');
      
      // Handle form submission
      $('#eventCreationForm').onsubmit = async (e) => {
        e.preventDefault();
        // This would redirect to the actual event creation page
        window.location.href = `/suite/submit/?via=dashboard`;
      };
      
      // Handle close events
      $('#closeEventModal').onclick = () => modal.style.display = 'none';
      $('#cancelEvent').onclick = () => modal.style.display = 'none';
    }

    async function loadPlaces(selector) {
      try {
        const response = await fetch('/api/dashboard/places/', { headers: {'X-Requested-With':'XMLHttpRequest'} });
        const data = await response.json();
        const select = $(selector);
        if (select) {
          select.innerHTML = '<option value="">Select venue...</option>' + 
            data.places.map(p => `<option value="${p.name}">${p.name}</option>`).join('');
        }
      } catch (ex) {
        console.error('Failed to load places:', ex);
      }
    }

  // No visibility dropdown on student; default to 'all'
  currentCategory = 'all';

    async function loadCalendarData(){
      try{
        const res = await fetch(`/api/calendar/?category=${encodeURIComponent(currentCategory)}`, { headers:{'X-Requested-With':'XMLHttpRequest'} });
        const j = await res.json();
        window.DASHBOARD_EVENTS = j.items || [];
        eventIndexByDate = new Map();
        (window.DASHBOARD_EVENTS||[]).forEach(e=>{
          if (!e.date) return;
          const status = (e.status||'').toLowerCase();
          if (status !== 'finalized') return; // finalized-only markers
          const list = eventIndexByDate.get(e.date) || [];
          list.push(e);
          eventIndexByDate.set(e.date, list);
        });
      }catch{ window.DASHBOARD_EVENTS = []; eventIndexByDate = new Map(); }
  buildCalendar();
    }
  
    // Heatmap
    function renderHeatmap(){
      const wrap = $('#heatmapContainer'); if(!wrap) return;
      const cols=53, rows=7, grid=document.createElement('div'); grid.className='hm-grid';
      for(let c=0;c<cols;c++){
        const col=document.createElement('div'); col.className='hm-col';
        for(let r=0;r<rows;r++){
          const cell=document.createElement('div'); cell.className='hm-cell';
          const v=Math.random(); if(v>0.8)cell.classList.add('l4'); else if(v>0.6)cell.classList.add('l3'); else if(v>0.35)cell.classList.add('l2'); else if(v>0.18)cell.classList.add('l1');
          col.appendChild(cell);
        }
        grid.appendChild(col);
      }
      wrap.innerHTML=''; wrap.appendChild(grid);
      fitHeatmap();
    }
    function fitHeatmap(){
      const wrap = $('#heatmapContainer'); if(!wrap) return;
      const cols=53, rows=7, gap=3;
      const cs=getComputedStyle(wrap);
      const availW=wrap.clientWidth-(parseFloat(cs.paddingLeft)||0)-(parseFloat(cs.paddingRight)||0);
      const availH=wrap.clientHeight-(parseFloat(cs.paddingTop)||0)-(parseFloat(cs.paddingBottom)||0);
      const size=Math.max(4, Math.floor(Math.min(
        (availW - (cols-1)*gap)/cols,
        (availH - (rows-1)*gap)/rows
      )));
      wrap.style.setProperty('--hm-size', size+'px');
      wrap.style.setProperty('--hm-gap', gap+'px');
    }
  
    // Simple local proposals list enhancer (optional)
    // (kept minimal to match teacher parity)
  
    // Height sync
    function syncHeights(){
      const isDesktop = window.innerWidth > 1200;
      const root=document.documentElement;
      const perf=$('#cardPerformance'), acts=$('#cardActions'), cal=$('#cardCalendar');
      const eventDetails=$('#cardEventDetails');
      const contrib=$('#cardContribution');
  
      if(!isDesktop){
        ['--calH','--contribH','--eventDetailsH'].forEach(v=>root.style.removeProperty(v));
        [perf,acts,cal,eventDetails].forEach(el=>{ if(el){ el.style.height=''; el.style.minHeight=''; }});
        return;
      }
  
      if (cal){
        const calH=Math.ceil(cal.getBoundingClientRect().height);
        root.style.setProperty('--calH', calH+'px');
        cal.style.height=calH+'px';
        if(acts) acts.style.height=calH+'px';
        if(perf) perf.style.height=calH+'px';
      }
  
      if (contrib && eventDetails){
        const contribH=Math.ceil(contrib.getBoundingClientRect().height);
        root.style.setProperty('--contribH', contribH+'px');
        eventDetails.style.height=contribH+'px';
      }
      fitHeatmap();
    }
  
    const debounce=(fn,ms=120)=>{let t;return(...a)=>{clearTimeout(t);t=setTimeout(()=>fn(...a),ms);}};
  
    // Tab switching for Performance/Contribution
    document.addEventListener('click', (e) => {
      if (e.target.matches('[data-view]')) {
        const view = e.target.dataset.view;
        const parent = e.target.closest('.card');
        
        // Update active button
        parent.querySelectorAll('.seg-btn').forEach(btn => btn.classList.remove('active'));
        e.target.classList.add('active');
        
        // Update title and load appropriate data
        const title = parent.querySelector('#perfTitle');
        if (view === 'performance') {
          if (title) title.textContent = 'Performance Metrics';
          loadPerformance();
        } else if (view === 'contribution') {
          if (title) title.textContent = 'Yearly Contribution';
          loadContribution();
        }
      }
    });

    document.addEventListener('DOMContentLoaded', ()=>{
      loadPerformance();
      loadRecentActivity();
      loadCalendarData();
      // Heatmap will be populated by contributions API with event-date aggregation
      // Fallback visual if API fails is handled inside loadContribution
      loadContribution();
      requestAnimationFrame(()=>{ syncHeights(); });
    });
    window.addEventListener('load', ()=>syncHeights());
    window.addEventListener('resize', debounce(syncHeights,150));
  })();
  