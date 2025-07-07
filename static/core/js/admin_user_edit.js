// static/core/js/admin_user_edit.js

document.addEventListener("DOMContentLoaded", () => {
  const $  = (sel, ctx = document) => ctx.querySelector(sel);
  const $$ = (sel, ctx = document) => [...ctx.querySelectorAll(sel)];

  const listBox     = $("#roles-list-container");
  const addBtn      = $("#add-role-btn");
  const tplHTML     = $("#role-card-template").innerHTML;
  const totalInput  = $('input[name$="-TOTAL_FORMS"]');
  const saveBtn     = $("#user-edit-form button[type=submit]");

  // Roles which require each org field
  const ORG_RULES = {
    department : ["hod", "faculty", "dept_iqac", "student", "dean", "director", "academic_coordinator"],
    club       : ["club_head"],
    center     : ["center_head"],
    cell       : ["cell_head"],
    association:["association_head"]
  };

  // Show/hide logic per role
  function bindCard(card) {
    const roleSel = $("select[name$='-role']", card);
    const groups = {
      department : $(".dept-group",        card),
      club       : $(".club-group",        card),
      center     : $(".center-group",      card),
      cell       : $(".cell-group",        card),
      association: $(".association-group", card),
    };
    const delBox = $("input[name$='-DELETE']", card);
    const remBtn = $(".remove-role-btn", card);

    // Always add 'Other…' to selects
    Object.values(groups).forEach(grp => {
      const sel = $("select", grp);
      if (sel && ![...sel.options].some(o => o.value === "other")) {
        sel.add(new Option("Other…", "other"));
      }
    });

    // Show only the needed org pickers for the role
    function syncPanels() {
      const r = (roleSel.value || "").toLowerCase();
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

    // Remove role logic
    remBtn?.addEventListener("click", () => {
      if (delBox) delBox.checked = true;
      card.style.display = "none";
    });
  }

  // Bind all existing role-cards
  $$(".role-card", listBox).forEach(bindCard);

  // Add role-card dynamically
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
