document.addEventListener('DOMContentLoaded', () => {
  const form = document.querySelector('.review-form-ultra');
  if (!form) return;
  const commentField = form.querySelector('textarea[name="comment"]');
  const rejectBtn = form.querySelector('button[name="action"][value="reject"]');
  if (rejectBtn) {
    rejectBtn.addEventListener('click', (e) => {
      if (!commentField.value.trim()) {
        e.preventDefault();
        alert('Please add a comment before rejecting the proposal.');
      }
    });
  }
});
