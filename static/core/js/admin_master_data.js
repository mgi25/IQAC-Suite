/**
 * Master Data Management – Category-first controls, live filters, sticky table,
 * icon-only actions. Frontend-only; existing endpoints preserved.
 */

// ======= Globals =======
let orgsByType = {};
let activeTypeKey = null;
let currentEditingRow = null;
let searchDebounceTimer = null;

// ======= Boot =======
document.addEventListener('DOMContentLoaded', () => {
  orgsByType = window.orgsByType || {};
  initControls();
  initTables();
  initializeInlineEditing();
  initializeFormHandlers();
  wireShortcuts();
  showSuccessToastIfNeeded();
});

// ======= Controls wiring =======
function initControls(){
  const cat = document.getElementById('categoryFilter');
  const stat = document.getElementById('statusFilter');
  const search = document.getElementById('universalSearch');
  const clear = document.getElementById('searchClearBtn');

  // Load last category (fallback to first)
  const saved = loadLastCategory();
  if (cat && saved) cat.value = saved;
  activeTypeKey = cat?.value || document.querySelector('.tab-panel')?.dataset.type || null;

  // Reflect category into panels immediately
  setActiveCategory(activeTypeKey, {scroll:false});

  // Events
  cat?.addEventListener('change', e => {
    activeTypeKey = e.target.value;
    saveLastCategory(activeTypeKey);
    setActiveCategory(activeTypeKey, {scroll:true});
    // default client-side sort by name asc per spec (applied by applyFilters)
    applyFilters(); // refresh visibility
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

  // AddFromSearch
  const addFromSearchBtn = document.getElementById('addFromSearchBtn');
  if (addFromSearchBtn){
    addFromSearchBtn.onclick = function(){
      const q = (search?.value || '').trim();
      if (q) addNewEntryFromSearch(q);
    };
  }

  // Buttons open panels
  document.getElementById('addNewEntryBtn')?.addEventListener('click', (e)=>{
    e.preventDefault();
    showPanel('add-form-container'); hidePanel('add-category-container');
    // preset entry form category to current selection
    const sel = document.getElementById('categorySelect');
    if (sel && activeTypeKey) { sel.value = activeTypeKey; sel.dispatchEvent(new Event('change')); }
  });

  document.getElementById('addNewCategoryBtn')?.addEventListener('click', (e)=>{
    e.preventDefault(); showPanel('add-category-container'); hidePanel('add-form-container');
  });
}

function initTables(){
  // Ensure only active category panel is visible initially
  updatePanelVisibility(/*force*/true);
  // Initial filter pass
  applyFilters();
}

// ======= Category switching & panel visibility =======
function setActiveCategory(typeKey, {scroll=true}={}){
  document.querySelectorAll('.tab-panel').forEach(p => {
    p.classList.toggle('is-active', p.dataset.type === typeKey);
  });
  updatePanelVisibility(/*force*/true);
  if (scroll){
    const wrap = document.querySelector(`#panel-${typeKey} .table-wrap`);
    if (wrap) wrap.scrollTop = 0;
  }
}

function updatePanelVisibility(force=false){
  const q = (document.getElementById('universalSearch')?.value || '').trim();
  const searching = q.length > 0;

  document.querySelectorAll('.tab-panel').forEach(panel=>{
    if (searching) {
      // During search: only show the active panel (scope is selected category)
      panel.style.display = panel.classList.contains('is-active') ? 'block' : 'none';
    } else {
      // No search: only active panel visible
      panel.style.display = panel.classList.contains('is-active') ? 'block' : 'none';
    }
    if (force && panel.classList.contains('is-active')) {
      const wrap = panel.querySelector('.table-wrap');
      if (wrap) wrap.scrollTop = 0;
    }
  });
}

function saveLastCategory(k){ try{ localStorage.setItem('mdm_active_category', k); }catch(e){} }
function loadLastCategory(){ try{ return localStorage.getItem('mdm_active_category'); }catch(e){ return null; } }

// ======= Filters (status + search) and default sort =======
function applyFilters(){
  updatePanelVisibility();

  const panel = document.querySelector('.tab-panel.is-active');
  if (!panel) return;

  const status = document.getElementById('statusFilter')?.value || 'all';
  const q = (document.getElementById('universalSearch')?.value || '').toLowerCase().trim();

  // Rows (ignore placeholder empty row)
  const rows = [...panel.querySelectorAll('tbody tr')].filter(tr => tr.querySelector('td'));

  // Filter rows by status + search
  let anyMatch = false;
  rows.forEach(tr=>{
    const isActive = tr.querySelector('.status-badge')?.classList.contains('status-active');
    const nameText = tr.querySelector('td[data-label="Name"]')?.textContent.toLowerCase() || '';
    let show = true;
    if (status === 'active') show = !!isActive;
    if (status === 'inactive') show = !isActive;
    if (q) show = show && nameText.includes(q);
    tr.style.display = show ? '' : 'none';
    if (show) anyMatch = true;
  });

  // Default sort: Name A→Z (per spec) whenever category/filters change
  const tbody = panel.querySelector('tbody');
  const dataRows = rows.filter(r => !r.querySelector('td.text-center'));
  dataRows.sort((a,b)=>{
    const an = a.querySelector('td[data-label="Name"]')?.textContent.trim().toLowerCase() || '';
    const bn = b.querySelector('td[data-label="Name"]')?.textContent.trim().toLowerCase() || '';
    return an.localeCompare(bn);
  });
  dataRows.forEach(r => tbody.appendChild(r));

  // No results panel
  const notFound = document.getElementById('search-not-found');
  const notFoundText = notFound?.querySelector('strong');
  if (q && !anyMatch){
    if (notFoundText) notFoundText.textContent = q;
    notFound.style.display = 'block';
  } else {
    if (notFound) notFound.style.display = 'none';
  }
}

// ======= Inline Editing (icon-only “Edit”) =======
function initializeInlineEditing(){
  document.addEventListener('click', function(e){
    if (e.target.closest('.btn-edit')) {
      e.preventDefault();
      const row = e.target.closest('tr');
      startInlineEdit(row);
    } else if (e.target.closest('.btn-row-save')) {
      e.preventDefault();
      const row = e.target.closest('tr');
      saveInlineEdit(row);
    } else if (e.target.closest('.btn-row-cancel')) {
      e.preventDefault();
      const row = e.target.closest('tr');
      cancelInlineEdit(row);
    }
  });
}

function startInlineEdit(row){
  if (currentEditingRow && currentEditingRow !== row) cancelInlineEdit(currentEditingRow);
  currentEditingRow = row;
  row.classList.add('editing-row');

  const panel = row.closest('.tab-panel');
  const orgTypeName = panel?.dataset.type;

  const nameCell = row.querySelector('td[data-label="Name"]');
  const parentCell = row.querySelector('td[data-label="Parent"]');
  const statusCell = row.querySelector('td[data-label="Status"]');
  const actionsCell = row.querySelector('td[data-label="Actions"]');

  const originalName = nameCell.textContent.trim();
  const originalParent = parentCell ? parentCell.textContent.trim() : null;
  const originalStatus = statusCell.querySelector('.status-badge').classList.contains('status-active');

  row.dataset.originalName = originalName;
  row.dataset.originalParent = originalParent || '';
  row.dataset.originalStatus = originalStatus;

  nameCell.innerHTML = `<input type="text" class="inline-edit-input" value="${escapeHtml(originalName)}">`;

  if (parentCell){
    let parentOptions = '<option value="">-- No Parent --</option>';
    const parentType = getParentTypeForOrgType(orgTypeName);
    if (parentType && orgsByType[parentType]){
      orgsByType[parentType].forEach(org=>{
        const selected = (org.name === originalParent && originalParent !== '-') ? 'selected' : '';
        parentOptions += `<option value="${org.id}" ${selected}>${escapeHtml(org.name)}</option>`;
      });
    }
    parentCell.innerHTML = `<select class="inline-edit-select">${parentOptions}</select>`;
  }

  statusCell.innerHTML = `
    <select class="inline-edit-select">
      <option value="true" ${originalStatus ? 'selected' : ''}>Active</option>
      <option value="false" ${!originalStatus ? 'selected' : ''}>Inactive</option>
    </select>
  `;

  actionsCell.innerHTML = `
    <button class="icon-btn btn-row-save" title="Save"><i class="fas fa-check"></i></button>
    <button class="icon-btn btn-row-cancel" title="Cancel"><i class="fas fa-times"></i></button>
  `;

  const firstInput = row.querySelector('.inline-edit-input');
  if (firstInput) firstInput.focus();
  row.addEventListener('keydown', inlineEditKeyHandler);
}

function inlineEditKeyHandler(e){
  if (!currentEditingRow) return;
  if (e.key === 'Enter'){ e.preventDefault(); saveInlineEdit(currentEditingRow); }
  if (e.key === 'Escape'){ e.preventDefault(); cancelInlineEdit(currentEditingRow); }
}

function saveInlineEdit(row){
  const id = row.dataset.id;
  const modelName = 'organization';

  const nameInput = row.querySelector('.inline-edit-input');
  const parentCell = row.querySelector('td[data-label="Parent"]');
  const parentSelect = parentCell ? parentCell.querySelector('.inline-edit-select') : null;
  const statusSelect = row.querySelector('td[data-label="Status"] .inline-edit-select');

  const newName = (nameInput?.value || '').trim();
  const newParent = parentSelect ? parentSelect.value : null;
  const newStatus = statusSelect?.value === 'true';

  if (!newName){ showToast('Name cannot be empty', 'error'); return; }

  const actionsCell = row.querySelector('td[data-label="Actions"]');
  actionsCell.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';

  const updateData = { name:newName, is_active:newStatus };
  if (parentSelect) updateData.parent = newParent || null;

  fetch(`/core-admin/settings/${modelName}/${id}/edit/`, {
    method:'POST',
    headers:{'Content-Type':'application/json','X-CSRFToken':getCsrfToken()},
    body: JSON.stringify(updateData)
  })
  .then(r=>r.json())
  .then(data=>{
    if (data.success){
      const parentName = data.parent || (newParent ? getOrgNameById(newParent) : null);
      finishInlineEdit(row, newName, newStatus, parentName);
      showToast('Updated successfully!','success');
    } else {
      throw new Error(data.error || 'Failed to update');
    }
  })
  .catch(err=>{ showToast(err.message,'error'); cancelInlineEdit(row); });
}

function cancelInlineEdit(row){
  const originalName = row.dataset.originalName;
  const originalParent = row.dataset.originalParent;
  const originalStatus = row.dataset.originalStatus === 'true';
  finishInlineEdit(row, originalName, originalStatus, originalParent === '' ? null : originalParent);
  delete row.dataset.originalName;
  delete row.dataset.originalParent;
  delete row.dataset.originalStatus;
  row.removeEventListener('keydown', inlineEditKeyHandler);
}

function finishInlineEdit(row, name, isActive, parentName=null){
  row.classList.remove('editing-row');
  currentEditingRow = null;

  const nameCell = row.querySelector('td[data-label="Name"]');
  const parentCell = row.querySelector('td[data-label="Parent"]');
  const statusCell = row.querySelector('td[data-label="Status"]');
  const actionsCell = row.querySelector('td[data-label="Actions"]');

  nameCell.textContent = name;
  if (parentCell) parentCell.textContent = (parentName && parentName !== '-') ? parentName : '-';

  statusCell.innerHTML = `<span class="status-badge ${isActive ? 'status-active' : 'status-inactive'}">${isActive ? 'Active' : 'Inactive'}</span>`;

  const isSuperuser = !!document.querySelector('a.icon-btn[title="Add Users"]');
  actionsCell.innerHTML = `
    <button class="icon-btn btn-edit" title="Edit Entry" aria-label="Edit Entry">
      <i class="fas fa-pen"></i>
    </button>
    ${isSuperuser ? `<a class="icon-btn" title="Add Users" aria-label="Add Users" href="/core-admin/org-users/${row.dataset.id}/">
      <i class="fas fa-user-plus"></i>
    </a>` : ``}
  `;

  if (isActive) row.classList.remove('inactive-row-display');
  else row.classList.add('inactive-row-display');
}

// ======= Add / Category forms =======
function initializeFormHandlers(){
  const categorySelect = document.getElementById('categorySelect');
  const parentOrgGroup = document.getElementById('parent-organization-group');
  const parentOrgSelect = document.getElementById('parentOrganizationSelect');
  const parentHint = document.getElementById('parentHint');

  function handleCategoryChange(){
    if (!categorySelect) return;
    const opt = categorySelect.options[categorySelect.selectedIndex];
    const canHaveParent = opt?.getAttribute('data-can-have-parent') === 'true';
    const parentType = opt?.getAttribute('data-parent-type');
    parentOrgGroup.style.display = canHaveParent ? 'block' : 'none';
    parentHint.textContent = canHaveParent && parentType ? `Parent must be a ${parentType}.` : '';
    if (canHaveParent && parentType && orgsByType[parentType]){
      parentOrgSelect.innerHTML = `<option value="" disabled selected>Select Parent</option>`;
      orgsByType[parentType].forEach(org=>{
        parentOrgSelect.innerHTML += `<option value="${org.id}">${escapeHtml(org.name)}</option>`;
      });
    } else {
      parentOrgSelect.innerHTML = `<option value="" disabled selected>Select Parent</option>`;
    }
  }

  if (categorySelect){
    categorySelect.addEventListener('change', handleCategoryChange);
    // preset to current selected category in controls
    const ctrlCat = document.getElementById('categoryFilter')?.value;
    if (ctrlCat) categorySelect.value = ctrlCat;
    setTimeout(handleCategoryChange, 50);
  }

  // Entry buttons
  document.getElementById('addEntryCancelBtn')?.addEventListener('click', (e)=>{
    e.preventDefault(); resetAddEntryForm(); hidePanel('add-form-container');
  });
  document.getElementById('addEntryConfirmBtn')?.addEventListener('click', (e)=>{
    e.preventDefault(); addNewEntry();
  });

  // Category buttons
  document.getElementById('addCategoryCancelBtn')?.addEventListener('click', (e)=>{
    e.preventDefault(); resetAddCategoryForm(); hidePanel('add-category-container');
  });
  const hasParentCategory = document.getElementById('hasParentCategory');
  hasParentCategory && (hasParentCategory.onchange = function(){
    document.getElementById('parentCategoryGroup').style.display = this.checked ? 'block' : 'none';
    if (!this.checked){ document.getElementById('parentCategorySelect').value = ""; }
  });
  document.getElementById('addCategoryConfirmBtn')?.addEventListener('click', (e)=>{
    e.preventDefault(); addNewCategory();
  });
}

// CRUD (same endpoints; unchanged logic)
function addNewEntry(){
  const categorySelect = document.getElementById('categorySelect');
  const parentOrgSelect = document.getElementById('parentOrganizationSelect');
  const nameInput = document.getElementById('newEntryName');

  const name = (nameInput?.value || '').trim();
  const opt = categorySelect?.options[categorySelect.selectedIndex];
  const category = opt?.value;
  const canHaveParent = opt?.getAttribute('data-can-have-parent') === 'true';

  let parent = null;
  if (canHaveParent){
    parent = parentOrgSelect?.value;
    if (!parent){ showToast("Please select the parent organization.", 'error'); return; }
  }
  if (!name){ showToast("Please enter a name.", 'error'); return; }

  const btn = document.getElementById("addEntryConfirmBtn");
  const original = btn.innerHTML; btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Adding…'; btn.disabled = true;

  const payload = { name, org_type:category }; if (parent) payload.parent = parent;

  fetch("/core-admin/settings/organization/add/",{
    method:"POST", headers:{"Content-Type":"application/json","X-CSRFToken":getCsrfToken()}, body:JSON.stringify(payload)
  })
  .then(r=>r.json())
  .then(data=>{
    if (data.success){ showToast('Entry added successfully!','success'); setTimeout(()=>window.location.reload(),800); }
    else throw new Error(data.error || 'Failed to add entry.');
  })
  .catch(err=> showToast(err.message,'error'))
  .finally(()=>{ btn.innerHTML = original; btn.disabled = false; });
}

function addNewCategory(){
  const name = (document.getElementById("newCategoryName")?.value || '').trim();
  const has = document.getElementById("hasParentCategory")?.checked;
  let parent = null;
  if (has){
    parent = document.getElementById("parentCategorySelect")?.value;
    if (!parent){ showToast("Please select a parent category.", 'error'); return; }
  }
  if (!name){ showToast("Enter a category name.", 'error'); return; }

  const btn = document.getElementById("addCategoryConfirmBtn");
  const original = btn.innerHTML; btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Adding…'; btn.disabled = true;

  const payload = { name }; if (parent) payload.parent = parent;

  fetch("/core-admin/settings/organization_type/add/",{
    method:"POST", headers:{"Content-Type":"application/json","X-CSRFToken":getCsrfToken()}, body:JSON.stringify(payload)
  })
  .then(r=>r.json())
  .then(data=>{
    if (data.success){ showToast('Category added successfully!','success'); setTimeout(()=>window.location.reload(),800); }
    else throw new Error(data.error || "Failed to add category.");
  })
  .catch(err=> showToast(err.message,'error'))
  .finally(()=>{ btn.innerHTML = original; btn.disabled = false; });
}

// ======= Utilities =======
function showPanel(id){ const el=document.getElementById(id); if(el) el.style.display='grid'; }
function hidePanel(id){ const el=document.getElementById(id); if(el) el.style.display='none'; }
function resetAddEntryForm(){ const n=document.getElementById('newEntryName'); if(n) n.value=''; const p=document.getElementById('parentOrganizationSelect'); if(p) p.value=''; }
function resetAddCategoryForm(){ const n=document.getElementById('newCategoryName'); if(n) n.value=''; const h=document.getElementById('hasParentCategory'); if(h) h.checked=false; const g=document.getElementById('parentCategoryGroup'); if(g) g.style.display='none'; const s=document.getElementById('parentCategorySelect'); if(s) s.value=''; }

function getParentTypeForOrgType(orgTypeName){
  const select = document.getElementById("categorySelect");
  if (select){
    for (let option of select.options){
      if (option.value.toLowerCase() === (orgTypeName||'').toLowerCase()){
        const pt = option.getAttribute('data-parent-type');
        return pt ? pt.toLowerCase() : null;
      }
    }
  }
  const map = { department:'school', club:'department', cell:'department', committee:'department', association:'department', center:'school' };
  return map[(orgTypeName||'').toLowerCase()];
}

function getOrgNameById(id){
  for (const t in orgsByType){
    const org = (orgsByType[t]||[]).find(o => String(o.id) === String(id));
    if (org) return org.name;
  }
  return null;
}

function getCsrfToken(){
  const token = document.querySelector('[name=csrfmiddlewaretoken]'); if (token) return token.value;
  for (let c of document.cookie.split(';')){ const [n,v]=c.trim().split('='); if (n==='csrftoken') return v; }
  const meta = document.querySelector('meta[name="csrf-token"]'); return meta ? meta.getAttribute('content') : '';
}

function showToast(msg,type='info'){
  const el = document.getElementById('toast-notification') || createToastElement();
  el.textContent = msg; el.className = `toast toast-${type} show`;
  clearTimeout(showToast._t); showToast._t = setTimeout(()=> el.classList.remove('show'), 3000);
}
function createToastElement(){ const t=document.createElement('div'); t.id='toast-notification'; t.className='toast'; document.body.appendChild(t); return t; }
function escapeHtml(str){ return String(str).replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[m])); }

function wireShortcuts(){
  document.addEventListener('keydown',(e)=>{
    const isMac = navigator.platform.toUpperCase().includes('MAC');
    if ((isMac && e.metaKey && e.key.toLowerCase()==='k') || (!isMac && e.ctrlKey && e.key.toLowerCase()==='k')){
      e.preventDefault(); document.getElementById('universalSearch')?.focus();
    }
  });
}

function showSuccessToastIfNeeded(){
  const urlParams = new URLSearchParams(window.location.search);
  if (urlParams.get('success')) showToast('Operation completed successfully!','success');
}
