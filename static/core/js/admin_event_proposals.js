function showProposalModal(id) {
    // AJAX: fetch details from backend (or pass context)
    fetch('/core-admin/event-proposal/' + id + '/json/')
    .then(response => response.json())
    .then(data => {
        document.getElementById("modal-title").innerText = data.title;
        document.getElementById("modal-details").innerHTML = `
            <b>Description:</b> ${data.description}<br>
            <b>Department:</b> ${data.department || "-"}<br>
            <b>User Type:</b> ${data.user_type}<br>
            <b>Status:</b> ${data.status_display}<br>
            <b>Date Submitted:</b> ${data.date_submitted}<br>
            <b>Submitted By:</b> ${data.submitted_by}
        `;
        document.getElementById("proposalModal").style.display = "flex";
    });
}
function hideProposalModal() {
    document.getElementById("proposalModal").style.display = "none";
}
window.onclick = function(event) {
    if (event.target == document.getElementById("proposalModal")) {
        hideProposalModal();
    }
}

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
