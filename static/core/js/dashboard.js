document.addEventListener('DOMContentLoaded', function () {
  const tabs = document.querySelectorAll('.notification-tabs .tab');
  const contents = document.querySelectorAll('.tab-content');

  tabs.forEach(tab => {
    tab.addEventListener('click', function () {
      // Remove active from all tabs
      tabs.forEach(t => {
        t.classList.remove('active');
        t.setAttribute('aria-selected', 'false');
      });
      // Hide all contents
      contents.forEach(c => c.style.display = 'none');

      // Activate this tab
      this.classList.add('active');
      this.setAttribute('aria-selected', 'true');
      // Show related content
      document.getElementById(this.dataset.tab).style.display = 'block';
    });
  });
  // Show first tab by default if page is reloaded
  document.querySelector('.tab.tab-ongoing').click();
});
