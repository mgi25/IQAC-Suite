/* POs & PSOs Management – Master Data–style controls + counts (frontend only) */
(function () {
    // ——— Mini helpers
    const $ = (s, r=document) => r.querySelector(s);
    const $$ = (s, r=document) => Array.from(r.querySelectorAll(s));
  
    let searchDebounceTimer = null;
  
    // Boot
    document.addEventListener('DOMContentLoaded', () => {
      initControls();
      initPanels();
      hydrateCountsFromServer();
      if (!window.orgOutcomeCounts) lazyFetchCounts();
      wireShortcuts();
    });
  
    // Controls (Category → Status → Search), identical behavior to MD
    function initControls(){
      const cat   = $('#categoryFilter');
      const stat  = $('#statusFilter');
      const search= $('#universalSearch');
      const clear = $('#searchClearBtn');
  
      // Restore last category
      const saved = loadLastCategory();
      if (cat && saved) cat.value = saved;
  
      const activeKey = cat?.value || $$('.tab-panel')[0]?.dataset.type || null;
      setActiveCategory(activeKey, { scroll:false });
      applyFilters(); // initial pass
  
      cat?.addEventListener('change', e => {
        const key = e.target.value;
        saveLastCategory(key);
        setActiveCategory(key, { scroll:true });
        applyFilters();
      });
  
      stat?.addEventListener('change', applyFilters);
  
      const onSearch = ()=>{
        if (searchDebounceTimer) clearTimeout(searchDebounceTimer);
        searchDebounceTimer = setTimeout(applyFilters, 220);
      };
      search?.addEventListener('input', onSearch);
  
      clear?.addEventListener('click', ()=>{
        if (!search) return;
        search.value = '';
        applyFilters();
        search.focus();
      });
    }
  
    function initPanels(){
      // Ensure only active panel is visible
      updatePanelVisibility(/*force*/true);
    }
  
    function setActiveCategory(typeKey, {scroll=true}={}){
      $$('.tab-panel').forEach(p => p.classList.toggle('is-active', p.dataset.type === typeKey));
      updatePanelVisibility(/*force*/true);
      if (scroll){
        const wrap = $(`#panel-${typeKey} .table-wrap`);
        if (wrap) wrap.scrollTop = 0;
      }
    }
  
    function updatePanelVisibility(force=false){
      const q = ($('#universalSearch')?.value || '').trim();
      const searching = q.length > 0;
  
      $$('.tab-panel').forEach(panel=>{
        // Same rule as MD: only active panel visible (search is scoped to category)
        panel.style.display = panel.classList.contains('is-active') ? 'block' : 'none';
        if (force && panel.classList.contains('is-active')) {
          const wrap = panel.querySelector('.table-wrap');
          if (wrap) wrap.scrollTop = 0;
        }
      });
    }
  
    function applyFilters(){
      updatePanelVisibility();
  
      const panel = $('.tab-panel.is-active');
      if (!panel) return;
  
      const status = $('#statusFilter')?.value || 'all';
      const q = ($('#universalSearch')?.value || '').toLowerCase().trim();
  
      const rows = [...panel.querySelectorAll('tbody tr')].filter(tr => tr.querySelector('td'));
      let anyMatch = false;
  
      rows.forEach(tr=>{
        const isActive = tr.querySelector('.status-badge')?.classList.contains('status-active');
        const nameText = tr.querySelector('td[data-label="Organization"]')?.textContent.toLowerCase() || '';
  
        let show = true;
        if (status === 'active')   show = !!isActive;
        if (status === 'inactive') show = !isActive;
        if (q) show = show && nameText.includes(q);
  
        tr.style.display = show ? '' : 'none';
        if (show) anyMatch = true;
      });
  
      // Default sort: Organization name A→Z (matches MD)
      const tbody = panel.querySelector('tbody');
      const dataRows = rows.filter(r => !r.querySelector('td.text-center'));
      dataRows.sort((a,b)=>{
        const an = a.querySelector('td[data-label="Organization"]')?.textContent.trim().toLowerCase() || '';
        const bn = b.querySelector('td[data-label="Organization"]')?.textContent.trim().toLowerCase() || '';
        return an.localeCompare(bn);
      });
      dataRows.forEach(r => tbody.appendChild(r));
  
      // No-results banner
      const notFound = $('#search-not-found');
      const strong = notFound?.querySelector('strong');
      if (q && !anyMatch){
        if (strong) strong.textContent = q;
        notFound.style.display = 'block';
      } else {
        if (notFound) notFound.style.display = 'none';
      }
    }
  
    // —— Counts (PO/PSO)
    function hydrateCountsFromServer(){
      const data = window.orgOutcomeCounts;
      if (!data || typeof data !== 'object') return;
      Object.keys(data).forEach(orgId => {
        const po  = Number(data[orgId]?.po_count  || 0);
        const pso = Number(data[orgId]?.pso_count || 0);
        updateRowCounts(orgId, po, pso);
      });
    }
  
    function lazyFetchCounts(){
      // Fetch counts for visible rows only, on idle
      const rows = $$('.tab-panel.is-active tbody tr');
      rows.forEach(row => {
        const orgId = row.dataset.id;
        const poSpan  = row.querySelector('td[data-label="POs"]  .count');
        const psoSpan = row.querySelector('td[data-label="PSOs"] .count');
        const poVal  = Number(poSpan?.textContent || 0);
        const psoVal = Number(psoSpan?.textContent || 0);
        if (poVal > 0 || psoVal > 0) return;
  
        fetch(`/api/organizations/${orgId}/outcomes/`)
          .then(r => r.ok ? r.json() : Promise.reject(r))
          .then(json => {
            if (json && json.success) updateRowCounts(orgId, json.po_count || 0, json.pso_count || 0);
          })
          .catch(()=>{ /* silent */ });
      });
    }
  
    function updateRowCounts(orgId, poCount, psoCount){
      const po  = document.querySelector(`a.chip-count[data-org-id="${orgId}"][data-kind="po"]  .count`);
      const pso = document.querySelector(`a.chip-count[data-org-id="${orgId}"][data-kind="pso"] .count`);
      if (po)  po.textContent  = String(poCount);
      if (pso) pso.textContent = String(psoCount);
    }
  
    // —— Utilities (same as MD semantics)
    function saveLastCategory(k){ try{ localStorage.setItem('mdm_active_category', k); }catch(e){} }
    function loadLastCategory(){ try{ return localStorage.getItem('mdm_active_category'); }catch(e){ return null; } }
  
    function wireShortcuts(){
      document.addEventListener('keydown',(e)=>{
        const isMac = navigator.platform.toUpperCase().includes('MAC');
        if ((isMac && e.metaKey && e.key.toLowerCase()==='k') || (!isMac && e.ctrlKey && e.key.toLowerCase()==='k')){
          e.preventDefault(); $('#universalSearch')?.focus();
        }
      });
    }
  })();
  