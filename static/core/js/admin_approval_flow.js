// ======= Globals =======
let approvalSteps = [];
let draggedUser = null;
let draggedIdx = null;
let roleSuggestions = [];
let searchDebounceTimer = null;

// ======= Boot =======
document.addEventListener('DOMContentLoaded', () => {
  initializeApprovalFlow();
  wireShortcuts();
  showSuccessToastIfNeeded();
});

// ======= Initialization =======
function initializeApprovalFlow() {
  if (window.SELECTED_ORG_ID) {
    loadCurrentFlow();
    loadRoles();
    
    const facultyToggle = document.getElementById('facultyFirstToggle');
    if (facultyToggle) facultyToggle.checked = window.REQUIRE_FACULTY_FIRST;
  }
  initModalHandlers();
}

function initModalHandlers() {
  // Close when clicking overlay
  document.querySelectorAll('.modal-overlay').forEach(el => {
    el.addEventListener('click', e => {
      if (e.target === el) closeModal(el.id);
    });
  });
  
  // ESC to close
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') closeAllModals();
  });
}

// ======= Modal controls =======
function openModal(id) {
  const modal = document.getElementById(id);
  if (modal) {
    modal.classList.add('show');
    document.body.style.overflow = 'hidden';
  }
}

function closeModal(id) {
  const modal = document.getElementById(id);
  if (modal) {
    modal.classList.remove('show');
    document.body.style.overflow = '';
  }
}

function closeAllModals() {
  document.querySelectorAll('.modal-overlay.show')
    .forEach(el => el.classList.remove('show'));
  document.body.style.overflow = '';
}

// ======= Toast notifications =======
let toastTimeout;
function showToast(message, type = 'success') {
  // Try both toast IDs for compatibility
  const toast = document.getElementById('toast') || document.getElementById('toast-notification');
  if (!toast) {
    console.log('Toast:', message); // Fallback to console
    return;
  }
  
  const msgEl = toast.querySelector('#toastMessage') || toast.querySelector('span');
  if (msgEl) {
    msgEl.textContent = message;
  }
  
  toast.className = `toast show toast-${type}`;
  clearTimeout(toastTimeout);
  toastTimeout = setTimeout(() => toast.classList.remove('show'), 3000);
}

// ======= Utility functions =======
function getCsrfToken() {
  return window.CSRF_TOKEN || '';
}

function debounce(fn, delay) {
  let timeout;
  return function(...args) {
    clearTimeout(timeout);
    timeout = setTimeout(() => fn.apply(this, args), delay);
  };
}

function escapeHtml(str) {
  return String(str).replace(/[&<>"']/g, m => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;'
  }[m]));
}

// ======= API helpers =======
async function fetchJson(url, opts = {}) {
  const headers = {
    'X-CSRFToken': getCsrfToken(),
    'Content-Type': 'application/json',
    ...(opts.headers || {})
  };
  
  const res = await fetch(url, {
    credentials: 'same-origin',
    ...opts,
    headers
  });
  
  return res.json();
}

// ======= Approval Flow Editor =======
function openApprovalFlowEditor() {
  openModal('approvalFlowEditorModal');
  loadApprovalFlow();
  loadOrgUsers();
  loadRoles();
}

async function loadCurrentFlow() {
  const tableBody = document.getElementById('currentFlowTableBody');
  if (!tableBody || !window.SELECTED_ORG_ID) return;
  
  try {
    const resp = await fetch(`/core-admin/approval-flow/${window.SELECTED_ORG_ID}/get/`);
    const data = await resp.json();
    
    if (data.success) {
      if (data.steps.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="4" class="text-center">No approval flow defined. Click "Edit Flow" to create one.</td></tr>';
      } else {
        tableBody.innerHTML = data.steps.map(step => `
          <tr>
            <td><span class="step-number">${step.step_order}</span></td>
            <td><span class="role-display">${step.role_display || step.role_required}</span></td>
            <td>${step.user_name ? `
              <div class="user-info">
                <strong>${step.user_name}</strong>
                <span class="user-email">${step.user_email || ''}</span>
              </div>
            ` : '<span class="text-muted"><i class="fas fa-user-slash"></i> Unassigned</span>'}</td>
            <td>
              <span class="status-badge ${step.optional ? 'status-inactive' : 'status-active'}">
                ${step.optional ? 'Optional' : 'Required'}
              </span>
            </td>
          </tr>
        `).join('');
      }
      
      // Update faculty toggle if provided
      if (typeof data.require_faculty_incharge_first !== 'undefined') {
        const toggle = document.getElementById('facultyFirstToggle');
        if (toggle) toggle.checked = data.require_faculty_incharge_first;
        window.REQUIRE_FACULTY_FIRST = data.require_faculty_incharge_first;
      }
    }
  } catch (e) {
    console.error('Failed to load current flow:', e);
  }
}

