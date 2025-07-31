document.addEventListener('DOMContentLoaded', function(){
  document.querySelectorAll('.form-group input:not([type=checkbox]):not([type=radio]), .form-group textarea, .form-group select').forEach(function(el){
    if(!el.placeholder) el.placeholder = ' ';
  });

  const posField = document.getElementById('id_pos_pso_mapping');
  const modal = document.getElementById('outcomeModal');
  if(posField && modal && modal.dataset.url){
    posField.addEventListener('click', openOutcomeModal);
    posField.readOnly = true;
    posField.style.cursor = 'pointer';
  }

  initAttachments();
});

function openOutcomeModal(){
  const modal = document.getElementById('outcomeModal');
  const container = document.getElementById('outcomeOptions');
  const url = modal.dataset.url;
  if(!url){
    alert('No organization set for this proposal.');
    return;
  }
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

function initAttachments(){
  const list = document.getElementById('attachment-list');
  const addBtn = document.getElementById('add-attachment-btn');
  const template = document.getElementById('attachment-template');
  const totalInput = document.querySelector('input[name$="-TOTAL_FORMS"]');
  if(!list || !addBtn || !template || !totalInput) return;

  function bind(block){
    const upload = block.querySelector('.attach-upload');
    const fileInput = block.querySelector('.file-input');
    const removeBtn = block.querySelector('.attach-remove');
    upload.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', () => {
      if(fileInput.files && fileInput.files[0]){
        const url = URL.createObjectURL(fileInput.files[0]);
        upload.innerHTML = `<img src="${url}">`;
        upload.appendChild(removeBtn);
        removeBtn.style.display = 'flex';
      }
    });
    removeBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      fileInput.value = '';
      upload.innerHTML = '<span class="attach-add">+</span>';
      removeBtn.style.display = 'none';
      const del = block.querySelector('input[name$="-DELETE"]');
      if(del) del.checked = true;
    });
  }

  list.querySelectorAll('.attachment-block').forEach(bind);

  addBtn.addEventListener('click', () => {
    const idx = +totalInput.value;
    const html = template.innerHTML.replace(/__prefix__/g, idx);
    const temp = document.createElement('div');
    temp.innerHTML = html.trim();
    const block = temp.firstElementChild;
    list.appendChild(block);
    totalInput.value = idx + 1;
    bind(block);
    block.querySelector('.file-input').click();
  });
}
