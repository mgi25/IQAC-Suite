// Registration form dynamic role assignment with TomSelect

document.addEventListener('DOMContentLoaded', function () {
  const container = document.getElementById('role-assignments');
  const addBtn = document.getElementById('add-role-btn');
  const assignmentsInput = document.getElementById('assignments-json');
  const form = document.getElementById('registrationForm');

  function initRow(row) {
    const orgSelect = row.querySelector('.organization-select');
    const roleSelect = row.querySelector('.role-select');

    const orgTom = new TomSelect(orgSelect, {
      valueField: 'id',
      labelField: 'text',
      searchField: 'text',
      maxOptions: 20,
      load: function (query, callback) {
        fetch(`/api/organizations/?q=${encodeURIComponent(query)}`)
          .then((r) => r.json())
          .then((data) => callback(data.organizations || []))
          .catch(() => callback());
      },
      onChange: function (value) {
        roleTom.clear();
        roleTom.clearOptions();
        if (!value) return;
        fetch(`/api/roles/?organization=${value}`)
          .then((r) => r.json())
          .then((data) => {
            roleTom.addOptions(data.roles || []);
          });
      },
    });

    const roleTom = new TomSelect(roleSelect, {
      valueField: 'id',
      labelField: 'text',
      searchField: 'text',
      maxOptions: 20,
      load: function (query, callback) {
        const orgId = orgSelect.value;
        if (!orgId) return callback();
        fetch(`/api/roles/?organization=${orgId}&q=${encodeURIComponent(query)}`)
          .then((r) => r.json())
          .then((data) => callback(data.roles || []))
          .catch(() => callback());
      },
    });
  }

  function addRow() {
    const row = document.createElement('div');
    row.className = 'assignment-row';
    row.innerHTML = `
      <select class="organization-select" placeholder="Organization"></select>
      <select class="role-select" placeholder="Role"></select>
    `;
    container.appendChild(row);
    initRow(row);
  }

  if (addBtn) {
    addBtn.addEventListener('click', function (e) {
      e.preventDefault();
      addRow();
    });
  }

  // Initialize with one row
  if (container) {
    addRow();
  }

  if (form) {
    form.addEventListener('submit', function () {
      const data = [];
      container.querySelectorAll('.assignment-row').forEach((row) => {
        const org = row.querySelector('.organization-select').value;
        const role = row.querySelector('.role-select').value;
        if (org && role) data.push({ organization: org, role: role });
      });
      assignmentsInput.value = JSON.stringify(data);
    });
  }
});
