document.addEventListener('DOMContentLoaded', () => {
  const table = $('#rolesTable').DataTable({
    dom: '<"dt-toolbar d-flex justify-content-between align-items-center flex-wrap mb-3"lfB>rtip',
    pagingType: 'simple',
    lengthMenu: [[10, 25, 50, -1], [10, 25, 50, "All"]],
    pageLength: 25,
    order: [[0, 'asc'], [1, 'asc']],
    buttons: ['copy', 'excel', 'pdf', 'print']
  });

  document.querySelectorAll('.delete-role-form').forEach(form => {
    form.addEventListener('submit', e => {
      if (!confirm('Delete this role?')) {
        e.preventDefault();
      }
    });
  });

  const orgTypeSel = document.getElementById('orgTypeSelect');
  const orgSel = document.getElementById('orgSelect');

  orgTypeSel.addEventListener('change', () => {
    const val = orgTypeSel.value;
    Array.from(orgSel.options).forEach(opt => {
      if (!val || opt.dataset.orgType === val || opt.value === '') {
        opt.style.display = '';
      } else {
        opt.style.display = 'none';
      }
    });
    orgSel.value = '';
  });
});
