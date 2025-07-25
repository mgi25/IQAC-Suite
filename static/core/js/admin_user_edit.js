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
    const typeSel = card.querySelector('.org-type-select');
    const roleSel = card.querySelector("select[name$='-role']");
    const orgSel = card.querySelector("select[name$='-organization']");
    const orgGroup = card.querySelectorAll('.field-group')[2];
    const delBox = card.querySelector("input[name$='-DELETE']");
    const remBtn = card.querySelector('.remove-role-btn');

    function populateOrganizations() {
      const typeId = typeSel.value;
      const orgs = ORGS_BY_TYPE[typeId] || [];
      const current = orgSel.value;
      orgSel.innerHTML = '<option value="">---------</option>' +
        orgs.map(o => `<option value="${o.id}">${o.name}</option>`).join('');
      if (current && orgSel.querySelector(`option[value="${current}"]`)) {
        orgSel.value = current;
      }
    }

    function populateRoleOptions() {
      const current = roleSel.value;
      const opts = [...BASE_ROLES];
      let extras = [];
      const typeId = typeSel.value;
      const orgId = orgSel.value;
      if (orgId && ORG_ROLES[orgId]) {
        extras = ORG_ROLES[orgId];
      } else if (typeId && ROLES_BY_TYPE[typeId]) {
        extras = ROLES_BY_TYPE[typeId];
      }
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

    typeSel.addEventListener('change', () => {
      populateOrganizations();
      populateRoleOptions();
      toggleOrg();
    });

    orgSel.addEventListener('change', () => {
      populateRoleOptions();
      toggleOrg();
    });

    roleSel.addEventListener('change', toggleOrg);

    populateOrganizations();
    populateRoleOptions();
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
