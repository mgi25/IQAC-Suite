document.addEventListener("DOMContentLoaded", function () {
    const isProposalPage = document.getElementById("proposal-form") !== null;
    const isReportPage   = document.getElementById("report-form") !== null;

    // ========== DOWNLOAD JSON ==========
    document.getElementById("download-json-btn")?.addEventListener("click", function () {
        let data = {};

        if (isProposalPage) {
            const form = document.getElementById("proposal-form");
            data.basic_info = {};
            data.why_this_event = {};

            // Basic + Why This Event
            form.querySelectorAll("input[name], select[name], textarea[name]").forEach(el => {
                if (!el.name) return;
                if (["need_analysis", "objectives", "outcomes", "flow"].includes(el.name)) {
                    data.why_this_event[el.name] = el.value;
                } else {
                    data.basic_info[el.name] = el.value;
                }
            });

            // Activities
            data.activities = [];
            document.querySelectorAll(".activity-row").forEach(row => {
                data.activities.push({
                    name: row.querySelector("input[name^='activity_name']")?.value || "",
                    date: row.querySelector("input[name^='activity_date']")?.value || ""
                });
            });

            // Speakers
            data.speakers = [];
            document.querySelectorAll(".speaker-item").forEach(sp => {
                data.speakers.push({
                    name: sp.querySelector("input[name*='name']")?.value || "",
                    designation: sp.querySelector("input[name*='designation']")?.value || "",
                    bio: sp.querySelector("textarea[name*='bio']")?.value || "",
                    linkedin: sp.querySelector("input[name*='linkedin']")?.value || ""
                });
            });

            // Expenses
            data.expenses = [];
            document.querySelectorAll(".expense-item").forEach(ex => {
                data.expenses.push({
                    item_name: ex.querySelector("input[name*='item_name']")?.value || "",
                    amount: ex.querySelector("input[name*='amount']")?.value || "",
                    justification: ex.querySelector("textarea[name*='justification']")?.value || ""
                });
            });

            // Income
            data.income = [];
            document.querySelectorAll(".income-item").forEach(inc => {
                data.income.push({
                    source: inc.querySelector("input[name*='source']")?.value || "",
                    amount: inc.querySelector("input[name*='amount']")?.value || ""
                });
            });

            // CDL
            data.cdl_support = {
                poster: document.querySelector("input[name='poster']")?.value || "",
                certificate_template: document.querySelector("input[name='certificate_template']")?.value || ""
            };
        }

        if (isReportPage) {
            const form = document.getElementById("report-form");
            data.event_information = {};
            form.querySelectorAll("input[name], select[name], textarea[name]").forEach(el => {
                data.event_information[el.name] = el.value;
            });

            // Rich text areas
            data.event_summary  = form.querySelector("textarea[name='event_summary']")?.value || "";
            data.event_outcomes = form.querySelector("textarea[name='event_outcomes']")?.value || "";
            data.analysis       = form.querySelector("textarea[name='analysis']")?.value || "";
            data.relevance      = form.querySelector("textarea[name='relevance']")?.value || "";
        }

        // Download
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
        const link = document.createElement("a");
        link.href = URL.createObjectURL(blob);
        link.download = isProposalPage ? "event_proposal.json" : "event_report.json";
        link.click();
    });

    // ========== UPLOAD JSON ==========
    document.getElementById("upload-json-input")?.addEventListener("change", function (event) {
        const file = event.target.files[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = function (e) {
            try {
                const data = JSON.parse(e.target.result);

                // ----- Proposal Page -----
                if (isProposalPage) {
                    const form = document.getElementById("proposal-form");

                    // Basic Info
                    Object.entries(data.basic_info || {}).forEach(([name, val]) => {
                        const el = form.querySelector(`[name="${name}"]`);
                        if (el) {
                            el.value = val;
                            el.dispatchEvent(new Event("input"));
                        }
                    });

                    // Why This Event
                    Object.entries(data.why_this_event || {}).forEach(([name, val]) => {
                        const el = form.querySelector(`[name="${name}"]`);
                        if (el) {
                            el.value = val;
                            el.dispatchEvent(new Event("input"));
                        }
                    });

                    // Activities
                    if (Array.isArray(data.activities)) {
                        document.querySelectorAll(".activity-row").forEach(e => e.remove());
                        data.activities.forEach(act => {
                            if (typeof addActivity === "function") addActivity();
                            const last = document.querySelector(".activity-row:last-child");
                            if (last) {
                                last.querySelector("input[name^='activity_name']").value = act.name || "";
                                last.querySelector("input[name^='activity_date']").value = act.date || "";
                            }
                        });
                    }

                    // Speakers
                    if (Array.isArray(data.speakers)) {
                        document.querySelectorAll(".speaker-item").forEach(e => e.remove());
                        data.speakers.forEach(sp => {
                            if (typeof addSpeaker === "function") addSpeaker();
                            const last = document.querySelector(".speaker-item:last-child");
                            if (last) {
                                last.querySelector("input[name*='name']").value = sp.name || "";
                                last.querySelector("input[name*='designation']").value = sp.designation || "";
                                last.querySelector("textarea[name*='bio']").value = sp.bio || "";
                                last.querySelector("input[name*='linkedin']").value = sp.linkedin || "";
                            }
                        });
                    }

                    // Expenses
                    if (Array.isArray(data.expenses)) {
                        document.querySelectorAll(".expense-item").forEach(e => e.remove());
                        data.expenses.forEach(ex => {
                            if (typeof addExpense === "function") addExpense();
                            const last = document.querySelector(".expense-item:last-child");
                            if (last) {
                                last.querySelector("input[name*='item_name']").value = ex.item_name || "";
                                last.querySelector("input[name*='amount']").value = ex.amount || "";
                                last.querySelector("textarea[name*='justification']").value = ex.justification || "";
                            }
                        });
                    }

                    // Income
                    if (Array.isArray(data.income)) {
                        document.querySelectorAll(".income-item").forEach(e => e.remove());
                        data.income.forEach(inc => {
                            if (typeof addIncome === "function") addIncome();
                            const last = document.querySelector(".income-item:last-child");
                            if (last) {
                                last.querySelector("input[name*='source']").value = inc.source || "";
                                last.querySelector("input[name*='amount']").value = inc.amount || "";
                            }
                        });
                    }

                    // CDL
                    if (data.cdl_support) {
                        const poster = document.querySelector("input[name='poster']");
                        const cert   = document.querySelector("input[name='certificate_template']");
                        if (poster) poster.value = data.cdl_support.poster || "";
                        if (cert) cert.value = data.cdl_support.certificate_template || "";
                    }
                }

                // ----- Report Page -----
                if (isReportPage) {
                    const form = document.getElementById("report-form");

                    Object.entries(data.event_information || {}).forEach(([name, val]) => {
                        const el = form.querySelector(`[name="${name}"]`);
                        if (el) {
                            el.value = val;
                            el.dispatchEvent(new Event("input"));
                        }
                    });

                    ["event_summary", "event_outcomes", "analysis", "relevance"].forEach(field => {
                        const el = form.querySelector(`[name="${field}"]`);
                        if (el) el.value = data[field] || "";
                    });
                }

                alert("Form successfully filled from JSON!");
            } catch {
                alert("Invalid JSON file");
            }
        };
        reader.readAsText(file);
    });
});