async function loadApprovalFlow() {
  const orgId = window.SELECTED_ORG_ID;
  approvalSteps = [];
  const stepsDiv = document.getElementById('approvalFlowSteps');
  
  if (!orgId || !stepsDiv) return;
  
  stepsDiv.innerHTML = '<div class="empty-msg">Loading flow…</div>';
  
  try {
    const resp = await fetch(`/core-admin/approval-flow/${orgId}/get/`);
    const data = await resp.json();
    
    if (data.success && data.steps.length > 0) {
      approvalSteps = data.steps.map(s => ({
        role: s.role_required,
        user: s.user_id ? {id: s.user_id, name: s.user_name || `User: ${s.user_id}`} : null,
        optional: s.optional
      }));
      renderApprovalSteps();
    } else {
      approvalSteps = [];
      renderApprovalSteps();
    }
    
    if (typeof data.require_faculty_incharge_first !== 'undefined') {
      window.REQUIRE_FACULTY_FIRST = data.require_faculty_incharge_first;
      const toggle = document.getElementById('facultyFirstToggle');
      if (toggle) toggle.checked = data.require_faculty_incharge_first;
    }
  } catch (e) {
    stepsDiv.innerHTML = '<div class="error-msg">Failed to load steps.</div>';
  }
}

function addApprovalStep() {
  approvalSteps.push({ role: '', user: null, optional: false });
  renderApprovalSteps();
}

// ======= Simplified Step Rendering (No TomSelect) =======
function renderApprovalSteps() {
  const stepsDiv = document.getElementById('approvalFlowSteps');
  if (!stepsDiv) return;
  
  if (approvalSteps.length === 0) {
    stepsDiv.innerHTML = '<div class="empty-msg"><i class="fas fa-plus-circle"></i> No steps added. Click "+ Add Step" to begin.</div>';
    return;
  }
  
  stepsDiv.innerHTML = approvalSteps.map((step, i) => `
    <div class="step-block" draggable="true" data-idx="${i}" 
         ondragstart="startDrag(event, ${i})" 
         ondragover="allowDrop(event)" 
         ondrop="dropStep(event, ${i})">
      <span class="drag-handle" title="Drag to reorder">
        <i class="fas fa-grip-vertical"></i>
      </span>
      <span class="step-number">${i + 1}</span>
      <input class="role-input" list="roleSuggestions" type="text" 
             placeholder="Role (e.g. faculty)" 
             value="${escapeHtml(step.role || '')}"
             oninput="updateStepRole(${i}, this.value);">
      <div class="user-display-wrapper">
        <div class="user-display" onclick="clearUser(${i})" title="Click to clear user">
          ${step.user ? escapeHtml(step.user.name) : 'Click to assign user'}
        </div>
      </div>
      <label class="optional-toggle">
        <input type="checkbox" ${step.optional ? 'checked' : ''} 
               onchange="toggleOptional(${i}, this.checked)"> 
        Optional
      </label>
      <button onclick="removeStep(${i})" class="btn btn-danger btn-sm" title="Remove step">
        <i class="fas fa-trash"></i>
      </button>
    </div>
  `).join('');
}

function updateStepRole(idx, value) {
  if (approvalSteps[idx]) {
    approvalSteps[idx].role = value;
  }
}

function toggleOptional(idx, val) {
  if (approvalSteps[idx]) {
    approvalSteps[idx].optional = val;
  }
}

function clearUser(idx) {
  if (approvalSteps[idx]) {
    approvalSteps[idx].user = null;
    renderApprovalSteps();
  }
}

function selectUserForStep(idx, userId, userName) {
  if (approvalSteps[idx]) {
    approvalSteps[idx].user = { id: userId, name: userName };
    renderApprovalSteps();
  }
}

