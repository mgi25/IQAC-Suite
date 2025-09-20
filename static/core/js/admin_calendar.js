/* Admin mini calendar + responsive drawer sync (no backend changes) */


// Admin Calendar Logic (CDL-style, but keep admin UI)
(function () {
  const $ = (s, r = document) => r.querySelector(s);
  // State
  let EVENTS = [];
  let calRef = new Date();
  let selectedDate = null;

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
  function ymdLocal(d) {
    const y = d.getFullYear();
    const m = fmt2(d.getMonth() + 1);
    const da = fmt2(d.getDate());
    return `${y}-${m}-${da}`;
  }

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
      if (!c.iso) {
        return `<div class="day muted" data-date="">${c.t}</div>`;
      }
      const isToday = c.iso === new Date().toISOString().slice(0, 10);
      // Show dot for both approved and finalized events
      let dayEvents = EVENTS.filter(e => e.date === c.iso && ['approved', 'finalized'].includes((e.status || '').toLowerCase()));
      const hasEvents = dayEvents.length > 0;
      return `<div class="day${hasEvents ? ' has-event' : ''}${isToday ? ' today' : ''}" data-date="${c.iso}">${c.t}</div>`;
    }).join('');
    $$('.day[data-date]', els.grid).forEach(d => d.addEventListener('click', () => {
      $$('.day.selected', els.grid).forEach(x => x.classList.remove('selected'));
      d.classList.add('selected');
      openDay(d.dataset.date);
    }));
  }

  function openDay(iso) {
    // Only approved/finalized events on day open
    let items = EVENTS.filter(e => e.date === iso && ['approved', 'finalized'].includes((e.status || '').toLowerCase()));
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
            <a class="chip-btn" href="${e.view_url || '#'}">View</a>
          </div>
        </div>
        <div class="event-detail-meta">${dateStr} • Org: ${e.organization || 'N/A'} • Status: ${e.status}</div>
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

  // Mobile drawer
  function openDrawerWithDate(iso) {
    const items = EVENTS.filter(e => e.date === iso && ['approved', 'finalized'].includes((e.status || '').toLowerCase()));
    els.drawerDate.textContent = new Date(iso).toLocaleDateString(undefined, { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
    els.drawerContent.innerHTML = items.length
      ? items.map(e => `
        <div class="event-item">
          <div class="event-title" title="${e.title}">${e.title}</div>
          <div class="event-acts"><a class="chip-btn" href="${e.view_url || '#'}">View</a></div>
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

  // Helper for querySelectorAll
  function $$(s, r = document) { return Array.from((r || document).querySelectorAll(s)); }

  // Load events from API
  async function loadCalendarFromAPI() {
    try {
      const res = await fetch('/api/calendar/?category=all', { headers: { 'X-Requested-With': 'XMLHttpRequest' } });
      const j = await res.json();
      // Accept both array and {items:[]} for compatibility
      if (Array.isArray(j)) {
        EVENTS = j;
      } else if (Array.isArray(j.items)) {
        EVENTS = j.items;
      } else {
        EVENTS = [];
      }
    } catch (_e) { EVENTS = []; }
    buildCalendar();
  }

  // Responsive: open drawer on mobile, panel on desktop
  els.grid?.addEventListener('click', e => {
    const day = e.target.closest('.day[data-date]');
    if (!day || !day.dataset.date) return;
    if (window.matchMedia('(max-width: 992px)').matches) {
      openDrawerWithDate(day.dataset.date);
    } else {
      openDay(day.dataset.date);
    }
  });

  document.addEventListener('DOMContentLoaded', () => {
    loadCalendarFromAPI();
    window.addEventListener('resize', buildCalendar);
  });
})();
  