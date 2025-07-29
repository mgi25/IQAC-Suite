// core/static/core/js/admin_approval_flow.js
(function() {
  // ———————————————————————————————————————————————
  // Configuration
  // ———————————————————————————————————————————————
  const CSRF_TOKEN = window.CSRF_TOKEN || '';

  // ———————————————————————————————————————————————
  // Utility: fetch wrapper with CSRF
  // ———————————————————————————————————————————————
  async function fetchJson(url, opts = {}) {
    const headers = {
      'X-CSRFToken': CSRF_TOKEN,
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

  // ———————————————————————————————————————————————
  // Debounce helper
  // ———————————————————————————————————————————————
  function debounce(fn, delay) {
    let timeout;
    return function(...args) {
      clearTimeout(timeout);
      timeout = setTimeout(() => fn.apply(this, args), delay);
    };
  }

  // ———————————————————————————————————————————————
  // Modal controls
  // ———————————————————————————————————————————————
  function openModal(id) {
    document.getElementById(id).classList.add('show');
    document.body.style.overflow = 'hidden';
  }
  function closeModal(id) {
    document.getElementById(id).classList.remove('show');
    document.body.style.overflow = '';
  }
  function closeAllModals() {
    document.querySelectorAll('.modal-overlay.show')
      .forEach(el => el.classList.remove('show'));
    document.body.style.overflow = '';
  }

  // ———————————————————————————————————————————————
  // Toast notification
  // ———————————————————————————————————————————————
  let toastTimeout;
  function showToast(message, type = 'success') {
    const toast = document.getElementById('toast');
    const msgEl = toast.querySelector('#toastMessage');
    toast.className = `toast show ${type}`;
    msgEl.textContent = message;
    clearTimeout(toastTimeout);
    toastTimeout = setTimeout(() => toast.classList.remove('show'), 3000);
    }

// ADD THIS:
window.showToast = showToast;


  // ———————————————————————————————————————————————
  // Loading placeholder
  // ———————————————————————————————————————————————
  function showLoading() {
    const list = document.getElementById('eventList');
    list.innerHTML = `<div class="loading">
      <div class="spinner"></div>Loading events...
    </div>`;
  }
  function hideLoading() {
    // New content will replace
  }

  // ———————————————————————————————————————————————
  // Filters
  // ———————————————————————————————————————————————
  function applyFilters() {
    const term = document.getElementById('searchInput').value.toLowerCase();
    const orgType = document.getElementById('orgTypeFilter').value;
    const status = document.getElementById('statusFilter').value;

    document.querySelectorAll('.event-card').forEach(card => {
      const title = card.querySelector('.event-title').textContent.toLowerCase();
      const meta = card.querySelector('.event-meta').textContent.toLowerCase();
      const cardStatus = card.querySelector('.event-status').className;
      const cardType = card.dataset.orgType || '';

      let visible = true;
      if (term && !title.includes(term) && !meta.includes(term)) visible = false;
      if (status && !cardStatus.includes(`status-${status}`)) visible = false;
      if (orgType && cardType !== orgType) visible = false;

      card.style.display = visible ? '' : 'none';
    });
  }

  // ———————————————————————————————————————————————
  // Fetch & display events, details & actions
  // ———————————————————————————————————————————————
  async function refreshEvents() {
    showLoading();
    try {
      const data = await fetchJson('/api/events/refresh/', { method: 'GET' });
      if (data.success) window.location.reload();
      else showToast('Failed to refresh events', 'error');
    } catch {
      showToast('Error refreshing events', 'error');
    }
  }

  async function openEventDetails(id) {
    try {
      const data = await fetchJson(`/api/events/${id}/details/`, { method: 'GET' });
      if (data.success) {
        document.getElementById('eventDetailsContent').innerHTML = data.html;
        openModal('eventDetailsModal');
      } else {
        showToast('Could not load details', 'error');
      }
    } catch {
      showToast('Error loading details', 'error');
    }
  }

  let currentEventId = null;
  async function redirectApprovalFlow(id) {
    currentEventId = id;
    try {
      const data = await fetchJson(`/api/events/${id}/current-approver/`, { method: 'GET' });
      if (data.success) {
        document.getElementById('currentApprover').value = data.current_approver;
        openModal('redirectFlowModal');
      } else {
        showToast('Could not load approver', 'error');
      }
    } catch {
      showToast('Error loading approver', 'error');
    }
  }

  async function submitRedirectFlow() {
    const newApprover = document.getElementById('newApprover').value;
    const reason = document.getElementById('redirectReason').value;
    const notify = document.getElementById('notifyUsers').checked;

    if (!newApprover || !reason) {
      showToast('Fill all fields', 'error');
      return;
    }
    try {
      const data = await fetchJson(`/api/events/${currentEventId}/redirect-flow/`, {
        method: 'POST',
        body: JSON.stringify({ new_approver: newApprover, reason, notify_users: notify })
      });
      if (data.success) {
        showToast('Flow redirected');
        closeModal('redirectFlowModal');
        refreshEvents();
      } else {
        showToast(data.message || 'Failed to redirect', 'error');
      }
    } catch {
      showToast('Error redirecting', 'error');
    }
  }

  function modifyApprovalStages() {
    showToast('Feature coming soon', 'warning');
  }

  async function escalateEvent(id) {
    if (!confirm('Escalate this event?')) return;
    try {
      const data = await fetchJson(`/api/events/${id}/escalate/`, { method: 'POST' });
      if (data.success) {
        showToast('Event escalated');
        refreshEvents();
      } else {
        showToast(data.message || 'Failed to escalate', 'error');
      }
    } catch {
      showToast('Error escalating', 'error');
    }
  }

  // ———————————————————————————————————————————————
  // Bulk actions
  // ———————————————————————————————————————————————
  async function openBulkActionsModal() {
    try {
      const data = await fetchJson('/api/events/bulk-list/', { method: 'GET' });
      if (data.success) {
        const list = document.getElementById('bulkEventsList');
        list.innerHTML = data.events.map(ev => `
          <label>
            <input type="checkbox" name="bulkEvents" value="${ev.id}">
            ${ev.title} — ${ev.organization} (${ev.status})
          </label>
        `).join('');
        openModal('bulkActionsModal');
      } else {
        showToast('Could not load bulk list', 'error');
      }
    } catch {
      showToast('Error loading bulk list', 'error');
    }
  }

  async function submitBulkActions() {
    const selected = Array.from(document.querySelectorAll('input[name="bulkEvents"]:checked'))
      .map(cb => cb.value);
    const action = document.getElementById('bulkAction').value;
    const comments = document.getElementById('bulkComments').value;

    if (!selected.length || !action) {
      showToast('Select events & action', 'error');
      return;
    }
    try {
      const data = await fetchJson('/api/events/bulk-actions/', {
        method: 'POST',
        body: JSON.stringify({ events: selected, action, comments })
      });
      if (data.success) {
        showToast(`Applied to ${selected.length} events`);
        closeModal('bulkActionsModal');
        refreshEvents();
      } else {
        showToast(data.message || 'Bulk action failed', 'error');
      }
    } catch {
      showToast('Error applying bulk action', 'error');
    }
  }

  // ———————————————————————————————————————————————
  // User management & stubs
  // ———————————————————————————————————————————————
  function openUserManagementModal() {
    openModal('userManagementModal');
  }
  function openAddUserModal() {
    document.getElementById('userManagementForm').reset();
    openModal('userManagementModal');
  }
  async function submitUserManagement() {
    const form = document.getElementById('userManagementForm');
    const dataObj = Object.fromEntries(new FormData(form).entries());
    dataObj.permissions = Array.from(form.permissions)
      .filter(ch => ch.checked).map(ch => ch.value);

    try {
      const data = await fetchJson('/api/users/manage/', {
        method: 'POST',
        body: JSON.stringify(dataObj)
      });
      if (data.success) {
        showToast('User saved');
        closeModal('userManagementModal');
        window.location.reload();
      } else {
        showToast(data.message || 'Failed to save user', 'error');
      }
    } catch {
      showToast('Error saving user', 'error');
    }
  }
  async function editUser(id) {
    try {
      const data = await fetchJson(`/api/users/${id}/details/`, { method: 'GET' });
      if (data.success) {
        const u = data.user;
        document.getElementById('userName').value = u.name;
        document.getElementById('userEmail').value = u.email;
        document.getElementById('userRole').value = u.role;
        document.getElementById('userOrganization').value = u.organization;
        u.permissions.forEach(pid => {
          const cb = document.querySelector(`input[name="permissions"][value="${pid}"]`);
          if (cb) cb.checked = true;
        });
        openModal('userManagementModal');
      } else {
        showToast('Could not load user', 'error');
      }
    } catch {
      showToast('Error loading user', 'error');
    }
  }
  function managePermissions() {
    showToast('Feature coming soon', 'warning');
  }
  function openBulkApprovalModal() {
    showToast('Feature coming soon', 'warning');
  }
  function openSystemSettingsModal() {
    showToast('Feature coming soon', 'warning');
  }
  function generateReport() {
    showToast('Feature coming soon', 'warning');
  }

  // ———————————————————————————————————————————————
  // Recent activity stub
  // ———————————————————————————————————————————————
  function loadRecentActivity() {
    // populated server-side
  }

  // ———————————————————————————————————————————————
  // Global event listeners
  // ———————————————————————————————————————————————
  function setupGlobalListeners() {
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

  // ———————————————————————————————————————————————
  // Initialization
  // ———————————————————————————————————————————————
  document.addEventListener('DOMContentLoaded', () => {
    console.log("✅ DOM ready, script loaded");
    // Filters
    document.getElementById('searchInput')
      .addEventListener('input', debounce(applyFilters, 300));
    document.getElementById('orgTypeFilter')
      .addEventListener('change', applyFilters);
    document.getElementById('statusFilter')
      .addEventListener('change', applyFilters);

    setupGlobalListeners();
    loadRecentActivity();
  });

  // ———————————————————————————————————————————————
  // Expose core functions to inline onclicks
  // ———————————————————————————————————————————————
  window.applyFilters = applyFilters;
  window.refreshEvents = refreshEvents;
  window.openEventDetails = openEventDetails;
  window.redirectApprovalFlow = redirectApprovalFlow;
  window.submitRedirectFlow = submitRedirectFlow;
  window.modifyApprovalStages = modifyApprovalStages;
  window.escalateEvent = escalateEvent;
  window.openBulkActionsModal = openBulkActionsModal;
  window.submitBulkActions = submitBulkActions;
  window.openUserManagementModal = openUserManagementModal;
  window.openAddUserModal = openAddUserModal;
  window.submitUserManagement = submitUserManagement;
  window.editUser = editUser;
  window.managePermissions = managePermissions;
  window.openBulkApprovalModal = openBulkApprovalModal;
  window.openSystemSettingsModal = openSystemSettingsModal;
  window.generateReport = generateReport;

  // ———————————————————————————————————————————————
  // Approval flow editor
  // ———————————————————————————————————————————————
  let draggedUser = null;

  function openApprovalFlowEditor() {
    openModal('approvalFlowEditorModal');
    loadApprovalFlow();
    loadOrgUsers();
    loadRoles();
  }
window.loadApprovalFlow = async function() {
  const orgId = window.SELECTED_ORG_ID;
  approvalSteps = [];
  const stepsDiv = document.getElementById('approvalFlowSteps');
  if (!orgId) {
    stepsDiv.innerHTML = '';
    return;
  }
  stepsDiv.innerHTML = '<div style="padding:1rem 0;">Loading flow…</div>';
  try {
    const resp = await fetch(`/core-admin/approval-flow/${orgId}/get/`);
    const data = await resp.json();
    if (data.success && data.steps.length > 0) {
      approvalSteps = data.steps.map(s => ({
        role: s.role_required,
        user: s.user_id ? {id: s.user_id, name: s.user_name || `User: ${s.user_id}`} : null
      }));
      renderApprovalSteps();
    } else {
      approvalSteps = [];
      renderApprovalSteps();
    }
  } catch (e) {
    stepsDiv.innerHTML = '<div class="error-msg">Failed to load steps.</div>';
  }
}

let approvalSteps = [];
let draggedIdx = null;
let roleSuggestions = [];

async function loadRoles() {
  const typeSel = document.getElementById('approvalCategorySelect');
  const orgSel = document.getElementById('approvalFlowOrgSelect');
  const typeId = typeSel ? typeSel.value : null;
  const orgId = orgSel ? orgSel.value : window.SELECTED_ORG_ID;

  if (!typeId && !orgId) {
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
          .map(r => `<option value="${r.name}"></option>`)
          .join('');
      }
    }
  } catch (e) {
    console.error('Failed to load role suggestions', e);
  }
}

window.addApprovalStep = function() {
  const stepsDiv = document.getElementById('approvalFlowSteps');
  const idx = approvalSteps.length + 1;
  approvalSteps.push({ role: '', user: null });
  renderApprovalSteps();
};

function renderApprovalSteps() {
  const stepsDiv = document.getElementById('approvalFlowSteps');
  if (approvalSteps.length === 0) {
    stepsDiv.innerHTML = '<div class="empty-msg">No steps added. Click "+ Add Step".</div>';
    return;
  }
  stepsDiv.innerHTML = approvalSteps.map((step, i) => `
    <div class="step-block" draggable="true" data-idx="${i}" ondragstart="startDrag(event, ${i})" ondragover="allowDrop(event)" ondrop="dropStep(event, ${i})">
      <span class="drag-handle"><i class="fa-solid fa-grip-vertical"></i></span>
      <span class="step-number">${i + 1}</span>
      <input class="role-input" list="roleSuggestions" type="text" placeholder="Role (e.g. faculty)" value="${step.role || ''}"
             oninput="updateStepRole(${i}, this.value); loadRoles();">
      <div>
        <input class="user-search-input" type="text" placeholder="Search user..."
               value="${step.user ? step.user.name : ''}" data-idx="${i}">
      </div>
      <button onclick="removeStep(${i})" class="btn btn-danger btn-sm">Delete</button>
    </div>
  `).join('');
  initUserSearchInputs();
}

function initUserSearchInputs() {
  document.querySelectorAll('.user-search-input').forEach(el => {
    if (el.dataset.tsInit) return;
    el.dataset.tsInit = '1';
    const idx = el.getAttribute('data-idx');
    new TomSelect(el, {
      valueField: 'id',
      labelField: 'text',
      searchField: 'text',
      create: false,
      load: function(query, callback) {
        const roleInput = document.querySelector(`.step-block[data-idx="${idx}"] .role-input`);
        const role = roleInput ? roleInput.value : '';
        const params = new URLSearchParams({
          q: query,
          role: role,
          org_id: window.SELECTED_ORG_ID,
          org_type_id: window.SELECTED_ORG_TYPE_ID
        });
        fetch(`/core-admin/api/search-users/?${params}`)
          .then(r => r.json())
          .then(data => {
            callback(
              (data.users || []).map(u => ({ id: u.id, text: `${u.name} (${u.email})` }))
            );
          })
          .catch(() => callback());
      },
      onChange: function(value) {
        const option = this.options[value];
        if (option) {
          selectUserForStep(parseInt(idx), value, option.text);
        }
      }
    });
  });
}


window.updateStepRole = function(idx, value) {
  approvalSteps[idx].role = value;
};

function searchUserForStep(idx, q) {
  if (!q) {
    document.getElementById(`user-search-results-${idx}`).innerHTML = '';
    return;
  }
  const role = document.querySelector(`.step-block[data-idx="${idx}"] .role-input`).value;
  const orgId = window.SELECTED_ORG_ID;
  const typeId = window.SELECTED_ORG_TYPE_ID;
  const params = new URLSearchParams({ q, role, org_id: orgId, org_type_id: typeId });
  fetch(`/core-admin/api/search-users/?${params}`)
    .then(r => r.json())
    .then(data => {
      const results = (data.users || []).map(u =>
        `<div class="user-search-option" onclick="selectUserForStep(${idx}, ${u.id}, '${u.name.replace("'", "\\'")}')">${u.name} (${u.email})</div>`
      ).join('');
      document.getElementById(`user-search-results-${idx}`).innerHTML = results || '<div class="user-search-option disabled">No users found</div>';
    });
}

const debouncedSearchUser = debounce(searchUserForStep, 300);

window.startDrag = function(e, idx) {
  draggedIdx = idx;
  e.dataTransfer.effectAllowed = 'move';
};

window.allowDrop = function(e) {
  e.preventDefault();
};

window.dropStep = function(e, idx) {
  e.preventDefault();
  if (draggedIdx === null || draggedIdx === idx) return;
  const step = approvalSteps.splice(draggedIdx, 1)[0];
  approvalSteps.splice(idx, 0, step);
  draggedIdx = null;
  renderApprovalSteps();
};



window.selectUserForStep = function(idx, userId, userName) {
  approvalSteps[idx].user = { id: userId, name: userName };
  renderApprovalSteps();
};

window.removeStep = function(idx) {
  approvalSteps.splice(idx, 1);
  renderApprovalSteps();
};
  window.saveApprovalFlow = function() {
    console.log("🟦 Save clicked");
  const orgId = window.SELECTED_ORG_ID;

  // Map your frontend data to the backend format!
  const payloadSteps = approvalSteps.map(s => ({
    role_required: s.role,
    user_id: s.user ? s.user.id : null
  }));

  fetch(`/core-admin/approval-flow/${orgId}/save/`, {
    method: "POST",
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF_TOKEN },
    credentials: 'same-origin',
    body: JSON.stringify({ steps: payloadSteps })
  })
  .then(r => r.json())
  .then(data => {
    if (data.success) {
      showToast('Approval flow saved!', 'success');
      closeModal('approvalFlowEditorModal');
      loadCurrentFlow();
    } else {
      alert("Failed to save flow");
    }
  }).catch(e => {
    alert("Error: " + e);
  });
};

window.deleteApprovalFlow = function() {
  console.log("🟥 Delete clicked");
  const orgId = window.SELECTED_ORG_ID;
  if (!orgId) return;
  if (!confirm('Delete entire approval flow for this organization?')) return;
  fetch(`/core-admin/approval-flow/${orgId}/delete/`, {
    method: 'POST',
    headers: { 'X-CSRFToken': CSRF_TOKEN },
    credentials: 'same-origin'
  })
  .then(r => r.json())
  .then(data => {
    if (data.success) {
      approvalSteps = [];
      renderApprovalSteps();
      showToast('Approval flow deleted', 'success');
      loadCurrentFlow();
    } else {
      showToast('Failed to delete flow', 'error');
    }
  })
  .catch(() => showToast('Error deleting flow', 'error'));
};

window.loadOrgUsers = async function(q = '') {
  const list = document.getElementById('orgUserList');
  if (!list) return;
  list.innerHTML = '<div style="padding:0.5rem">Loading...</div>';
  const params = new URLSearchParams({ q, org_type_id: window.SELECTED_ORG_TYPE_ID });
  const resp = await fetch(`/core-admin/api/org-users/${window.SELECTED_ORG_ID}/?${params}`);
  const data = await resp.json();
  if (data.success) {
    list.innerHTML = (data.users || []).map(u =>
      `<div class="user-item" draggable="true" ondragstart="startUserDrag(${u.id}, '${u.name.replace("'", "\'")}', '${u.role.replace("'", "\'")}')">${u.name} <span class="role">(${u.role})</span></div>`
    ).join('') || '<div class="empty-msg">No users found</div>';
  } else {
    list.innerHTML = '<div class="error-msg">Failed to load users</div>';
  }
};

window.startUserDrag = function(id, name, role) {
  draggedUser = { id, name, role };
};

window.dropOnSteps = function(e) {
  e.preventDefault();
  if (!draggedUser) return;
  approvalSteps.push({ role: draggedUser.role.toLowerCase(), user: { id: draggedUser.id, name: draggedUser.name } });
  renderApprovalSteps();
  draggedUser = null;
};

window.loadCurrentFlow = async function() {
  const container = document.getElementById('currentFlowList');
  if (!container) return;
  container.innerHTML = '';
  const resp = await fetch(`/core-admin/approval-flow/${window.SELECTED_ORG_ID}/get/`);
  const data = await resp.json();
  if (data.success) {
    if (data.steps.length === 0) {
      container.innerHTML = '<li>No approval flow defined.</li>';
    } else {
      container.innerHTML = data.steps.map(s => `<li>${s.step_order}. ${s.role_required} – ${s.user_name || 'Unassigned'}</li>`).join('');
    }
  }
};

document.addEventListener('DOMContentLoaded', () => {
  if (window.SELECTED_ORG_ID) {
    loadCurrentFlow();
    loadRoles();
    // Optionally also load the editable flow if needed:
    // loadApprovalFlow();
    // Or open the editor if you want to auto-open:
    // openApprovalFlowEditor();
    const select = document.getElementById('approvalFlowOrgSelect');
    if (select) {
      select.value = String(window.SELECTED_ORG_ID);
      select.addEventListener('change', () => {
        window.SELECTED_ORG_ID = select.value;
        loadRoles();
      });
    }
    const typeSelect = document.getElementById('approvalCategorySelect');
    if (typeSelect) {
      typeSelect.addEventListener('change', loadRoles);
    }
  }
});

  // Expose approval flow helpers
  window.openApprovalFlowEditor = openApprovalFlowEditor;
  window.closeModal = closeModal;
})();
