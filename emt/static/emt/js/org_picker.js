// JS: Only show relevant org select
document.addEventListener('DOMContentLoaded', function() {
  const orgType = document.getElementById('id_org_type');
  const orgFields = {
    department: document.getElementById('dept-select-group'),
    association: document.getElementById('assoc-select-group'),
    club: document.getElementById('club-select-group'),
    center: document.getElementById('center-select-group'),
    cell: document.getElementById('cell-select-group'),
  };
  function syncOrgPicker() {
    Object.values(orgFields).forEach(g => g.style.display = 'none');
    const v = orgType.value;
    if (orgFields[v]) orgFields[v].style.display = '';
  }
  orgType.addEventListener('change', syncOrgPicker);
  syncOrgPicker(); // On page load
});
