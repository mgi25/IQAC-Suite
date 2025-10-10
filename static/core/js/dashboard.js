/* IQAC Suite – Dashboard UI (frontend only) */
(function () {
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
  const px = v => Number.parseFloat(v) || 0;

  // Simple tab/anchor navigation
  function goTab(id, hash) {
    const extra = hash ? (hash.startsWith('#') ? hash.slice(1) : hash) : '';
    const suffix = extra ? (extra.startsWith('&') ? extra : `&${extra}`) : '';
    location.hash = `#${id}${suffix}`;
  }
  $('#kpiStudents')?.addEventListener('click', () => goTab('students'));
  $('#kpiClasses')?.addEventListener('click', () => goTab('profile'));
  $('#kpiOrgEvents')?.addEventListener('click', () => goTab('events', '#type=my'));
  $('#kpiPartEvents')?.addEventListener('click', () => goTab('events', '#type=participating'));
  $$('[data-go-tab="profile"]').forEach(el=>el.addEventListener('click',e=>{e.preventDefault();goTab('profile');}));
  $$('[data-go-tab="events"]').forEach(el=>el.addEventListener('click',e=>{e.preventDefault();goTab('events');}));

  // Donut: Performance / Contribution
  let donut, currentView = 'performance';
  const ctx = $('#donutChart')?.getContext('2d');
  const COLORS = ['#6366f1','#f59e0b','#10b981','#ef4444'];

  function renderDonut(labels, data) {
    if (!ctx) return;
    donut?.destroy();
    donut = new Chart(ctx, {
      type: 'doughnut',
      data: { labels, datasets: [{ data, backgroundColor: COLORS, borderWidth: 0, cutout: '70%' }] },
      options: {
        plugins: { legend: { display: false } },
        responsive: true,
        maintainAspectRatio: true,
        layout:{padding:10}
      }
    });
    const legend = $('#donutLegend');
    if (legend) legend.innerHTML = labels.map((l,i)=>{
      const raw = data[i];
      const n = typeof raw === 'number' ? Math.round(raw*10)/10 : raw;
      const val = (typeof n === 'number' && Number.isFinite(n))
        ? (n % 1 === 0 ? n.toFixed(0) : n.toFixed(1))
        : n;
      return `<div class="legend-row"><span class="legend-dot" style="background:${COLORS[i]}"></span><span>${l}</span><strong style="margin-left:auto">${val}%</strong></div>`;
    }).join('');
  }

  async function loadPerformance() {
    try{
      if(window.AppOverlay) AppOverlay.show('Loading performance…');
      const res = await fetch('/api/student/performance-data/', { headers: { 'X-Requested-With':'XMLHttpRequest' }});
      const j = await res.json();
      renderDonut(j.labels, j.percentages);
    }catch{
      renderDonut(['Excellent','Good','Average','Poor'], [35, 40, 20, 5]);
    } finally { if(window.AppOverlay) AppOverlay.hide(); }
  }
  async function loadContribution() {
    try{
      if(window.AppOverlay) AppOverlay.show('Loading contribution…');
      const res = await fetch('/api/event-contribution/', { headers: { 'X-Requested-With':'XMLHttpRequest' }});
      const j = await res.json();
      const pct = Number(j.overall_percentage) || 0;
      renderDonut(['My Contribution','Other'], [pct, Math.max(0, 100 - pct)]);
    }catch{
      renderDonut(['Organized','Participated','Reviewed','Other'], [45, 35, 15, 5]);
    } finally { if(window.AppOverlay) AppOverlay.hide(); }
  }

  async function loadRecentEvents() {
    try {
      const res = await fetch('/api/user/events-data/', { headers: { 'X-Requested-With': 'XMLHttpRequest' }});
      const j = await res.json();
      
      // Update the static actions list with dynamic data if needed
      const actionsList = $('#actionsList');
      if (actionsList && j.events) {
        const proposalTracker = actionsList.querySelector('#proposalTracker');
        const recentEventsHtml = j.events.slice(0, 3).map(event => `
          <article class="list-item">
            <div class="bullet ${event.status.toLowerCase()}">
              <i class="fa-regular fa-calendar"></i>
            </div>
            <div class="list-body">
              <h4>${event.title}</h4>
              <p>${event.organization} - ${event.created_at}</p>
            </div>
            <span class="chip-btn">${event.status}</span>
          </article>
        `).join('');
        if (recentEventsHtml) {
          const existingContent = actionsList.innerHTML;
          actionsList.innerHTML = recentEventsHtml + existingContent;
        }
      }
    } catch (error) {
      console.error('Failed to load recent events:', error);
    }
  }

  $$('.seg-btn').forEach(b => b.addEventListener('click', e => {
    $$('.seg-btn').forEach(x => x.classList.remove('active'));
    e.currentTarget.classList.add('active');
    currentView = e.currentTarget.dataset.view;
    try{ localStorage.setItem('iqac:student:view', currentView); }catch(_e){}
    const title = $('#perfTitle');
    if (title) title.textContent = currentView === 'performance' ? 'Student Performance' : 'Event Contribution';
    (currentView === 'performance' ? loadPerformance() : loadContribution()).then(syncHeights);
  }));

  // Calendar: delegate to shared module (CalendarModule)

  // Add event scope passthrough - now opens modal instead
  $('#addEventBtn')?.addEventListener('click', (e) => {
    e.preventDefault();
    showEventCreationModal();
  });

  // Chart click handler for proposal tracking
  $('#chartContainer')?.addEventListener('click', () => {
    loadAndShowProposals();
  });

  // Clear event details
  $('#clearEventDetails')?.addEventListener('click', () => {
    $('#eventDetailsContent').innerHTML = '<div class="empty">Click an event in the calendar to view details.</div>';
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
      const scope = $('#visibilitySelect')?.value || 'all';
      window.location.href = `/suite/submit/?via=dashboard&scope=${encodeURIComponent(scope)}`;
    };
    
    // Handle close events
    $('#closeEventModal').onclick = () => modal.style.display = 'none';
    $('#cancelEvent').onclick = () => modal.style.display = 'none';
  }

  async function loadPlaces(selector) {
    try {
      const response = await fetch('/api/dashboard/places/', { headers: {'X-Requested-With':'XMLHttpRequest', 'Accept': 'application/json'} });
      const data = await response.json();
      const select = $(selector);
      if (select) {
        // microcopy: typographic ellipsis and consistent phrasing
        select.innerHTML = '<option value="">Select a venue…</option>' + 
          data.places.map(p => `<option value="${p.name}">${p.name}</option>`).join('');
      }
    } catch (ex) {
      console.error('Failed to load places:', ex);
    }
  }

  async function loadPeople(selector) {
    try {
      const response = await fetch('/api/dashboard/people/', { headers: {'X-Requested-With':'XMLHttpRequest', 'Accept': 'application/json'} });
      const data = await response.json();
      const select = $(selector);
      if (select) {
        select.innerHTML = data.people.map(p => 
          `<option value="${p.id}">${p.name} (${p.role})</option>`
        ).join('');
      }
    } catch (ex) {
      console.error('Failed to load people:', ex);
    }
  }

  async function loadAndShowProposals() {
    try {
      const response = await fetch('/api/user/proposals/', { headers: {'X-Requested-With':'XMLHttpRequest'} });
      const data = await response.json();
      
      const tracker = $('#proposalTracker');
      const list = $('#proposalsList');
      
      if (data.proposals && data.proposals.length > 0) {
        const seen = new Set();
        const uniq = [];
        for (const p of data.proposals){
          const key = (p.title||'').trim().toLowerCase();
          if (seen.has(key)) continue; seen.add(key); uniq.push(p);
        }
        list.innerHTML = uniq.map(p => `
          <article class="list-item">
            <div class="bullet ${p.status}"><i class="fa-regular fa-file-lines"></i></div>
            <div class="list-body">
              <h4>${p.title}</h4>
              <p>${p.status_display}</p>
            </div>
            <a href="${p.view_url}" class="chip-btn"><i class="fa-regular fa-eye"></i> View</a>
          </article>
        `).join('');
        tracker.style.display = 'block';
      } else {
        list.innerHTML = '<div class="empty">No proposals found.</div>';
        tracker.style.display = 'block';
      }
    } catch (ex) {
      console.error('Failed to load proposals:', ex);
    }
  }

  function showSuccessMessage(message) {
    // Simple success message - could be enhanced with a toast system
    const temp = document.createElement('div');
    temp.style.cssText = 'position:fixed;top:20px;right:20px;background:#10b981;color:white;padding:12px 16px;border-radius:6px;z-index:1001;';
    temp.textContent = message;
    document.body.appendChild(temp);
    setTimeout(() => document.body.removeChild(temp), 3000);
  }

  // Dropdown filtering
  $('#visibilitySelect')?.addEventListener('change', (e)=>{
    currentCategory = e.target.value || 'all';
    loadCalendarData();
  });

async function loadCalendarData() {
  try {
    const res = await fetch(`/api/calendar/?category=all`, {
      headers: { 'X-Requested-With': 'XMLHttpRequest' }
    });
    const j = await res.json();
    DASHBOARD_EVENTS = j.items || [];

    // Index by date using the canonical CalendarModule events (no forced 'finalized' filter)
    eventIndexByDate = new Map();
    const canonical = (window.CalendarModule && typeof CalendarModule.getEvents === 'function') ? CalendarModule.getEvents() : DASHBOARD_EVENTS;
    (canonical || []).forEach(e => {
      if (!e.date) return;
      const list = eventIndexByDate.get(e.date) || [];
      list.push(e);
      eventIndexByDate.set(e.date, list);
    });
  } catch {
    DASHBOARD_EVENTS = [];
    eventIndexByDate = new Map();
  }
  buildCalendar();
  renderMonthEvents();
}

function renderMonthEvents() {
  const wrap = document.getElementById("upcomingWrap");
  const thisMonth = calRef.getMonth();
  const thisYear  = calRef.getFullYear();

  // Use the CalendarModule's events to determine what's in this month (keeps behavior identical to admin)
  const canonical = (window.CalendarModule && typeof CalendarModule.getEvents === 'function') ? CalendarModule.getEvents() : DASHBOARD_EVENTS;
  const events = (canonical || []).filter(e => {
    if (!e.date) return false;
    const d = new Date(e.date);
    return d.getMonth() === thisMonth && d.getFullYear() === thisYear;
  });

  if (events.length === 0) {
    wrap.innerHTML = `<div class="empty">No upcoming events this month.</div>`;
    return;
  }

wrap.innerHTML = events.map(ev => `
  <article class="list-item">
    <div class="bullet"><i class="fa-solid fa-calendar"></i></div>
    <div class="list-body">
      <h4><a href="${ev.view_url}">${ev.title}</a></h4>
      <p class="muted">${ev.date}</p>
    </div>
  </article>
`).join("");


}



  // Heatmap
  async function renderHeatmap(){
    const wrap = $('#heatmapContainer'); if (!wrap) return;
    try{
      const res = await fetch('/api/student/contributions/', { headers:{'X-Requested-With':'XMLHttpRequest'} });
      const j = await res.json();
      const contributions = j.contributions || [];
      // Build GitHub-style grid
      const cols = 53, rows = 7;
      const grid = document.createElement('div'); grid.className='hm-grid';
      // Map date->level
      const map = Object.create(null);
      contributions.forEach(c=>{ map[c.date] = c.level; });
      // Start 52 weeks back
      const today = new Date();
      const start = new Date(today); start.setDate(today.getDate() - (52*7));
      let cur = new Date(start);
      for (let c=0; c<cols; c++){
        const col = document.createElement('div'); col.className='hm-col';
        for (let r=0; r<rows; r++){
          const cell = document.createElement('div'); cell.className='hm-cell';
          const dateStr = cur.toISOString().split('T')[0];
          const lvl = map[dateStr] || 0;
          if (lvl>0) cell.classList.add(`l${lvl}`);
          cell.title = lvl>0 ? `${dateStr}: ${lvl} contribution${lvl>1?'s':''}` : `${dateStr}: No contributions`;
          col.appendChild(cell);
          cur.setDate(cur.getDate()+1);
        }
        grid.appendChild(col);
      }
      wrap.innerHTML=''; wrap.appendChild(grid);
      fitHeatmap();
    }catch{
      // graceful no-op on failure
      wrap.innerHTML = '<div class="empty">No contribution data</div>';
    }
  }

  function fitHeatmap(){
    const wrap = $('#heatmapContainer'); if(!wrap) return;
    const cols = 53, rows = 7, gap = 3;
    const cs = getComputedStyle(wrap);
    const availW = wrap.clientWidth  - (parseFloat(cs.paddingLeft)||0) - (parseFloat(cs.paddingRight)||0);
    const availH = wrap.clientHeight - (parseFloat(cs.paddingTop)||0)  - (parseFloat(cs.paddingBottom)||0);
    const size = Math.max(4, Math.floor(Math.min(
      (availW - (cols - 1) * gap) / cols,
      (availH - (rows - 1) * gap) / rows
    )));
    wrap.style.setProperty('--hm-size', size + 'px');
    wrap.style.setProperty('--hm-gap',  gap  + 'px');
  }

  // To-do functionality removed - replaced with event details viewer

  function syncHeights(){
    const isDesktop = window.innerWidth > 1200;
    const root = document.documentElement;
    const perf = $('#cardPerformance');
    const acts = $('#cardActions');
    const cal  = $('#cardCalendar');
    const eventDetails = $('#cardEventDetails');
    const contrib = $('#cardContribution');
  
    if(!isDesktop){
      ['--calH','--contribH','--eventDetailsH'].forEach(v=>root.style.removeProperty(v));
      [perf, acts, cal, eventDetails].forEach(el=>{ if(el){ el.style.height=''; el.style.minHeight=''; }});
      return;
    }
  
    // 1) Match Actions + Performance exactly to Calendar height
    if (cal) {
      const calH = Math.ceil(cal.getBoundingClientRect().height);
      root.style.setProperty('--calH', calH + 'px');
      cal.style.height  = calH + 'px';
      if (acts) acts.style.height = calH + 'px';
      if (perf) perf.style.height = calH + 'px';
    }
  
    // 2) Event Details equals Contribution
    if (contrib && eventDetails) {
      const contribH = Math.ceil(contrib.getBoundingClientRect().height);
      root.style.setProperty('--contribH', contribH + 'px');
      eventDetails.style.height = contribH + 'px';
    }
    fitHeatmap();
  }  

  const debounce = (fn,ms=120)=>{ let t; return (...a)=>{ clearTimeout(t); t=setTimeout(()=>fn(...a),ms); }; };

  // Boot
  document.addEventListener('DOMContentLoaded', () => {
    try{ const saved = localStorage.getItem('iqac:student:view'); if(saved){ currentView = saved; $$('.seg-btn').forEach(x=>x.classList.toggle('active', x.dataset.view===saved)); } }catch(_e){}
    loadPerformance();
    loadAndShowProposals();
    // loadRecentEvents(); // intentionally not auto-prepending to keep the section focused
    // Initialize shared calendar module (same behavior as admin)
    try{
      if (window.CalendarModule && typeof CalendarModule.init === 'function'){
        if(window.AppOverlay) AppOverlay.show('Loading calendar…');
        CalendarModule.init({ endpoint: '/api/calendar/?category=all', inlineEventsElementId: 'calendarEventsJson', showOnlyStartDate: false });
      } else {
        // fallback to legacy data load if CalendarModule is not available
        if(window.AppOverlay) AppOverlay.show('Loading calendar…');
        loadCalendarData().finally(()=>{ if(window.AppOverlay) AppOverlay.hide(); });
      }
    }catch(ex){ console.error('CalendarModule init failed', ex); if(window.AppOverlay) AppOverlay.show('Loading calendar…'); loadCalendarData().finally(()=>{ if(window.AppOverlay) AppOverlay.hide(); }); }
    renderHeatmap();
    requestAnimationFrame(()=>{ syncHeights(); });
  });

  window.addEventListener('load', ()=>syncHeights());
  window.addEventListener('resize', debounce(syncHeights, 150));
})();
