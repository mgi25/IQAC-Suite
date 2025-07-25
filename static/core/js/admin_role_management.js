document.addEventListener('DOMContentLoaded', () => {
  $('#rolesTable').DataTable({
    dom: '<"dt-toolbar d-flex justify-content-between align-items-center flex-wrap mb-3"lf>rtip',
    pagingType: 'simple',
    lengthMenu: [[10, 25, 50, -1], [10, 25, 50, "All"]],
    pageLength: 25,
    order: [[0, 'asc']]
  });

  document.querySelectorAll('.delete-role-form').forEach(form => {
    form.addEventListener('submit', e => {
      if (!confirm('Delete this role?')) {
        e.preventDefault();
      }
    });
  });

  // simple confirm for deletions handled above
});
