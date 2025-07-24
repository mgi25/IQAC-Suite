 document.addEventListener('DOMContentLoaded', () => {
   document.querySelectorAll('.delete-role-form').forEach(form => {
     form.addEventListener('submit', e => {
       if (!confirm('Delete this role?')) {
         e.preventDefault();
       }
     });
   });
 });
