/* header bell toggle & outside-click close */
document.addEventListener('DOMContentLoaded', () => {
  const btn   = document.getElementById('notifBtn');
  const pop   = document.getElementById('notifPopup');
  const close = document.getElementById('notifClose') || document.getElementById('notifClose');

  if (!btn || !pop) return;

  btn.addEventListener('click', (e) => {
    e.stopPropagation();
    pop.classList.toggle('open');
  });

  if (close) close.addEventListener('click', () => pop.classList.remove('open'));

  document.addEventListener('click', (e) => {
    if (pop.classList.contains('open') && !pop.contains(e.target) && e.target !== btn) {
      pop.classList.remove('open');
    }
  });
});
