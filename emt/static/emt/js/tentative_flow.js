document.addEventListener('DOMContentLoaded', () => {
  const tableBody = document.querySelector('#flow-table tbody');
  const addRowBtn = document.getElementById('add-row-btn');
  const hiddenField = document.getElementById('id_content');
  const form = document.querySelector('form');

  function addRow(time = '', activity = '') {
    const row = document.createElement('tr');
    row.innerHTML = `
      <td><input type="datetime-local" class="time-input" value="${time}"></td>
      <td><input type="text" class="activity-input" value="${activity}"></td>
      <td><button type="button" class="btn-remove-row">Remove</button></td>
    `;
    row.querySelector('.btn-remove-row').addEventListener('click', () => row.remove());
    row.querySelectorAll('input').forEach(input => {
      input.addEventListener('input', () => {
        input.classList.remove('has-error');
        const err = input.parentElement.querySelector('.error-message');
        if (err) err.remove();
      });
    });
    tableBody.appendChild(row);
  }

  // Load existing schedule
  const initial = (hiddenField.value || '').trim();
  if (initial) {
    initial.split('\n').forEach(line => {
      const parts = line.split('||');
      const time = (parts[0] || '').trim();
      const activity = (parts[1] || '').trim();
      addRow(time, activity);
    });
  } else {
    addRow();
  }

  addRowBtn.addEventListener('click', () => addRow());

  function clearErrors() {
    tableBody.querySelectorAll('.error-message').forEach(e => e.remove());
    tableBody.querySelectorAll('.has-error').forEach(el => el.classList.remove('has-error'));
  }

  function showError(input, message) {
    input.classList.add('has-error');
    let err = input.parentElement.querySelector('.error-message');
    if (!err) {
      err = document.createElement('div');
      err.className = 'error-message';
      input.parentElement.appendChild(err);
    }
    err.textContent = message;
  }

  form.addEventListener('submit', (e) => {
    clearErrors();
    const lines = [];
    let valid = true;
    tableBody.querySelectorAll('tr').forEach(tr => {
      const timeInput = tr.querySelector('.time-input');
      const activityInput = tr.querySelector('.activity-input');
      const time = timeInput.value.trim();
      const activity = activityInput.value.trim();
      if (!time) {
        showError(timeInput, 'Date & time required');
        valid = false;
      } else if (isNaN(Date.parse(time))) {
        showError(timeInput, 'Invalid date & time');
        valid = false;
      }
      if (!activity) {
        showError(activityInput, 'Activity required');
        valid = false;
      }
      if (time && activity) {
        lines.push(`${time}||${activity}`);
      }
    });
    if (!valid) {
      e.preventDefault();
      return;
    }
    hiddenField.value = lines.join('\n');
  });
});

