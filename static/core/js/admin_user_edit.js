// simplified dynamic organization handling

document.addEventListener('DOMContentLoaded', () => {
  const listBox    = document.getElementById('roles-list-container');
  const addBtn     = document.getElementById('add-role-btn');
  const tplHTML    = document.getElementById('role-card-template').innerHTML;
  const totalInput = document.querySelector('input[name$="-TOTAL_FORMS"]');
  const saveBtn    = document.querySelector('#user-edit-form button[type=submit]');

  const ORG_OPTIONAL_ROLES = ['dean','academic_coordinator','director','cdl','uni_iqac','admin'];

  const fetchJson = (url) => fetch(url, {headers: {'Accept': 'application/json'}}).then(r => r.json());

  function bindCard(card) {
    const typeSel = card.querySelector('.org-type-select');
    const roleSel = card.querySelector("select[name$='-role']");
    const orgSel  = card.querySelector("select[name$='-organization']");
    const orgGroup = card.querySelectorAll('.field-group')[2];
    const delBox  = card.querySelector("input[name$='-DELETE']");
    const remBtn  = card.querySelector('.remove-role-btn');

    async function loadOrganizations() {
      const typeId = typeSel.value;
      const current = orgSel.value;
      if (!typeId) {
        orgSel.innerHTML = '<option value="">---------</option>';
        await loadRoles();
        return;
      }
      const data = await fetchJson(`/core-admin/api/org-type/${typeId}/organizations/`);
      const orgs = data.organizations || [];
      orgSel.innerHTML = '<option value="">---------</option>' +
        orgs.map(o => `<option value="${o.id}">${o.name}</option>`).join('');
      if (current && orgSel.querySelector(`option[value="${current}"]`)) {
        orgSel.value = current;
      }
      await loadRoles();
    }

    async function loadRoles() {
      const typeId = typeSel.value;
      const orgId  = orgSel.value;
      const current = roleSel.value;
      if (!typeId && !orgId) {
        roleSel.innerHTML = '<option value="">---------</option>';
        toggleOrg();
        return;
      }
      let url = '';
      if (orgId) {
        url = `/core-admin/api/organization/${orgId}/roles/`;
      } else {
        url = `/core-admin/api/org-type/${typeId}/roles/`;
      }
      const data = await fetchJson(url);
      const roles = data.roles || [];
      roleSel.innerHTML = '<option value="">---------</option>' +
        roles.map(r => `<option value="${r}">${r}</option>`).join('');
      if (current && roleSel.querySelector(`option[value="${current}"]`)) {
        roleSel.value = current;
      }
      toggleOrg();
    }

    function toggleOrg() {
      const r = (roleSel.value || '').toLowerCase();
      if (ORG_OPTIONAL_ROLES.includes(r)) {
        orgGroup.style.display = 'none';
        orgSel.value = '';
      } else {
        orgGroup.style.display = '';
      }
    }

    typeSel.addEventListener('change', loadOrganizations);
    orgSel.addEventListener('change', loadRoles);
    roleSel.addEventListener('change', toggleOrg);

    loadOrganizations();

    remBtn?.addEventListener('click', () => {
      if (delBox) delBox.checked = true;
      card.style.display = 'none';
    });
  }

  document.querySelectorAll('.role-card').forEach(bindCard);

  addBtn.addEventListener('click', () => {
    saveBtn.disabled = true;
    const idx = +totalInput.value;
    listBox.insertAdjacentHTML('beforeend', tplHTML.replace(/__prefix__/g, idx));
    bindCard(listBox.querySelector(`.role-card[data-form-index="${idx}"]`));
    totalInput.value = idx + 1;
    requestAnimationFrame(() => (saveBtn.disabled = false));
  });
});
