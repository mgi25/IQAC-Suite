(function(){
  const selectedCats = new Set();
  const grid = document.getElementById('ga-grid');
  const hidden = document.getElementById('ga-hidden');
  const countEl = document.getElementById('selectedCount');
  const summaryEl = document.getElementById('summaryText');

  const CAT_NAMES = {
    academic: 'Academic Excellence',
    professional: 'Professional Excellence',
    personality: 'Personality Development',
    leadership: 'Leadership',
    communication: 'Communication',
    social: 'Social Sensitivity'
  };

  function updateHiddenFromCheckboxes(){
    if(!hidden) return;
    const vals = Array.from(document.querySelectorAll('.ga-panel input[type="checkbox"]:checked')).map(cb => cb.value);
    hidden.value = vals.join(', ');
  }

  function updateSummary(){
    // Use category selections for count and label
    const count = selectedCats.size;
    if(countEl) countEl.textContent = `${count} selected`;
    if(count === 0){
      summaryEl.textContent = 'No attributes selected yet. Select relevant categories to proceed.';
    } else {
      const names = Array.from(selectedCats).map(k => CAT_NAMES[k] || k);
      summaryEl.innerHTML = `<strong>Selected:</strong> ${names.join(', ')}`;
    }
  }

  function togglePanel(card){
    const id = card.getAttribute('data-id');
    // Instead of in-place panel scroll, open modal for this category
    openModalForCategory(id, card);
  }

  function hydratePanelsFromSaved(){
    // Preselect checkboxes from saved string without opening inline panels
    const saved = (hidden && hidden.value || '').toLowerCase();
    Object.keys(CAT_NAMES).forEach(id => {
      const card = grid.querySelector(`.attribute-category[data-id="${id}"]`);
      if(!card) return;
      const panel = card.querySelector('.ga-panel');
      if(!panel) return;
      panel.querySelectorAll('input[type="checkbox"]').forEach(cb => {
        const v = (cb.value||'').toLowerCase();
        cb.checked = saved.includes(v);
      });
    });
    updateHiddenFromCheckboxes();
    recomputeSelectedCatsFromCheckboxes();
    updateSummary();
  }

  function recomputeSelectedCatsFromCheckboxes(){
    selectedCats.clear();
    Object.keys(CAT_NAMES).forEach(id => {
      const card = grid.querySelector(`.attribute-category[data-id="${id}"]`);
      const panel = card ? card.querySelector('.ga-panel') : null;
      if(!panel) return;
      const anyChecked = Array.from(panel.querySelectorAll('input[type="checkbox"]')).some(cb => cb.checked);
      if(card) card.classList.toggle('selected', anyChecked);
      if(anyChecked) selectedCats.add(id);
    });
  }

  // Grid interactions
  if(grid){
    grid.addEventListener('click', (e) => {
      const card = e.target.closest('.attribute-category');
      if(!card || !grid.contains(card)) return;
  // Modal approach: ignore inner panel areas if any
  if(e.target.closest('.ga-panel')) return;
      togglePanel(card);
    });
  }

  // Per-category actions
  document.addEventListener('click', (e) => {
    const actBtn = e.target.closest('[data-action]');
    if(!actBtn) return;
    const action = actBtn.getAttribute('data-action');
    const cat = actBtn.getAttribute('data-cat');
    const panel = document.querySelector(`.ga-panel[data-panel="${cat}"]`);
    if(!panel) return;
    const boxes = panel.querySelectorAll('input[type="checkbox"]');
    if(action === 'select-all'){
      boxes.forEach(cb => cb.checked = true);
    } else if(action === 'clear'){
      boxes.forEach(cb => cb.checked = false);
    }
    updateHiddenFromCheckboxes();
    recomputeSelectedCatsFromCheckboxes();
    updateSummary();
  });

  // Change events inside panels update hidden and keep summary
  document.addEventListener('change', (e) => {
    if(e.target.matches('.ga-panel input[type="checkbox"]')){
      updateHiddenFromCheckboxes();
      recomputeSelectedCatsFromCheckboxes();
      updateSummary();
    }
  });

  // Top controls
  const btnAll = document.getElementById('btn-select-all');
  const btnClear = document.getElementById('btn-clear-all');
  const btnAI = document.getElementById('btn-ai-recommend');

  btnAll && btnAll.addEventListener('click', () => {
    document.querySelectorAll('.ga-panel input[type="checkbox"]').forEach(cb => cb.checked = true);
    updateHiddenFromCheckboxes();
    recomputeSelectedCatsFromCheckboxes();
    updateSummary();
  });
  btnClear && btnClear.addEventListener('click', () => {
    selectedCats.clear();
  document.querySelectorAll('.attribute-category').forEach(c => c.classList.remove('selected'));
    document.querySelectorAll('.ga-panel input[type="checkbox"]').forEach(cb => cb.checked = false);
    updateHiddenFromCheckboxes();
    updateSummary();
  });
  btnAI && btnAI.addEventListener('click', () => {
    ['academic','communication','professional'].forEach(k => {
      const panel = document.querySelector(`.ga-panel[data-panel="${k}"]`);
      if(!panel) return;
      const first = panel.querySelector('input[type="checkbox"]');
      if(first) first.checked = true;
    });
    updateHiddenFromCheckboxes();
    recomputeSelectedCatsFromCheckboxes();
    updateSummary();
    toast('AI has suggested relevant attributes based on common event patterns');
  });

  function toast(message, type='info'){
    const el = document.createElement('div');
    el.style.cssText = `position:fixed;bottom:20px;right:20px;background:${type==='success'?'#10b981':type==='warning'?'#f59e0b':'#3b82f6'};color:#fff;padding:12px 16px;border-radius:8px;box-shadow:0 4px 12px rgba(0,0,0,.15);z-index:1000;max-width:300px;font-size:.9rem;`;
    el.textContent = message;
    document.body.appendChild(el);
    setTimeout(() => { el.style.opacity = '0'; el.style.transform = 'translateX(100%)'; setTimeout(() => el.remove(), 300); }, 2200);
  }

  // Initialize from server
  hydratePanelsFromSaved();

  // Modal handling
  const modal = document.getElementById('ga-modal');
  const modalBody = document.getElementById('ga-modal-body');
  const modalTitle = document.getElementById('ga-modal-title');
  const modalSelectAll = document.getElementById('ga-modal-select-all');
  const modalClear = document.getElementById('ga-modal-clear');
  const modalClose = document.getElementById('ga-modal-close');
  let currentCat = null;

  function openModalForCategory(catId, card){
    currentCat = catId;
    const name = CAT_NAMES[catId] || catId;
    modalTitle.textContent = name;
    // Clone the panel options into the modal body
    const panel = card.querySelector(`.ga-panel[data-panel="${catId}"]`);
    if(panel){
      const opts = panel.querySelector('.panel-options');
      modalBody.innerHTML = '';
      if(opts){ modalBody.appendChild(opts.cloneNode(true)); }
    } else {
      modalBody.textContent = 'No options available';
    }
    // Pre-checks are preserved by cloning; show modal
    modal.classList.add('show');
    modal.style.display = 'flex';
  }

  function closeModalSyncBack(){
    if(!currentCat) { hideModal(); return; }
    // Sync changes back to the real panel checkboxes
    const realPanel = document.querySelector(`.ga-panel[data-panel="${currentCat}"]`);
    const realBoxes = realPanel ? realPanel.querySelectorAll('input[type="checkbox"]') : [];
    const modalBoxes = modalBody ? modalBody.querySelectorAll('input[type="checkbox"]') : [];
    if(realBoxes && modalBoxes && realBoxes.length === modalBoxes.length){
      modalBoxes.forEach((mb, i) => { realBoxes[i].checked = mb.checked; });
    }
  updateHiddenFromCheckboxes();
  recomputeSelectedCatsFromCheckboxes();
  updateSummary();
  hideModal();
  }

  function hideModal(){
    modal.classList.remove('show');
    modal.style.display = 'none';
    currentCat = null;
  }

  modalSelectAll && modalSelectAll.addEventListener('click', () => {
    modalBody.querySelectorAll('input[type="checkbox"]').forEach(cb => cb.checked = true);
  });
  modalClear && modalClear.addEventListener('click', () => {
    modalBody.querySelectorAll('input[type="checkbox"]').forEach(cb => cb.checked = false);
  });
  modalClose && modalClose.addEventListener('click', () => closeModalSyncBack());
  modal && modal.addEventListener('click', (e) => { if(e.target === modal) closeModalSyncBack(); });
  document.addEventListener('keydown', (e) => {
    if(e.key === 'Escape' && modal.classList.contains('show')) closeModalSyncBack();
  });
})();
