/* ─────  admin_user_edit.js  v3  ───────────────────────── */

document.addEventListener("DOMContentLoaded", () => {
  /* short helpers */
  const $  = (sel, ctx = document) => ctx.querySelector(sel);
  const $$ = (sel, ctx = document) => [...ctx.querySelectorAll(sel)];

  /* DOM handles */
  const listBox   = $("#roles-list-container");
  const addBtn    = $("#add-role-btn");
  const template  = $("#role-card-template").innerHTML;
  const totalForm = () => $('input[name$="-TOTAL_FORMS"]');
  const saveBtn   = $("#user-edit-form button[type=submit]");

  /* =======================================================
     bind a single “role-card” (existing OR new)
     ======================================================= */
  function bindCard(card) {
    const roleSel = $("select[name$='-role']", card);
    const deptGrp = $(".dept-group",   card);
    const clubGrp = $(".club-group",   card);
    const cenGrp  = $(".center-group", card);
    const delBox  = $("input[name$='-DELETE']", card);
    const remBtn  = $(".remove-role-btn", card);

    /* make sure each select has an “Other…” option only once */
    [deptGrp, clubGrp, cenGrp].forEach((grp) => {
      const sel = $("select", grp);
      if (sel && ![...sel.options].some((o) => o.value === "other")) {
        sel.add(new Option("Other…", "other"));
      }
    });

    /* toggle the three org-pickers when role changes */
    function showRelevantGroups() {
      const v = roleSel.value;
      deptGrp.style.display = ["hod", "faculty", "dept_iqac"].includes(v) ? "" : "none";
      clubGrp.style.display = v === "club_head"   ? "" : "none";
      cenGrp.style.display  = v === "center_head" ? "" : "none";
    }
    roleSel.addEventListener("change", showRelevantGroups);
    showRelevantGroups();

    /* generic “Other…” handler */
    function enableOther(grp, cls) {
      const sel = $("select", grp);
      const txt = $("." + cls, grp);
      if (!sel || !txt) return;

      function toggle() {
        if (sel.value === "other") {
          txt.style.display = "block";
          txt.required = true;
          sel.value = "";            // clear the <option>
        } else {
          txt.style.display = "none";
          txt.required = false;
          txt.value = "";
        }
      }
      sel.addEventListener("change", toggle);
      toggle();
    }
    enableOther(deptGrp, "add-dept-input");
    enableOther(clubGrp, "add-club-input");
    enableOther(cenGrp,  "add-center-input");

    /* remove-button – hide card and tick DELETE */
    remBtn.addEventListener("click", () => {
      if (delBox) delBox.checked = true;
      card.style.display = "none";
    });
  }

  /* bind every existing card on initial page load */
  $$(".role-card", listBox).forEach(bindCard);

  /* “+ Add Role” button */
  addBtn.addEventListener("click", () => {
    /* prevent impatient click on Save until we finish */
    saveBtn.disabled = true;

    const idx = Number(totalForm().value);
    listBox.insertAdjacentHTML("beforeend", template.replace(/__prefix__/g, idx));
    bindCard($(`.role-card[data-form-index="${idx}"]`, listBox));
    totalForm().value = idx + 1;

    /* re-enable save after next paint */
    requestAnimationFrame(() => (saveBtn.disabled = false));
  });
});