function removeStep(idx) {
  approvalSteps.splice(idx, 1);
  renderApprovalSteps();
}

// ======= Drag and drop for steps =======
function startDrag(e, idx) {
  draggedIdx = idx;
  e.dataTransfer.effectAllowed = 'move';
  e.target.classList.add('dragging');
}

function allowDrop(e) {
  e.preventDefault();
}

function dropStep(e, idx) {
  e.preventDefault();
  if (draggedIdx === null || draggedIdx === idx) return;
  
  const step = approvalSteps.splice(draggedIdx, 1)[0];
  approvalSteps.splice(idx, 0, step);
  draggedIdx = null;
  
  document.querySelectorAll('.step-block').forEach(block => {
    block.classList.remove('dragging');
  });
  
  renderApprovalSteps();
}

// ======= User management =======
const debouncedLoadUsers = debounce(loadOrgUsers, 300);

async function loadOrgUsers(q = '') {
  const list = document.getElementById('orgUserList');
  if (!list) return;
  
  list.innerHTML = '<div class="empty-msg">Loading...</div>';
  
  const params = new URLSearchParams({ 
    q, 
    org_type_id: window.SELECTED_ORG_TYPE_ID 
  });
  
  try {
    const resp = await fetch(`/core-admin/api/org-users/${window.SELECTED_ORG_ID}/?${params}`);
    const data = await resp.json();
    
    if (data.success) {
      if (data.users && data.users.length > 0) {
        list.innerHTML = data.users.map(u => `
          <div class="user-item" 
               draggable="true" 
               ondragstart="startUserDrag(${u.id}, '${escapeHtml(u.name)}', '${escapeHtml(u.role)}')"
               onclick="selectUserForStep(getCurrentStepIndex(), ${u.id}, '${escapeHtml(u.name)}')"
               title="Drag to step or click to assign">
            <strong>${escapeHtml(u.name)}</strong>
            <span class="role">${escapeHtml(u.role)}</span>
          </div>
        `).join('');
      } else {
        list.innerHTML = '<div class="empty-msg">No users found</div>';
      }
    } else {
      list.innerHTML = '<div class="error-msg">Failed to load users</div>';
    }
  } catch (e) {
    list.innerHTML = '<div class="error-msg">Error loading users</div>';
  }
}

function getCurrentStepIndex() {
  // Simple helper to get the last step index for click assignment
  return Math.max(0, approvalSteps.length - 1);
}

function startUserDrag(id, name, role) {
  draggedUser = { id, name, role };
}

function dropOnSteps(e) {
  e.preventDefault();
  if (!draggedUser) return;
  
  // Add dragged user as new step
  approvalSteps.push({ 
    role: draggedUser.role.toLowerCase(), 
    user: { id: draggedUser.id, name: draggedUser.name },
    optional: false
  });
  
  renderApprovalSteps();
  draggedUser = null;
  
  // Visual feedback
  const stepsContainer = document.getElementById('approvalFlowSteps');
  if (stepsContainer) {
    stepsContainer.classList.remove('drag-over');
  }
}

// ======= Role suggestions =======
async function loadRoles() {
  const orgId = window.SELECTED_ORG_ID;
  const typeId = window.SELECTED_ORG_TYPE_ID;
  
  if (!orgId && !typeId) {
    document.getElementById('roleSuggestions').innerHTML = '';
    return;
  }

  let url = '';
  if (orgId) {
    url = `/core-admin/api/organization/${orgId}/roles/`;
  } else {
    url = `/core-admin/api/org-type/${typeId}/roles/`;
  }

  try {
    const resp = await fetch(url);
    const data = await resp.json();
    
    if (data.success) {
      roleSuggestions = data.roles || [];
      const list = document.getElementById('roleSuggestions');
      if (list) {
        list.innerHTML = roleSuggestions
          .map(r => `<option value="${escapeHtml(r.name)}"></option>`)
          .join('');
      }
    }
  } catch (e) {
    console.error('Failed to load role suggestions', e);
  }
}

