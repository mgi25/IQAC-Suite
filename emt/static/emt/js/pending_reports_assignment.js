// Assignment Modal Functionality for Pending Reports
document.addEventListener('DOMContentLoaded', function() {
    const modal = document.getElementById('assignModal');
    const modalClose = document.querySelector('.assign-modal-close');
    const cancelBtn = document.getElementById('cancelAssignBtn');
    const confirmBtn = document.getElementById('confirmAssignBtn');
    const unassignBtn = document.getElementById('unassignBtn');
    const searchInput = document.getElementById('participantSearch');
    const participantsList = document.getElementById('participantsList');
    const selectedParticipantDiv = document.getElementById('selectedParticipant');
    const eventTitleDiv = document.getElementById('assignEventTitle');
    
    let currentProposalId = null;
    let selectedParticipant = null;
    let searchTimeout = null;

    // Open modal when assign button is clicked
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('iqac-assign-btn')) {
            const proposalId = e.target.dataset.proposalId;
            const eventTitle = e.target.dataset.eventTitle;
            openAssignModal(proposalId, eventTitle);
        }
    });

    function openAssignModal(proposalId, eventTitle) {
        currentProposalId = proposalId;
        eventTitleDiv.textContent = `Event: ${eventTitle}`;
        
        // Reset modal state
        searchInput.value = '';
        participantsList.innerHTML = '';
        selectedParticipant = null;
        updateSelectedParticipant();
        confirmBtn.disabled = true;
        
        // Check if already assigned
        checkCurrentAssignment(proposalId);
        
        // Load participants
        loadParticipants(proposalId, '');
        
        // Show modal
        modal.style.display = 'flex';
        searchInput.focus();
    }

    function checkCurrentAssignment(proposalId) {
        // Find the row for this proposal to check assignment status
        const assignBtn = document.querySelector(`[data-proposal-id="${proposalId}"]`);
        const statusCell = assignBtn.closest('tr').querySelector('.iqac-td-status .iqac-status-badge');
        
        if (statusCell.classList.contains('assigned')) {
            unassignBtn.style.display = 'inline-block';
        } else {
            unassignBtn.style.display = 'none';
        }
    }

    function loadParticipants(proposalId, query) {
        const url = `/suite/api/event-participants/${proposalId}/?q=${encodeURIComponent(query)}`;
        
        fetch(url)
            .then(response => response.json())
            .then(data => {
                if (data.participants) {
                    displayParticipants(data.participants);
                } else {
                    participantsList.innerHTML = '<div class="error-message">Failed to load participants</div>';
                }
            })
            .catch(error => {
                console.error('Error loading participants:', error);
                participantsList.innerHTML = '<div class="error-message">Error loading participants</div>';
            });
    }

    function displayParticipants(participants) {
        if (participants.length === 0) {
            participantsList.innerHTML = '<div class="no-participants">No participants found</div>';
            return;
        }

        const html = participants.map(participant => `
            <div class="participant-card" data-participant-id="${participant.id}">
                <div class="participant-info">
                    <span class="participant-name">${participant.name}</span>
                    <span class="participant-role">${participant.role}</span>
                    <span class="participant-email">${participant.email}</span>
                </div>
                <button class="btn-select-participant" data-participant='${JSON.stringify(participant)}'>
                    Select
                </button>
            </div>
        `).join('');

        participantsList.innerHTML = html;

        // Add click handlers for select buttons
        participantsList.addEventListener('click', function(e) {
            if (e.target.classList.contains('btn-select-participant')) {
                const participantData = JSON.parse(e.target.dataset.participant);
                selectParticipant(participantData);
            }
        });
    }

    function selectParticipant(participant) {
        selectedParticipant = participant;
        updateSelectedParticipant();
        confirmBtn.disabled = false;
        
        // Visual feedback
        document.querySelectorAll('.participant-card').forEach(card => {
            card.classList.remove('selected');
        });
        document.querySelector(`[data-participant-id="${participant.id}"]`).classList.add('selected');
    }

    function updateSelectedParticipant() {
        if (selectedParticipant) {
            document.getElementById('selectedName').textContent = selectedParticipant.name;
            document.getElementById('selectedRole').textContent = selectedParticipant.role;
            document.getElementById('selectedEmail').textContent = selectedParticipant.email;
            selectedParticipantDiv.style.display = 'block';
        } else {
            selectedParticipantDiv.style.display = 'none';
        }
    }

    // Search functionality
    searchInput.addEventListener('input', function() {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            loadParticipants(currentProposalId, this.value);
        }, 300);
    });

    // Confirm assignment
    confirmBtn.addEventListener('click', function() {
        if (!selectedParticipant || !currentProposalId) return;

        confirmBtn.disabled = true;
        confirmBtn.textContent = 'Assigning...';

        const url = `/suite/api/assign-report/${currentProposalId}/`;
        
        fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify({
                assigned_user_id: selectedParticipant.id
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                updateUIAfterAssignment(selectedParticipant);
                closeModal();
                showSuccessMessage(`Report generation assigned to ${selectedParticipant.name}`);
            } else {
                showErrorMessage(data.error || 'Failed to assign task');
            }
        })
        .catch(error => {
            console.error('Error assigning task:', error);
            showErrorMessage('Network error while assigning task');
        })
        .finally(() => {
            confirmBtn.disabled = false;
            confirmBtn.textContent = 'Confirm Assignment';
        });
    });

    // Unassign functionality
    unassignBtn.addEventListener('click', function() {
        if (!currentProposalId) return;

        unassignBtn.disabled = true;
        unassignBtn.textContent = 'Removing...';

        const url = `/suite/api/unassign-report/${currentProposalId}/`;
        
        fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                updateUIAfterUnassignment();
                closeModal();
                showSuccessMessage('Assignment removed successfully');
            } else {
                showErrorMessage(data.error || 'Failed to remove assignment');
            }
        })
        .catch(error => {
            console.error('Error removing assignment:', error);
            showErrorMessage('Network error while removing assignment');
        })
        .finally(() => {
            unassignBtn.disabled = false;
            unassignBtn.textContent = 'Remove Assignment';
        });
    });

    function updateUIAfterAssignment(participant) {
        const assignBtn = document.querySelector(`[data-proposal-id="${currentProposalId}"]`);
        const statusCell = assignBtn.closest('tr').querySelector('.iqac-td-status .iqac-status-badge');
        
        // Update status
        statusCell.textContent = `Assigned to ${participant.name}`;
        statusCell.classList.add('assigned');
        
        // Update button text
        assignBtn.textContent = 'Reassign';
    }

    function updateUIAfterUnassignment() {
        const assignBtn = document.querySelector(`[data-proposal-id="${currentProposalId}"]`);
        const statusCell = assignBtn.closest('tr').querySelector('.iqac-td-status .iqac-status-badge');
        
        // Update status
        statusCell.textContent = 'Submitted by you';
        statusCell.classList.remove('assigned');
        
        // Update button text
        assignBtn.textContent = 'Assign to';
    }

    function closeModal() {
        modal.style.display = 'none';
        currentProposalId = null;
        selectedParticipant = null;
    }

    // Modal close handlers
    modalClose.addEventListener('click', closeModal);
    cancelBtn.addEventListener('click', closeModal);
    
    // Close modal when clicking outside
    modal.addEventListener('click', function(e) {
        if (e.target === modal) {
            closeModal();
        }
    });

    // Utility functions
    function getCsrfToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || 
               document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
    }

    function showSuccessMessage(message) {
        // You can implement a toast notification system here
        alert(message); // Simple fallback
    }

    function showErrorMessage(message) {
        // You can implement a toast notification system here
        alert('Error: ' + message); // Simple fallback
    }
});
