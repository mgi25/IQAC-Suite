const modal = document.getElementById("proposalModal");
const modalTitle = document.getElementById("modal-title");
const modalDetails = document.getElementById("modal-details");

const escapeHTML = (value) => {
    if (value === null || value === undefined) {
        return "";
    }
    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
};

const formatValue = (value, options = {}) => {
    const { preserveBreaks = false } = options;
    if (value === null || value === undefined || value === "") {
        return "—";
    }
    const safe = escapeHTML(value);
    return preserveBreaks ? safe.replace(/\n/g, "<br>") : safe;
};

const renderDetailRows = (rows) => rows
    .map(({ label, value }) => `
        <div class="detail-row">
            <span class="detail-label">${label}</span>
            <span class="detail-value">${value}</span>
        </div>
    `)
    .join("");

window.showProposalModal = (id) => {
    if (!modal || !modalDetails || !modalTitle) {
        return;
    }

    modal.classList.add("is-visible");
    modal.setAttribute("aria-hidden", "false");
    document.body.classList.add("modal-open");

    modalTitle.textContent = "Loading…";
    modalDetails.innerHTML = renderDetailRows([
        { label: "Please wait", value: "Fetching proposal details…" }
    ]);

    fetch(`/core-admin/event-proposal/${id}/json/`)
        .then((response) => {
            if (!response.ok) {
                throw new Error("Failed to fetch proposal details");
            }
            return response.json();
        })
        .then((data) => {
            const submittedAt = data.date_submitted || "";
            let dateOnly = submittedAt;
            let timeOnly = "";

            if (submittedAt.includes(" ")) {
                const parts = submittedAt.split(" ");
                dateOnly = parts[0];
                timeOnly = parts[1]?.slice(0, 5) || "";
            }

            modalTitle.textContent = data.title || "Event Proposal";

            const rows = [
                { label: "Description", value: formatValue(data.description, { preserveBreaks: true }) },
                { label: "Organization", value: formatValue(data.organization) },
                { label: "User Type", value: formatValue(data.user_type) },
                { label: "Status", value: formatValue(data.status_display) },
                { label: "Date Submitted", value: formatValue(dateOnly) },
                { label: "Time Submitted", value: formatValue(timeOnly) },
                { label: "Submitted By", value: formatValue(data.submitted_by) },
            ];

            modalDetails.innerHTML = renderDetailRows(rows);

            const closeButton = modal.querySelector(".modal-close");
            if (closeButton && typeof closeButton.focus === "function") {
                try {
                    closeButton.focus({ preventScroll: true });
                } catch (err) {
                    closeButton.focus();
                }
            }
        })
        .catch((error) => {
            modalTitle.textContent = "Unable to load";
            modalDetails.innerHTML = renderDetailRows([
                { label: "Error", value: formatValue(error.message || "Something went wrong.") },
            ]);
        });
};

window.hideProposalModal = () => {
    if (!modal) {
        return;
    }

    modal.classList.remove("is-visible");
    modal.setAttribute("aria-hidden", "true");
    document.body.classList.remove("modal-open");
};

if (modal) {
    modal.addEventListener("click", (event) => {
        if (event.target === modal) {
            window.hideProposalModal();
        }
    });
}

document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && modal && modal.classList.contains("is-visible")) {
        window.hideProposalModal();
    }
});

function handleAction(proposalId, action) {
    let comment = "";
    if (action === "returned" || action === "rejected") {
        comment = prompt("Add a comment for this action (optional):");
        if (action === "rejected" && !confirm("Are you sure you want to reject this proposal?")) return;
    }
    fetch(`/core-admin/event-proposal/${proposalId}/action/`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": window.CSRF_TOKEN },
        body: JSON.stringify({ action, comment })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            window.location.reload();
        } else {
            alert(data.error || "Action failed.");
        }
    });
}

document.addEventListener("DOMContentLoaded", () => {
    const table = document.querySelector(".proposals-table");
    if (table) {
        table.classList.add("fade-in");
    }
});