// ======= Real-time visualization updates =======
function updateFlowVisualization(steps, facultyFirst = false) {
  const flowDiagram = document.getElementById('flowVisualization');
  if (!flowDiagram) return;
  
  let html = '';
  
  // Faculty first step
  if (facultyFirst) {
    html += `
      <div class="flow-step flow-step-faculty">
        <i class="fas fa-user-tie"></i>
        <div class="step-content">
          <strong>Faculty</strong>
          <small>In-Charge</small>
        </div>
      </div>
    `;
  }
  
  // Regular steps
  steps.forEach((step, index) => {
    const stepType = step.optional ? 'flow-step-optional' : 'flow-step-required';
    const stepRole = step.role || 'User';
    const stepUser = step.user ? step.user.name : 'Unassigned';
    
    // Choose appropriate icon based on role
    let icon = 'fas fa-user';
    const roleLower = stepRole.toLowerCase();
    if (roleLower.includes('student')) icon = 'fas fa-user-graduate';
    else if (roleLower.includes('faculty')) icon = 'fas fa-chalkboard-teacher';
    else if (roleLower.includes('hod')) icon = 'fas fa-user-tie';
    else if (roleLower.includes('principal')) icon = 'fas fa-crown';
    
    html += `
      <div class="flow-step ${stepType}">
        <span class="step-badge">${index + 1}</span>
        <i class="${icon}"></i>
        <div class="step-content">
          <strong>${stepRole.length > 8 ? stepRole.substring(0,8) : stepRole}</strong>
          <small>${stepUser.length > 10 ? stepUser.substring(0,10) : stepUser}</small>
        </div>
        ${step.optional ? '<i class="fas fa-question-circle optional-icon" title="Optional Step"></i>' : ''}
      </div>
    `;
  });
  
  // End step
  if (steps.length > 0) {
    html += `
      <div class="flow-step flow-step-end">
        <i class="fas fa-check-circle"></i>
        <div class="step-content">
          <strong>Approved</strong>
          <small>Final</small>
        </div>
      </div>
    `;
  }
  
  flowDiagram.innerHTML = html;
}

function updateCurrentFlowTable(steps) {
  const tableBody = document.querySelector('.data-table tbody');
  if (!tableBody) return;
  
  if (steps.length === 0) {
    tableBody.innerHTML = '<tr><td colspan="4" class="text-center">No approval flow configured</td></tr>';
    return;
  }
  
  const html = steps.map((step, index) => `
    <tr>
      <td>
        <span class="step-number">${index + 1}</span>
      </td>
      <td>
        <span class="role-display">${step.role ? step.role.charAt(0).toUpperCase() + step.role.slice(1) : 'Unassigned'}</span>
      </td>
      <td>
        ${step.user ? `
          <div class="user-info">
            <strong>${step.user.name}</strong>
            <span class="user-email">${step.user.email || ''}</span>
          </div>
        ` : '<span class="text-muted"><i class="fas fa-user-slash"></i> Unassigned</span>'}
      </td>
      <td>
        <span class="status-badge ${step.optional ? 'status-inactive' : 'status-active'}">
          ${step.optional ? 'Optional' : 'Required'}
        </span>
      </td>
    </tr>
  `).join('');
  
  tableBody.innerHTML = html;
}

function updateFlowSummary(steps) {
  const summary = document.querySelector('.flow-summary');
  if (summary) {
    summary.textContent = `${steps.length} step${steps.length !== 1 ? 's' : ''} configured`;
  }
}

function updateFacultyFirstBadge(enabled) {
  const badge = document.querySelector('.filters-left .status-badge');
  if (badge) {
    badge.className = `status-badge ${enabled ? 'status-active' : 'status-inactive'}`;
    badge.textContent = enabled ? 'Enabled' : 'Disabled';
  }
}

