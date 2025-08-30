/* Admin mini calendar + responsive drawer sync (no backend changes) */

function readEventsFromDOM() {
    try {
      return JSON.parse(document.getElementById('events-data').textContent) || [];
    } catch { return []; }
  }
  
  document.addEventListener('DOMContentLoaded', () => {
    let CALENDAR_EVENTS = readEventsFromDOM();
  
    const els = {
      title: document.getElementById('calTitle'),
      grid: document.getElementById('calGrid'),
      prev: document.getElementById('calPrev'),
      next: document.getElementById('calNext'),
      details: document.getElementById('eventDetailsContent'),
      clearDetails: document.getElementById('clearEventDetails'),
      drawer: document.getElementById('eventSidebar'),
      drawerOverlay: document.getElementById('sidebarOverlay'),
      drawerDate: document.getElementById('sidebarDate'),
      drawerContent: document.getElementById('sidebarContent'),
      drawerClose: document.getElementById('sidebarClose'),
    };
  
    let currentDate = new Date();
    let selectedDate = null;
  
    const isMobile = () => window.matchMedia('(max-width: 992px)').matches;
  
    function ymdLocal(d){
      const y=d.getFullYear();
      const m=String(d.getMonth()+1).padStart(2,'0');
      const da=String(d.getDate()).padStart(2,'0');
      return `${y}-${m}-${da}`;
    }
  
    function renderCalendar(){
      const year=currentDate.getFullYear();
      const month=currentDate.getMonth();
  
      els.title.textContent = currentDate.toLocaleString('default',{month:'long', year:'numeric'});
  
      const firstDay = new Date(year, month, 1).getDay();
      const daysInMonth = new Date(year, month+1, 0).getDate();
  
      els.grid.innerHTML = '';
  
      for(let i=0;i<firstDay;i++){
        const empty = document.createElement('div');
        empty.className = 'day muted';
        els.grid.appendChild(empty);
      }
  
      const today = new Date(); today.setHours(0,0,0,0);
  
      for(let day=1; day<=daysInMonth; day++){
        const date = new Date(year, month, day);
        const dateStr = ymdLocal(date);
  
        const btn = document.createElement('button');
        btn.className = 'day';
        btn.textContent = day;
  
        if (date.getTime() === today.getTime()) btn.classList.add('today');
        if (selectedDate && date.getTime() === selectedDate.getTime()) btn.classList.add('selected');
  
        const dayEvents = CALENDAR_EVENTS.filter(e => e.date === dateStr);
        if (dayEvents.length) btn.classList.add('has-event');
  
        btn.addEventListener('click', () => {
          if (isMobile()) {
            openDrawerWithDate(date, dayEvents);
          } else {
            showEventDetailsInPanel(date, dayEvents);
          }
        });
  
        els.grid.appendChild(btn);
      }
    }
  
    function formatLongDate(date){
      return date.toLocaleDateString('default', { weekday:'long', year:'numeric', month:'long', day:'numeric' });
    }
  
    function actionsHTML(event){
      const view = event.view_url ? `<a href="${event.view_url}" class="chip-btn">View Details</a>` : '';
      const gcal = (!event.past && event.gcal_url) ? `<a class="chip-btn" target="_blank" rel="noopener" href="${event.gcal_url}">Google</a>` : '';
      return [view, gcal].filter(Boolean).join('');
    }
  
    function showEventDetailsInPanel(date, dayEvents){
      selectedDate = new Date(date);
      els.details.innerHTML = `
        <div class="event-date">${formatLongDate(date)}</div>
        ${dayEvents.length
          ? dayEvents.map(ev => `
            <div class="event-detail-item">
              <div class="row">
                <h4 title="${ev.title}">${ev.title}</h4>
                <div class="actions">${actionsHTML(ev)}</div>
              </div>
              ${ev.time ? `<p class="event-time">${ev.time}</p>` : ''}
              ${ev.location ? `<p>${ev.location}</p>` : ''}
            </div>
          `).join('')
          : `<div class="empty">No events scheduled for this date</div>`
        }
      `;
      els.clearDetails.style.display = 'block';
      renderCalendar();
    }
  
    function openDrawerWithDate(date, dayEvents){
      els.drawerDate.textContent = formatLongDate(date);
      els.drawerContent.innerHTML = dayEvents.length
        ? dayEvents.map(ev => `
            <div class="event-item">
              <div class="event-title" title="${ev.title}">${ev.title}</div>
              <div class="event-acts">${actionsHTML(ev)}</div>
            </div>
          `).join('')
        : `<p class="empty">No events for this day.</p>`;
  
      els.drawer.classList.add('active');
      els.drawer.setAttribute('aria-hidden','false');
      els.drawerOverlay.classList.remove('hidden');
      els.drawerOverlay.focus();
    }
  
    function closeDrawer(){
      els.drawer.classList.remove('active');
      els.drawer.setAttribute('aria-hidden','true');
      els.drawerOverlay.classList.add('hidden');
    }
  
    els.prev.addEventListener('click', () => { currentDate.setMonth(currentDate.getMonth()-1); renderCalendar(); });
    els.next.addEventListener('click', () => { currentDate.setMonth(currentDate.getMonth()+1); renderCalendar(); });
  
    els.clearDetails.addEventListener('click', () => {
      selectedDate = null;
      els.details.innerHTML = '<div class="empty">Click an event in the calendar to view details</div>';
      els.clearDetails.style.display = 'none';
      renderCalendar();
    });
  
    els.drawerClose?.addEventListener('click', closeDrawer);
    els.drawerOverlay?.addEventListener('click', closeDrawer);
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeDrawer(); });
  
    async function loadCalendarFromAPI(){
      try{
        const res = await fetch('/api/calendar/?category=all', { headers:{'X-Requested-With':'XMLHttpRequest'} });
        const j = await res.json();
        if (Array.isArray(j.items)) CALENDAR_EVENTS = j.items;
      }catch(_e){ /* keep server-injected fallback */ }
      renderCalendar();
    }
  
    loadCalendarFromAPI();
    window.addEventListener('resize', () => renderCalendar());
  });
  