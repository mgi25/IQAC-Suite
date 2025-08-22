/* Academic Year Settings – Tabs + Modal + Preview + Validation (frontend only) */
/* Tabs: match Master Data toolbar tabs */
(function () {
    const $ = (s, r = document) => r.querySelector(s);
    const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
  
    const tabs = $$('.tab-btn');
    const panels = $$('.tab-panel');
  
    tabs.forEach(tab => {
      tab.addEventListener('click', () => {
        tabs.forEach(t => { t.classList.remove('is-active'); t.setAttribute('aria-selected','false'); });
        panels.forEach(p => p.classList.remove('is-active'));
        tab.classList.add('is-active'); tab.setAttribute('aria-selected','true');
        $('#' + tab.getAttribute('aria-controls'))?.classList.add('is-active');
      });
    });
  
  
    /* ---------- Modal ---------- */
    const modal = $('#yearModal');
    const titleEl = $('#modalTitle');
    const openAddBtn = $('#btnOpenAdd');
    const closeEls = $$('[data-close]');
    const form = $('#academicYearForm');
    const idInput = $('#yearId');
    const startInput = $('#startDate');
    const endInput = $('#endDate');
    const yearLabel = $('#yearLabel');
    const notices = $('#formNotices');
  
    function openModal(mode, payload) {
      // mode: 'add' | 'edit'
      if (mode === 'add') {
        titleEl.innerHTML = '<i class="fas fa-plus-circle"></i> Add Academic Year';
        form.reset();
        idInput.value = '';
        yearLabel.textContent = '—';
      } else {
        titleEl.innerHTML = '<i class="fas fa-edit"></i> Edit Academic Year';
        idInput.value = payload?.id || '';
        startInput.value = payload?.start || '';
        endInput.value = payload?.end || '';
        deriveYearLabel();
      }
      modal.classList.add('is-open');
      modal.setAttribute('aria-hidden', 'false');
      startInput?.focus();
    }
    function closeModal() {
      modal.classList.remove('is-open');
      modal.setAttribute('aria-hidden', 'true');
    }
  
    openAddBtn?.addEventListener('click', () => openModal('add'));
    closeEls.forEach(el => el.addEventListener('click', closeModal));
    modal?.addEventListener('click', (e) => { if (e.target.dataset.close !== undefined) closeModal(); });
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && modal.classList.contains('is-open')) closeModal(); });
  
    // Edit buttons: open modal prefilled (and keep existing ?edit= navigation harmless)
    $$('.js-edit').forEach(a => {
      a.addEventListener('click', (e) => {
        // Prefer instant modal; let the href remain for fallback/refresh
        e.preventDefault();
        openModal('edit', {
          id: a.dataset.id,
          start: a.dataset.start,
          end: a.dataset.end
        });
        // Update URL without reload so backend routes remain consistent
        const url = new URL(window.location);
        url.searchParams.set('edit', a.dataset.id);
        window.history.replaceState({}, '', url);
      });
    });
  
    // If backend provided edit_year (via ?edit=), auto-open modal
    (function autoOpenFromServer(){
      const el = $('#editYearData');
      if (!el) return;
      try {
        const data = JSON.parse(el.textContent.trim());
        openModal('edit', data);
      } catch {}
    })();
  
    /* ---------- Year Label ---------- */
    function deriveYearLabel() {
      if (!startInput.value || !endInput.value) { yearLabel.textContent = '—'; return; }
      const s = new Date(startInput.value);
      const e = new Date(endInput.value);
      if (Number.isNaN(s.getTime()) || Number.isNaN(e.getTime())) { yearLabel.textContent = '—'; return; }
      const y1 = s.getFullYear();
      const right = String(e.getFullYear()).slice(-2);
      yearLabel.textContent = `${y1}–${right}`;
    }
    startInput?.addEventListener('change', deriveYearLabel);
    endInput?.addEventListener('change', deriveYearLabel);
  
    /* ---------- Validation (informational) ---------- */
    function clearNotices(){ notices.innerHTML = ''; }
    function pushNotice(msg, type='warn'){
      const d = document.createElement('div');
      d.className = `notice ${type}`;
      d.textContent = msg;
      notices.appendChild(d);
    }
  
    // Active ranges from JSON (for overlap hint)
    const activeRanges = (() => {
      try {
        const raw = $('#activeYearsData')?.textContent?.trim();
        if (!raw) return [];
        const parsed = JSON.parse(raw);
        return parsed.map(r => ({
          s: new Date(r.start + 'T00:00:00'),
          e: new Date(r.end + 'T23:59:59')
        })).filter(r => !Number.isNaN(r.s.getTime()) && !Number.isNaN(r.e.getTime()));
      } catch { return []; }
    })();
  
    function rangesOverlap(aStart, aEnd, bStart, bEnd){ return aStart <= bEnd && bStart <= aEnd; }
  
    form?.addEventListener('submit', (e) => {
      clearNotices();
      const sv = startInput.value, ev = endInput.value;
      if (!sv || !ev) return true;
      const s = new Date(sv), en = new Date(ev);
      if (en < s) { e.preventDefault(); pushNotice('End Date Cannot Be Earlier Than Start Date.', 'error'); return false; }
      const conflict = activeRanges.some(r => rangesOverlap(s, en, r.s, r.e));
      if (conflict) pushNotice('This Range Overlaps An Existing Active Academic Year. Please Confirm.', 'warn');
      else pushNotice('Dates Look Good.', 'ok');
      // Allow submit to proceed to backend.
      return true;
    });
  })();
  