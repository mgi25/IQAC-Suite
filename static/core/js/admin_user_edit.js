document.addEventListener('DOMContentLoaded', () => {
  const container   = document.getElementById('roles-list-container');
  const addBtn      = document.getElementById('add-role-btn');
  const template    = document.getElementById('role-card-template').innerHTML;
  const totalForms  = () => document.querySelector('input[name$="-TOTAL_FORMS"]');

  // bind existing cards
  container.querySelectorAll('.role-card').forEach(bindCard);

  // add-new
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

    // ensure “Other…” appears
    [deptGrp, clubGrp, cenGrp].forEach(grp => {
      const sel = grp.querySelector('select');
      if (sel && ![...sel.options].some(o=>o.value==='other')) {
        sel.add(new Option('Other…','other'));
      }
    });

    // on role change, show only the relevant group
    roleSel.addEventListener('change', () => {
      const v = roleSel.value;
      deptGrp.style.display = ['hod','faculty','dept_iqac'].includes(v) ? 'block' : 'none';
      clubGrp.style.display = (v==='club_head')   ? 'block' : 'none';
      cenGrp.style.display  = (v==='center_head') ? 'block' : 'none';
    });
    roleSel.dispatchEvent(new Event('change'));

    // toggle “Other…” text inputs
    const setupOther = (grp, inputCls) => {
      const sel = grp.querySelector('select');
      const txt = grp.querySelector(`.${inputCls}`);
      sel.addEventListener('change', () => {
        txt.style.display = (sel.value==='other') ? 'block' : 'none';
      });
    };
    setupOther(deptGrp, 'add-dept-input');
    setupOther(clubGrp, 'add-club-input');
    setupOther(cenGrp, 'add-center-input');

    // remove: hide & flag DELETE
    remBtn.addEventListener('click', () => {
      if (delBox) delBox.checked = true;
      card.style.display = 'none';
    });
  }
});
