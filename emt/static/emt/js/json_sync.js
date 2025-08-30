document.addEventListener("DOMContentLoaded", function () {
    // --- FIELD MAPPING (modern UI ↔ hidden Django fields) ---
    const fieldMap = {
        "event-title-modern": "event_title",
        "target-audience-modern": "target_audience",
        "event-focus-type-modern": "event_focus_type",
        "venue-modern": "venue",
        "event-start-date": "event_start_date",
        "event-end-date": "event_end_date",
        "academic-year-modern": "academic_year",
        "pos-pso-modern": "pos_pso",
        "sdg-goals-modern": "sdg_goals",
        "num-activities-modern": "num_activities",
        "student-coordinators-modern": "student_coordinators",
        "faculty-select": "faculty_incharges",
        "committees-collaborations-modern": "committees_collaborations",
        "id_need_analysis": "need_analysis",
        "id_objectives": "objectives",
        "id_learning_outcomes": "outcomes",
        "id_flow": "flow"
    };

    // --- SYNC MODERN ↔ HIDDEN ---
    Object.entries(fieldMap).forEach(([modernId, djangoName]) => {
        const modernEl = document.getElementById(modernId);
        const hiddenEl = document.querySelector(`[name="${djangoName}"]`);
        if (modernEl && hiddenEl) {
            modernEl.addEventListener("input", () => hiddenEl.value = modernEl.value);
            hiddenEl.addEventListener("input", () => modernEl.value = hiddenEl.value);
        }
    });

    // --- JSON EXPORT ---
    document.getElementById("download-json-btn")?.addEventListener("click", function () {
        const form = document.getElementById("proposal-form");
        const data = {
            basic_info: {},
            why_this_event: {},
            schedule: [],
            speakers: [],
            expenses: [],
            income: [],
            cdl_support: {}
        };

        // Basic Info + Why This Event
        form.querySelectorAll("input[name], select[name], textarea[name]").forEach(el => {
            if (!el.name) return;
            if (["need_analysis", "objectives", "outcomes", "flow"].includes(el.name)) {
                data.why_this_event[el.name] = el.value;
            } else {
                data.basic_info[el.name] = el.value;
            }
        });

        // Schedule (activities)
        document.querySelectorAll("#dynamic-activities-section .activity-item").forEach(act => {
            data.schedule.push({
                title: act.querySelector("input[name*='title']")?.value || "",
                description: act.querySelector("textarea[name*='description']")?.value || "",
                start_time: act.querySelector("input[name*='start_time']")?.value || "",
                end_time: act.querySelector("input[name*='end_time']")?.value || ""
            });
        });

        // Speakers
        document.querySelectorAll(".speaker-item").forEach(sp => {
            data.speakers.push({
                name: sp.querySelector("input[name*='name']")?.value || "",
                designation: sp.querySelector("input[name*='designation']")?.value || "",
                bio: sp.querySelector("textarea[name*='bio']")?.value || "",
                linkedin: sp.querySelector("input[name*='linkedin']")?.value || ""
            });
        });

        // Expenses
        document.querySelectorAll(".expense-item").forEach(ex => {
            data.expenses.push({
                item_name: ex.querySelector("input[name*='item_name']")?.value || "",
                amount: ex.querySelector("input[name*='amount']")?.value || "",
                funding_source: ex.querySelector("input[name*='funding_source']")?.value || "",
                justification: ex.querySelector("textarea[name*='justification']")?.value || ""
            });
        });

        // Income
        document.querySelectorAll(".income-item").forEach(inc => {
            data.income.push({
                source: inc.querySelector("input[name*='source']")?.value || "",
                amount: inc.querySelector("input[name*='amount']")?.value || ""
            });
        });

        // CDL Support
        data.cdl_support = {
            poster: document.querySelector("input[name='poster']")?.value || "",
            certificate_template: document.querySelector("input[name='certificate_template']")?.value || "",
            other_files: Array.from(document.querySelectorAll("input[name='other_files']")).map(f => f.value)
        };

        // Download
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
        const link = document.createElement("a");
        link.href = URL.createObjectURL(blob);
        link.download = "event_proposal.json";
        link.click();
    });

    // --- JSON IMPORT ---
    document.getElementById("upload-json-input")?.addEventListener("change", function (event) {
        const file = event.target.files[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = function (e) {
            try {
                const data = JSON.parse(e.target.result);
                const form = document.getElementById("proposal-form");

                // Basic Info
                for (const [name, value] of Object.entries(data.basic_info || {})) {
                    const el = form.querySelector(`[name="${name}"]`);
                    if (el) {
                        el.value = value;
                        el.dispatchEvent(new Event("input"));
                    }
                }

                // Why This Event
                for (const [name, value] of Object.entries(data.why_this_event || {})) {
                    const el = form.querySelector(`[name="${name}"]`);
                    if (el) {
                        el.value = value;
                        el.dispatchEvent(new Event("input"));
                    }
                }

                // Schedule (activities)
                if (Array.isArray(data.schedule)) {
                    document.querySelectorAll(".activity-item").forEach(e => e.remove());
                    data.schedule.forEach(act => {
                        if (typeof addActivity === "function") addActivity(); // your existing function
                        const last = document.querySelector(".activity-item:last-child");
                        if (last) {
                            last.querySelector("input[name*='title']").value = act.title || "";
                            last.querySelector("textarea[name*='description']").value = act.description || "";
                            last.querySelector("input[name*='start_time']").value = act.start_time || "";
                            last.querySelector("input[name*='end_time']").value = act.end_time || "";
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
                            last.querySelector("input[name*='funding_source']").value = ex.funding_source || "";
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

                // CDL Support (basic prefill only)
                if (data.cdl_support) {
                    const poster = document.querySelector("input[name='poster']");
                    const cert = document.querySelector("input[name='certificate_template']");
                    if (poster) poster.value = data.cdl_support.poster || "";
                    if (cert) cert.value = data.cdl_support.certificate_template || "";
                }

                alert("Form successfully filled from JSON!");
            } catch (err) {
                alert("Invalid JSON file");
            }
        };
        reader.readAsText(file);
    });
});