// ======= Save and delete operations =======
async function saveApprovalFlow() {
  const orgId = window.SELECTED_ORG_ID;
  if (!orgId) {
    showToast('No organization selected', 'error');
    return;
  }

  // Validate steps
  for (let i = 0; i < approvalSteps.length; i++) {
    const step = approvalSteps[i];
    if (!step.role.trim()) {
      showToast(`Step ${i + 1} is missing a role`, 'error');
      return;
    }
  }

  // Map frontend data to backend format
  const payloadSteps = approvalSteps.map(s => ({
    role_required: s.role,
    user_id: s.user ? s.user.id : null,
    optional: s.optional
  }));
  
  const requireFic = document.getElementById('facultyFirstToggle');
  const requireFlag = requireFic ? requireFic.checked : false;

  try {
    const data = await fetchJson(`/core-admin/approval-flow/${orgId}/save/`, {
      method: 'POST',
      body: JSON.stringify({ 
        steps: payloadSteps, 
        require_faculty_incharge_first: requireFlag 
      })
    });

    if (data.success) {
      showToast('Approval flow saved successfully!', 'success');
      closeModal('approvalFlowEditorModal');
      
      // Real-time updates without page refresh
      updateFlowVisualization(approvalSteps, requireFlag);
      updateCurrentFlowTable(approvalSteps);
      updateFlowSummary(approvalSteps);
      updateFacultyFirstBadge(requireFlag);
      
      // Update page elements
      const emptyState = document.querySelector('.empty-state');
      const flowContent = document.querySelector('.flow-status-header');
      
      if (approvalSteps.length > 0 && emptyState) {
        emptyState.style.display = 'none';
        if (flowContent) flowContent.style.display = 'flex';
      }
      
    } else {
      showToast(data.error || 'Failed to save flow', 'error');
    }
  } catch (e) {
    console.error('Save error:', e);
    showToast('Error saving flow', 'error');
  }
}

async function deleteApprovalFlow() {
  const orgId = window.SELECTED_ORG_ID;
  if (!orgId) return;
  
  if (!confirm('Delete the entire approval flow for this organization? This action cannot be undone.')) {
    return;
  }

  try {
    const data = await fetchJson(`/core-admin/approval-flow/${orgId}/delete/`, {
      method: 'POST'
    });

    if (data.success) {
      approvalSteps = [];
      renderApprovalSteps();
      showToast('Approval flow deleted successfully', 'success');
      closeModal('approvalFlowEditorModal');
      loadCurrentFlow();
    } else {
      showToast(data.error || 'Failed to delete flow', 'error');
    }
  } catch (e) {
    console.error('Delete error:', e);
    showToast('Error deleting flow', 'error');
  }
}

// ======= Utility functions =======
function wireShortcuts() {
  document.addEventListener('keydown', (e) => {
    const isMac = navigator.platform.toUpperCase().includes('MAC');
    if ((isMac && e.metaKey && e.key.toLowerCase() === 'k') || 
        (!isMac && e.ctrlKey && e.key.toLowerCase() === 'k')) {
      e.preventDefault();
      const searchInput = document.getElementById('userSearchInput');
      if (searchInput) searchInput.focus();
    }
  });
}

function showSuccessToastIfNeeded() {
  const urlParams = new URLSearchParams(window.location.search);
  if (urlParams.get('success')) {
    showToast('Operation completed successfully!', 'success');
  }
}

// ======= Drag over effects =======
document.addEventListener('dragover', (e) => {
  const stepsContainer = document.getElementById('approvalFlowSteps');
  if (stepsContainer && stepsContainer.contains(e.target)) {
    e.preventDefault();
    stepsContainer.classList.add('drag-over');
  }
});

document.addEventListener('dragleave', (e) => {
  const stepsContainer = document.getElementById('approvalFlowSteps');
  if (stepsContainer && !stepsContainer.contains(e.relatedTarget)) {
    stepsContainer.classList.remove('drag-over');
  }
});

document.addEventListener('drop', (e) => {
  const stepsContainer = document.getElementById('approvalFlowSteps');
  if (stepsContainer) {
    stepsContainer.classList.remove('drag-over');
  }
});

// ======= Global exports =======
window.openApprovalFlowEditor = openApprovalFlowEditor;
window.closeModal = closeModal;
window.loadRoles = loadRoles;
window.addApprovalStep = addApprovalStep;
window.updateStepRole = updateStepRole;
window.toggleOptional = toggleOptional;
window.removeStep = removeStep;
window.clearUser = clearUser;
window.startDrag = startDrag;
window.allowDrop = allowDrop;
window.dropStep = dropStep;
window.startUserDrag = startUserDrag;
window.dropOnSteps = dropOnSteps;
window.saveApprovalFlow = saveApprovalFlow;
window.deleteApprovalFlow = deleteApprovalFlow;
window.loadOrgUsers = loadOrgUsers;
window.selectUserForStep = selectUserForStep;
window.showToast = showToast;
window.updateFlowVisualization = updateFlowVisualization;
window.updateCurrentFlowTable = updateCurrentFlowTable;
window.updateFlowSummary = updateFlowSummary;
window.updateFacultyFirstBadge = updateFacultyFirstBadge;