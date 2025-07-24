// simplified dynamic organization handling

document.addEventListener('DOMContentLoaded', () => {
  const $ = (sel, ctx = document) => ctx.querySelector(sel);
  const $$ = (sel, ctx = document) => [...ctx.querySelectorAll(sel)];

  const listBox    = document.getElementById('roles-list-container');
  const addBtn     = document.getElementById('add-role-btn');
  const tplHTML    = document.getElementById('role-card-template').innerHTML;
  const totalInput = document.querySelector('input[name$="-TOTAL_FORMS"]');
  const saveBtn    = document.querySelector('#user-edit-form button[type=submit]');

  const ORG_OPTIONAL_ROLES = ['dean','academic_coordinator','director','cdl','uni_iqac','admin'];

  function bindCard(card) {
    const roleSel = card.querySelector("select[name$='-role']");
    const orgSel = card.querySelector("select[name$='-organization']");
    const orgGroup = card.querySelectorAll('.field-group')[1];
    const delBox = card.querySelector("input[name$='-DELETE']");
    const remBtn = card.querySelector('.remove-role-btn');

    function populateOptions() {
      const current = roleSel.value;
      const opts = [...BASE_ROLES];
      const extras = ORG_ROLES[orgSel.value] || [];
      extras.forEach(r => opts.push([r, r]));
      roleSel.innerHTML = opts.map(o => `<option value="${o[0]}">${o[1]}</option>`).join('');
      if (current) roleSel.value = current;
    }

    function toggleOrg() {
      const r = (roleSel.value || '').toLowerCase();
      if (ORG_OPTIONAL_ROLES.includes(r)) {
        orgGroup.style.display = 'none';
        const inp = orgGroup.querySelector('select, input');
        if (inp) inp.value = '';
      } else {
        orgGroup.style.display = '';
      }
    }

    orgSel.addEventListener('change', () => {
      populateOptions();
      toggleOrg();
    });
    roleSel.addEventListener('change', toggleOrg);
    populateOptions();
    toggleOrg();

    remBtn?.addEventListener('click', () => {
      if (delBox) delBox.checked = true;
      card.style.display = 'none';
    });
  }

  $$(".role-card", listBox).forEach(bindCard);

  addBtn.addEventListener('click', () => {
    saveBtn.disabled = true;
    const idx = +totalInput.value;
    listBox.insertAdjacentHTML('beforeend', tplHTML.replace(/__prefix__/g, idx));
    bindCard($(`.role-card[data-form-index="${idx}"]`));
    totalInput.value = idx + 1;
    requestAnimationFrame(() => (saveBtn.disabled = false));
  });
});
