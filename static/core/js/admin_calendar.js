/* Admin mini calendar - reuse CDL head dashboard data and calendar rules */
(function () {
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from((r || document).querySelectorAll(s));

  // State
  let EVENTS = [];
  let calRef = new Date();

  // Elements
  const els = {
    title: $('#calTitle'),
    grid: $('#calGrid'),
    prev: $('#calPrev'),
    next: $('#calNext'),
    details: $('#eventDetailsContent'),
    clearDetails: $('#clearEventDetails'),
    drawer: $('#eventSidebar'),
    drawerOverlay: $('#sidebarOverlay'),
    drawerDate: $('#sidebarDate'),
    drawerContent: $('#sidebarContent'),
    drawerClose: $('#sidebarClose'),
  };

  const fmt2 = v => String(v).padStart(2, '0');

  function buildCalendar() {
    if (!els.grid || !els.title) return;
    const year = calRef.getFullYear();
    const month = calRef.getMonth();
    els.title.textContent = calRef.toLocaleString(undefined, { month: 'long', year: 'numeric' });
    const first = new Date(year, month, 1);
    const last = new Date(year, month + 1, 0);
    const startIdx = first.getDay();
    const prevLast = new Date(year, month, 0).getDate();
    const cells = [];
    for (let i = startIdx - 1; i >= 0; i--) cells.push({ t: prevLast - i, iso: null, muted: true });
    for (let d = 1; d <= last.getDate(); d++) {
      const iso = `${year}-${fmt2(month + 1)}-${fmt2(d)}`;
      cells.push({ t: d, iso, muted: false });
    }
    while (cells.length % 7 !== 0) cells.push({ t: '', iso: null, muted: true });

    els.grid.innerHTML = cells.map(c => {
      if (!c.iso) return `<div class="day muted" data-date="">${c.t}</div>`;
      const isToday = c.iso === new Date().toISOString().slice(0, 10);
      const dayAll = EVENTS.filter(e => e.date === c.iso);
      const count = dayAll.length;
      const hasSupport = dayAll.some(e => e.type === 'cdl_support');
      // Always mark dates with events as 'has-event'. If any are support-type, also add 'has-meeting'.
      let markClass = '';
      if (count > 0) {
        markClass = ' has-event';
        if (hasSupport) markClass += ' has-meeting';
      }
      return `<div class="day${markClass}${isToday ? ' today' : ''}" data-date="${c.iso}">${c.t}</div>`;
    }).join('');

    $$('.day[data-date]', els.grid).forEach(d => d.addEventListener('click', () => {
      $$('.day.selected', els.grid).forEach(x => x.classList.remove('selected'));
      d.classList.add('selected');
      if (window.matchMedia('(max-width: 992px)').matches) {
        openDrawerWithDate(d.dataset.date);
      } else {
        openDay(d.dataset.date);
      }
    }));
  }

  function openDay(iso) {
    const items = EVENTS.filter(e => e.date === iso);
    const box = els.details;
    const clearBtn = els.clearDetails;
    if (!box) return;
    const dateStr = new Date(iso).toLocaleDateString(undefined, { day: '2-digit', month: '2-digit', year: 'numeric' });
    if (!items.length) {
      box.innerHTML = `<div class="empty">No events for ${dateStr}</div>`;
      clearBtn && (clearBtn.style.display = 'none');
      return;
    }
    box.innerHTML = items.map(e => `
      <div class="event-detail-item">
        <div class="event-detail-title with-actions">
          <span class="title-text">${e.title}</span>
          <div class="title-actions">
            <a class="chip-btn" href="${e.view_url || ('/proposal/' + (e.id||'') + '/detail/')}">View</a>
          </div>
        </div>
        <div class="event-detail-meta">${dateStr} • Status: ${e.status || 'N/A'} • Org: ${e.organization || 'N/A'}</div>
      </div>
    `).join('');
    if (clearBtn) {
      clearBtn.style.display = 'inline-flex';
      clearBtn.onclick = () => {
        box.innerHTML = '<div class="empty">Click an event in the calendar to view details</div>';
        clearBtn.style.display = 'none';
        $$('.day.selected', els.grid).forEach(x => x.classList.remove('selected'));
      };
    }
  }

  function openDrawerWithDate(iso) {
    const items = EVENTS.filter(e => e.date === iso);
    els.drawerDate.textContent = new Date(iso).toLocaleDateString(undefined, { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
    els.drawerContent.innerHTML = items.length
      ? items.map(e => `
        <div class="event-item">
          <div class="event-title" title="${e.title}">${e.title}</div>
          <div class="event-acts"><a class="chip-btn" href="${e.view_url || ('/proposal/' + (e.id||'') + '/detail/')}">View</a></div>
        </div>
      `).join('')
      : `<p class="empty">No events for this day.</p>`;
    els.drawer.classList.add('active');
    els.drawer.setAttribute('aria-hidden', 'false');
    els.drawerOverlay.classList.remove('hidden');
    els.drawerOverlay.focus();
  }

  function closeDrawer() {
    els.drawer.classList.remove('active');
    els.drawer.setAttribute('aria-hidden', 'true');
    els.drawerOverlay.classList.add('hidden');
  }

  els.prev?.addEventListener('click', () => { calRef = new Date(calRef.getFullYear(), calRef.getMonth() - 1, 1); buildCalendar(); });
  els.next?.addEventListener('click', () => { calRef = new Date(calRef.getFullYear(), calRef.getMonth() + 1, 1); buildCalendar(); });
  els.clearDetails?.addEventListener('click', () => {
    els.details.innerHTML = '<div class="empty">Click an event in the calendar to view details</div>';
    els.clearDetails.style.display = 'none';
    $$('.day.selected', els.grid).forEach(x => x.classList.remove('selected'));
  });
  els.drawerClose?.addEventListener('click', closeDrawer);
  els.drawerOverlay?.addEventListener('click', closeDrawer);
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeDrawer(); });

  // Load events from CDL head dashboard API (month-scoped behavior is handled client-side by buildCalendar)
  async function loadCalendarFromAPI(scope='all') {
    try {
      const res = await fetch(`/api/cdl/head-dashboard/?scope=${encodeURIComponent(scope)}`, { headers: { 'Accept': 'application/json' } });
      if(!res.ok) throw new Error('Network error');
      const data = await res.json();
      EVENTS = (data.events || []).filter(Boolean);
      // Normalize API dates to YYYY-MM-DD (strip time if present)
      EVENTS = EVENTS.map(e => ({ ...e, date: (e.date || '').toString().split('T')[0] || null }));

      // Always attempt to merge inline server-provided `#events-data` (admin template) so that
      // approved+finalized admin events (which admin template already provides) are visible even
      // when the CDL API returns only finalized events.
      if (document.getElementById('events-data')) {
        try {
          const el = document.getElementById('events-data');
          const raw = el.textContent || el.innerText || '';
          const parsed = JSON.parse(raw || '[]');
          if (Array.isArray(parsed) && parsed.length) {
            const inline = parsed.map(it => ({
              id: it.id || it.event_id || null,
              title: it.title || it.event_title || it.event_title || '',
              date: ((it.date || it.start_date || it.event_start_date) || '').toString().split('T')[0] || null,
              status: (it.status || '').toString().toLowerCase(),
              organization: it.organization || it.organization__name || null,
              type: it.type || 'proposal',
              view_url: it.view_url || it.url || null,
            })).filter(Boolean);

            // merge deduping by date+title (safe heuristic)
            const map = new Map();
            EVENTS.concat(inline).forEach(ev => {
              const key = `${(ev.date||'')}|${(ev.title||'')}`;
              if (!map.has(key)) map.set(key, ev);
            });
            EVENTS = Array.from(map.values());
            console.debug('admin_calendar: merged inline events, total=', EVENTS.length);
          }
        } catch (parseE) {
          console.warn('admin_calendar: failed to parse inline events-data', parseE);
        }
      }
    } catch (e) {
      console.warn('Failed to load calendar events for admin dashboard:', e);
      EVENTS = [];
    }
    buildCalendar();
  }

  document.addEventListener('DOMContentLoaded', () => {
    loadCalendarFromAPI('all');
    window.addEventListener('resize', buildCalendar);
  });
})();
  