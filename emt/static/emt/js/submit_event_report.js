document.addEventListener('DOMContentLoaded', function(){
  document.querySelectorAll('.form-group input:not([type=checkbox]):not([type=radio]), .form-group textarea, .form-group select').forEach(function(el){
    if(!el.placeholder) el.placeholder = ' ';
  });

  const posField = document.getElementById('id_pos_pso_mapping');
  if(posField){
    posField.addEventListener('click', openOutcomeModal);
    posField.readOnly = true;
    posField.style.cursor = 'pointer';
  }
});

function openOutcomeModal(){
  const modal = document.getElementById('outcomeModal');
  const container = document.getElementById('outcomeOptions');
  const url = modal.dataset.url;
  modal.classList.add('show');
  container.textContent = 'Loading...';
  fetch(url)
    .then(r => r.json())
    .then(data => {
      if(data.success){
        container.innerHTML = '';
        data.pos.forEach(po => { addOption(container,'PO: ' + po.description); });
        data.psos.forEach(pso => { addOption(container,'PSO: ' + pso.description); });
      } else {
        container.textContent = 'No data';
      }
    })
    .catch(() => { container.textContent = 'Error loading'; });
}

function addOption(container, labelText){
  const lbl = document.createElement('label');
  const cb = document.createElement('input');
  cb.type = 'checkbox';
  cb.value = labelText;
  lbl.appendChild(cb);
  lbl.appendChild(document.createTextNode(' ' + labelText));
  container.appendChild(lbl);
  container.appendChild(document.createElement('br'));
}

document.getElementById('outcomeCancel').onclick = function(){
  document.getElementById('outcomeModal').classList.remove('show');
};

document.getElementById('outcomeSave').onclick = function(){
  const modal = document.getElementById('outcomeModal');
  const selected = Array.from(modal.querySelectorAll('input[type=checkbox]:checked')).map(c => c.value);
  const field = document.getElementById('id_pos_pso_mapping');
  let existing = field.value.trim();
  if(existing){ existing += '\n'; }
  field.value = existing + selected.join('\n');
  modal.classList.remove('show');
};
