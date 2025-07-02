document.addEventListener('DOMContentLoaded', () => {
  const container   = document.getElementById('roles-list-container');
  const addBtn      = document.getElementById('add-role-btn');
  const template    = document.getElementById('role-card-template').innerHTML;
  const totalForms  = () => document.querySelector('input[name$="-TOTAL_FORMS"]');

  // Bind existing cards
  container.querySelectorAll('.role-card').forEach(bindCard);

  // Add new role card
  addBtn.addEventListener('click', () => {
    const idx = parseInt(totalForms().value, 10);
    const html = template.replace(/__prefix__/g, idx);
    container.insertAdjacentHTML('beforeend', html);
    bindCard(container.querySelector(`.role-card[data-form-index="${idx}"]`));
    totalForms().value = idx + 1;
  });

  function bindCard(card) {
    const roleSel = card.querySelector('select[name$="-role"]');
    const deptGrp = card.querySelector('.dept-group');
    const clubGrp = card.querySelector('.club-group');
    const cenGrp  = card.querySelector('.center-group');
    const remBtn  = card.querySelector('.remove-role-btn');
    const delBox  = card.querySelector('input[type="checkbox"][name$="-DELETE"]');

    // Make sure "Other…" option exists (only once)
    [deptGrp, clubGrp, cenGrp].forEach(grp => {
      const sel = grp.querySelector('select');
      if (sel && ![...sel.options].some(o => o.value === 'other')) {
        sel.add(new Option('Other…', 'other'));
      }
    });

    // On role change, show only the relevant group
    roleSel.addEventListener('change', () => {
      const v = roleSel.value;
      deptGrp.style.display = ['hod','faculty','dept_iqac'].includes(v) ? 'block' : 'none';
      clubGrp.style.display = (v === 'club_head') ? 'block' : 'none';
      cenGrp.style.display  = (v === 'center_head') ? 'block' : 'none';
    });
    roleSel.dispatchEvent(new Event('change'));

    // Helper to toggle "Other..." input
    function setupOther(grp, inputCls) {
    const sel = grp.querySelector('select');
    const txt = grp.querySelector(`.${inputCls}`);
    if (!sel || !txt) return;
    function toggleInput() {
      if (sel.value === 'other') {
        txt.style.display = 'block';
        txt.required = true;
        sel.value = '';   // <--- THIS IS THE FIX!
      } else {
        txt.style.display = 'none';
        txt.required = false;
        txt.value = '';
      }
    }
    sel.addEventListener('change', toggleInput);
    toggleInput();
  }

    setupOther(deptGrp, 'add-dept-input');
    setupOther(clubGrp, 'add-club-input');
    setupOther(cenGrp, 'add-center-input');

    // Remove: hide & flag DELETE
    remBtn.addEventListener('click', () => {
      if (delBox) delBox.checked = true;
      card.style.display = 'none';
    });
  }
});
