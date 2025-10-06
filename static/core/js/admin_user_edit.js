// simplified dynamic organization handling

document.addEventListener('DOMContentLoaded', () => {
  const listBox    = document.getElementById('roles-list-container');
  const addBtn     = document.getElementById('add-role-btn');
  const tplHTML    = document.getElementById('role-card-template').innerHTML;
  // Find the TOTAL_FORMS input for this formset by looking inside the roles container
  let totalInput = listBox.querySelector('input[name$="-TOTAL_FORMS"]');
  if (!totalInput) totalInput = document.querySelector('input[name$="-TOTAL_FORMS"]');
  const saveBtn    = document.querySelector('#user-edit-form button[type=submit]');

  const ORG_OPTIONAL_ROLES = ['dean','academic_coordinator','director','cdl','uni_iqac','admin'];

  const fetchJson = (url) => fetch(url, {headers: {'Accept': 'application/json'}}).then(r => r.json());

  // utility: remove validation errors from a field element
  function clearFieldErrors(field) {
    if (!field) return;
    // Remove sibling error lists/spans inserted by Django templates
    const errEls = Array.from(field.parentElement.querySelectorAll('.errorlist'));
    errEls.forEach(e => e.remove());
    // Remove invalid CSS classes if present
    field.classList.remove('error');
    field.removeAttribute('aria-invalid');
  }

  // Mark a card as logically deleted (checks DELETE input) and hide it
  function markCardDeleted(card) {
    const delBox = card.querySelector("input[name$='-DELETE']");
    // keep the DELETE input enabled so the formset knows this form is deleted
  // Only target visible controls (exclude hidden inputs like form-*-id and management fields)
  const controls = Array.from(card.querySelectorAll('select, input:not([type=hidden])')).filter(el => el !== delBox);
    if (delBox) delBox.checked = true;
    controls.forEach(s => {
      // clear value so partial data isn't submitted
      try { s.value = ''; } catch (e) {}
      // disable so it won't be validated by browser
      s.disabled = true;
      clearFieldErrors(s);
    });
    // Remove any server-rendered error lists inside this card
    const cardErrs = card.querySelectorAll('.errorlist');
    cardErrs.forEach(e => e.remove());
    card.style.display = 'none';
  }

  // Unmark a card as deleted and show it
  function unmarkCardDeleted(card) {
    const delBox = card.querySelector("input[name$='-DELETE']");
  const controls = Array.from(card.querySelectorAll('select, input:not([type=hidden])')).filter(el => el !== delBox);
    if (delBox) delBox.checked = false;
    controls.forEach(s => {
      s.disabled = false;
    });
    card.style.display = '';
  }

  function bindCard(card) {
    const typeSel = card.querySelector('.org-type-select');
    const roleSel = card.querySelector("select[name$='-role']");
    const orgSel  = card.querySelector("select[name$='-organization']");
    const orgGroup = card.querySelectorAll('.field-group')[2];
    const delBox  = card.querySelector("input[name$='-DELETE']");
    const remBtn  = card.querySelector('.remove-role-btn');

    // Do not auto-hide empty cards on initial bind. We'll populate only
    // when a category exists, and otherwise wait for the user to choose one.

    async function loadOrganizations() {
      const typeId = typeSel.value;
      const current = orgSel ? orgSel.value : null;

      if (!typeId) {
        // If category cleared, remove this card from active submission
        if (orgSel) {
          orgSel.innerHTML = '<option value="">---------</option>';
          orgSel.value = '';
        }
        if (roleSel) {
          roleSel.innerHTML = '<option value="">---------</option>';
          roleSel.value = '';
        }
        markCardDeleted(card);
        return;
      }

      // category chosen -> ensure card is active
      unmarkCardDeleted(card);

      const data = await fetchJson(`/core-admin/api/org-type/${typeId}/organizations/`);
      const orgs = data.organizations || [];
      if (orgSel) {
        orgSel.innerHTML = '<option value="">---------</option>' +
          orgs.map(o => `<option value="${o.id}">${o.name}</option>`).join('');
        if (current && orgSel.querySelector(`option[value="${current}"]`)) {
          orgSel.value = current;
        }
      }
      await loadRoles();
    }

    async function loadRoles() {
      const typeId = typeSel.value;
      const orgId  = orgSel ? orgSel.value : null;
      const current = roleSel ? roleSel.value : null;

      // if both empty, keep role list empty and consider deleted
      if (!typeId && !orgId) {
        if (roleSel) roleSel.innerHTML = '<option value="">---------</option>';
        toggleOrg();
        if (!typeSel.value) markCardDeleted(card);
        return;
      }

      unmarkCardDeleted(card);

      let url = '';
      if (orgId) {
        url = `/core-admin/api/organization/${orgId}/roles/`;
      } else {
        url = `/core-admin/api/org-type/${typeId}/roles/`;
      }
      const data = await fetchJson(url);
      const roles = data.roles || [];
      if (roleSel) {
        roleSel.innerHTML = '<option value="">---------</option>' +
          roles.map(r => `<option value="${r.id}">${r.name}</option>`).join('');
        if (current && roleSel.querySelector(`option[value="${current}"]`)) {
          roleSel.value = current;
        }
      }
      toggleOrg();
    }

    function toggleOrg() {
      if (!roleSel) return;
      const opt = roleSel.options[roleSel.selectedIndex];
      const r = opt ? opt.textContent.toLowerCase() : '';
      if (ORG_OPTIONAL_ROLES.includes(r)) {
        if (orgGroup) orgGroup.style.display = 'none';
        if (orgSel) orgSel.value = '';
      } else {
        if (orgGroup) orgGroup.style.display = '';
      }
    }

    // Attach events
    typeSel.addEventListener('change', loadOrganizations);
    if (orgSel) orgSel.addEventListener('change', loadRoles);
    if (roleSel) roleSel.addEventListener('change', toggleOrg);

    // Removal button should mark delete and hide
    remBtn?.addEventListener('click', () => {
      markCardDeleted(card);
    });

    // Initial population only if category already chosen (existing forms)
    if (typeSel.value) {
      loadOrganizations();
    }
  }

  // bind existing cards
  document.querySelectorAll('.role-card').forEach(bindCard);

  // add new card
  addBtn.addEventListener('click', () => {
    saveBtn.disabled = true;
    const idx = +totalInput.value;
    listBox.insertAdjacentHTML('beforeend', tplHTML.replace(/__prefix__/g, idx));
    const newCard = listBox.querySelector(`.role-card[data-form-index="${idx}"]`);
    bindCard(newCard);
    // Newly-inserted cards should be active (not auto-deleted). Ensure it's unmarked
    // deleted and focus the category select to help user start filling it.
    try {
      unmarkCardDeleted(newCard);
      const cat = newCard.querySelector('.org-type-select');
      if (cat) cat.focus();
    } catch (e) {
      // ignore
    }
    totalInput.value = idx + 1;
    requestAnimationFrame(() => (saveBtn.disabled = false));
  });
});
