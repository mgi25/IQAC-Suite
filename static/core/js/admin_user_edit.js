// static/core/js/admin_user_edit.js

document.addEventListener("DOMContentLoaded", () => {
  const $  = (sel, ctx = document) => ctx.querySelector(sel);
  const $$ = (sel, ctx = document) => [...ctx.querySelectorAll(sel)];

  const listBox     = $("#roles-list-container");
  const addBtn      = $("#add-role-btn");
  const tplHTML     = $("#role-card-template").innerHTML;
  const totalInput  = $('input[name$="-TOTAL_FORMS"]');
  const saveBtn     = $("#user-edit-form button[type=submit]");

  const SINGLE_USER_ROLES = ["dean", "academic_coordinator", "director"];
  const CDL_ROLE = "cdl";
  const ORG_RULES = {
    department : ["hod", "faculty", "dept_iqac", "student"],
    club       : ["club_head"],
    center     : ["center_head"],
    cell       : ["cell_head"],
    association:["association_head"]
  };

  function bindCard(card) {
    const roleSel = $("select[name$='-role']", card);
    const groups = {
      department : $(".dept-group",        card),
      club       : $(".club-group",        card),
      center     : $(".center-group",      card),
      cell       : $(".cell-group",        card),
      association: $(".association-group", card),
    };
    const cdlRoleGrp = $(".cdl-role-group", card);
    const delBox = $("input[name$='-DELETE']", card);
    const remBtn = $(".remove-role-btn", card);

    Object.values(groups).forEach(grp => {
      const sel = $("select", grp);
      if (sel && ![...sel.options].some(o => o.value === "other")) {
        sel.add(new Option("Other…", "other"));
      }
    });

    function syncPanels() {
      const r = (roleSel.value || "").toLowerCase();

      // Hide all org groups and show CDL select for CDL
      if (r === CDL_ROLE) {
        Object.values(groups).forEach(grp => grp.style.display = "none");
        if (cdlRoleGrp) cdlRoleGrp.style.display = "block";
        return;
      }

      // Hide all org groups and CDL select for single-user roles
      if (SINGLE_USER_ROLES.includes(r)) {
        Object.values(groups).forEach(grp => grp.style.display = "none");
        if (cdlRoleGrp) cdlRoleGrp.style.display = "none";
        return;
      }

      // Default: Show/hide org pickers per role
      if (cdlRoleGrp) cdlRoleGrp.style.display = "none";
      Object.entries(groups).forEach(([key, grp]) => {
        grp.style.display = ORG_RULES[key].includes(r) ? "block" : "none";
      });
    }
    roleSel.addEventListener("change", syncPanels);
    syncPanels();

    // "Other..." field logic
    function enableOther(grp, txtCls) {
      const sel = $("select", grp);
      const txt = $("." + txtCls, grp);
      if (!sel || !txt) return;
      function toggle() {
        const custom = sel.value === "other";
        txt.style.display = custom ? "block" : "none";
        txt.required = custom;
        if (custom) {
          sel.value = "";
        } else {
          txt.value = "";
        }
      }
      sel.addEventListener("change", toggle);
      toggle();
    }
    enableOther(groups.department, "add-dept-input");
    enableOther(groups.club, "add-club-input");
    enableOther(groups.center, "add-center-input");
    enableOther(groups.cell, "add-cell-input");
    enableOther(groups.association, "add-association-input");

    remBtn?.addEventListener("click", () => {
      if (delBox) delBox.checked = true;
      card.style.display = "none";
    });
  }

  $$(".role-card", listBox).forEach(bindCard);

  addBtn.addEventListener("click", () => {
    saveBtn.disabled = true;
    const idx = +totalInput.value;
    listBox.insertAdjacentHTML(
      "beforeend",
      tplHTML.replace(/__prefix__/g, idx)
    );
    bindCard($(`.role-card[data-form-index="${idx}"]`));
    totalInput.value = idx + 1;
    requestAnimationFrame(() => (saveBtn.disabled = false));
  });
});
