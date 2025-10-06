/* Shared calendar module (reusable) */
(function(){
  const $ = (s,r=document)=>r.querySelector(s);
  const $$ = (s,r=document)=>Array.from((r||document).querySelectorAll(s));

  const fmt2 = v => String(v).padStart(2,'0');

  let STATE = {
    endpoint: '/api/calendar/?category=all',
    inlineElem: null,
    events: [],
    calRef: new Date(),
    showOnlyStartDate: false,
  };

  function buildCalendar() {
    const head = $('#calTitle');
    const grid = $('#calGrid');
    if(!head || !grid) return;
    const calRef = STATE.calRef;
    head.textContent = calRef.toLocaleString(undefined, { month: 'long', year: 'numeric' });
    const year = calRef.getFullYear(), month = calRef.getMonth();
    const first = new Date(year, month, 1);
    const last  = new Date(year, month + 1, 0);
    const startIdx = first.getDay();

    const cells = [];
    for(let i=0;i<startIdx;i++) cells.push({text:'', iso:null});
    for(let d=1; d<=last.getDate(); d++){
      const dt = new Date(year, month, d);
      const iso = `${dt.getFullYear()}-${fmt2(dt.getMonth()+1)}-${fmt2(dt.getDate())}`;
      cells.push({text:d, iso});
    }

    grid.innerHTML = cells.map(c => {
      if(!c.iso) return `<div class="day muted"></div>`;
      const isToday = c.iso === new Date().toISOString().slice(0,10);
      const dayEvents = STATE.events.filter(e => e.date === c.iso);
      const hasEvent = dayEvents.length > 0;
      const cls = ['day']; if (hasEvent) cls.push('has-event'); if (isToday) cls.push('today');
      return `<div class="${cls.join(' ')}" data-date="${c.iso}" tabindex="0" role="button">${c.text}</div>`;
    }).join('');

    $$('.day[data-date]', grid).forEach(el=>el.addEventListener('click', ()=>{
      $$('.day.selected', grid).forEach(x=>x.classList.remove('selected'));
      el.classList.add('selected');
      if (window.matchMedia('(max-width: 992px)').matches) {
        openDrawer(el.dataset.date);
      } else {
        openDay(el.dataset.date);
      }
    }));
  }

  function openDay(iso){
    const items = STATE.events.filter(e=>e.date===iso);
    const box = $('#eventDetailsContent');
    const clearBtn = $('#clearEventDetails');
    if(!box) return;
    const dateStr = iso ? new Date(iso).toLocaleDateString() : '';
    if(!items.length){ box.innerHTML = `<div class="empty">No events for ${dateStr}</div>`; if(clearBtn) clearBtn.style.display='none'; return; }
    box.innerHTML = items.map(e => `
      <div class="event-detail-item">
        <div class="row"><h4>${e.title}</h4><div class="actions">${e.view_url?`<a class="chip-btn" href="${e.view_url}">View</a>`:''}${!e.past && e.gcal_url?`<a class="chip-btn" target="_blank" href="${e.gcal_url}">Google</a>`:''}</div></div>
        <div class="event-detail-meta">${e.datetime?new Date(e.datetime).toLocaleString():'All day'}${e.venue?`<br><i class="fa-solid fa-location-dot"></i> ${e.venue}`:''}</div>
      </div>
    `).join('');
    if (clearBtn) { clearBtn.style.display='inline-flex'; clearBtn.onclick = ()=>{ box.innerHTML = '<div class="empty">Click an event in the calendar to view details</div>'; clearBtn.style.display='none'; $$('.day.selected').forEach(x=>x.classList.remove('selected')); }; }
  }

  function openDrawer(iso){
    const items = STATE.events.filter(e=>e.date===iso);
    const drawer = $('#eventSidebar');
    const overlay = $('#sidebarOverlay');
    const dateEl = $('#sidebarDate');
    const content = $('#sidebarContent');
    if(!drawer||!overlay||!content||!dateEl) return;
    dateEl.textContent = new Date(iso).toLocaleDateString(undefined, { weekday:'long', year:'numeric', month:'long', day:'numeric' });
    content.innerHTML = items.length ? items.map(e=>`<div class="event-item"><div class="event-title">${e.title}</div><div class="event-acts"><a class="chip-btn" href="${e.view_url||''}">View</a></div></div>`).join('') : '<p class="empty">No events for this day.</p>';
    drawer.classList.add('active'); drawer.setAttribute('aria-hidden','false'); overlay.classList.remove('hidden'); overlay.focus();
  }

  function closeDrawer(){ const drawer = $('#eventSidebar'), overlay = $('#sidebarOverlay'); if(drawer){ drawer.classList.remove('active'); drawer.setAttribute('aria-hidden','true'); } if(overlay) overlay.classList.add('hidden'); }

  async function loadEventsFromEndpoint(endpoint){
    try {
      const res = await fetch(endpoint, { headers: { 'X-Requested-With':'XMLHttpRequest', 'Accept':'application/json' } });
      if (!res.ok) throw new Error('Network');
      const j = await res.json();
      const items = j.items || j.events || j || [];
      // Normalize items: prefer start date fields and compute date as YYYY-MM-DD
      STATE.events = (Array.isArray(items) ? items : []).map(e => ({
        ...e,
        start_date: (e.start_date || e.date || e.event_start_date || '').toString(),
        end_date: (e.end_date || e.event_end_date || '').toString(),
        date: ((e.start_date || e.date || e.event_start_date) || '').toString().split('T')[0] || null
      })).filter(ev => {
        if (!STATE.showOnlyStartDate) return true;
        // showOnlyStartDate: keep only events that have a start date and no meaningful end_date
        const hasStart = !!(ev.date);
        const hasEnd = !!(ev.end_date && ev.end_date.trim());
        return hasStart && !hasEnd;
      });
    } catch (e) {
      console.warn('calendar: failed to load events', e);
      STATE.events = [];
    }

  // try merge inline JSON if present (admin templates provide #events-data)
    if (STATE.inlineElem) {
      try {
        const el = document.getElementById(STATE.inlineElem);
        if (el) {
          const raw = el.textContent || el.innerText || '';
          const parsed = JSON.parse(raw || '[]');
          if (Array.isArray(parsed) && parsed.length) {
            const inline = parsed.map(it => ({
              id: it.id || it.event_id || null,
              title: it.title || it.event_title || '',
              start_date: (it.start_date || it.date || it.event_start_date || '').toString(),
              end_date: (it.end_date || it.event_end_date || '').toString(),
              date: ((it.date || it.start_date || it.event_start_date) || '').toString().split('T')[0] || null,
              status: it.status || '',
              organization: it.organization || null,
              view_url: it.view_url || it.url || null,
              type: it.type || 'event'
            })).filter(ev => {
              if (!STATE.showOnlyStartDate) return true;
              const hasStart = !!(ev.date);
              const hasEnd = !!(ev.end_date && ev.end_date.trim());
              return hasStart && !hasEnd;
            });

            const map = new Map();
            STATE.events.concat(inline).forEach(ev => {
              const key = `${ev.date || ''}|${(ev.title || '')}`;
              if (!map.has(key)) map.set(key, ev);
            });
            STATE.events = Array.from(map.values());
          }
        }
      } catch (ex) {
        console.warn('calendar: inline parse failed', ex);
      }
    }

    // expose the latest events for page scripts that still read a global
    try{ window.CALENDAR_EVENTS = STATE.events; }catch(e){}
    buildCalendar();
  }

  // Public API
  window.CalendarModule = {
    init(opts={}){
      STATE.endpoint = opts.endpoint || STATE.endpoint;
      STATE.inlineElem = opts.inlineEventsElementId || null;
      STATE.showOnlyStartDate = !!opts.showOnlyStartDate;
      if (opts.initialDate) STATE.calRef = new Date(opts.initialDate);
      document.getElementById('calPrev')?.addEventListener('click', ()=>{ STATE.calRef = new Date(STATE.calRef.getFullYear(), STATE.calRef.getMonth()-1, 1); buildCalendar(); });
      document.getElementById('calNext')?.addEventListener('click', ()=>{ STATE.calRef = new Date(STATE.calRef.getFullYear(), STATE.calRef.getMonth()+1, 1); buildCalendar(); });
      document.getElementById('sidebarClose')?.addEventListener('click', closeDrawer);
      document.getElementById('sidebarOverlay')?.addEventListener('click', closeDrawer);
      document.addEventListener('keydown', (e)=>{ if(e.key==='Escape') closeDrawer(); });
      // load
      loadEventsFromEndpoint(STATE.endpoint);
      window.addEventListener('resize', ()=>buildCalendar());
    }
    ,
    // helper for other scripts to read the currently loaded events
    getEvents(){ return STATE.events; }
  };

})();
