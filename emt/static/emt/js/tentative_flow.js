document.addEventListener('DOMContentLoaded', () => {
  const tableBody = document.querySelector('#flow-table tbody');
  const addRowBtn = document.getElementById('add-row-btn');
  const hiddenField = document.getElementById('id_content');
  const form = document.querySelector('form');

  function addRow(time = '', activity = '') {
    const row = document.createElement('tr');
    row.innerHTML = `
      <td><input type="text" class="time-input" value="${time}"></td>
      <td><input type="text" class="activity-input" value="${activity}"></td>
      <td><button type="button" class="btn-remove-row">Remove</button></td>
    `;
    row.querySelector('.btn-remove-row').addEventListener('click', () => row.remove());
    tableBody.appendChild(row);
  }

  // Load existing schedule
  const initial = (hiddenField.value || '').trim();
  if (initial) {
    initial.split('\n').forEach(line => {
      const parts = line.split(/[-–]\s*/);
      const time = parts.shift()?.trim() || '';
      const activity = parts.join(' - ').trim();
      addRow(time, activity);
    });
  } else {
    addRow();
  }

  addRowBtn.addEventListener('click', () => addRow());

  form.addEventListener('submit', () => {
    const lines = [];
    tableBody.querySelectorAll('tr').forEach(tr => {
      const time = tr.querySelector('.time-input').value.trim();
      const activity = tr.querySelector('.activity-input').value.trim();
      if (time || activity) {
        lines.push(`${time} – ${activity}`);
      }
    });
    hiddenField.value = lines.join('\n');
  });
});

