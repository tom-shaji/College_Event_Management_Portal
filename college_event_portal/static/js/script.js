document.addEventListener('DOMContentLoaded', () => {
    // Auto-hide toasts after 4 seconds
    const toasts = document.querySelectorAll('.toast');
    toasts.forEach(toast => {
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(100%)';
            toast.style.transition = 'all 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    });

    // Modal Logic
    const modals = document.querySelectorAll('.modal-overlay');
    const modalTriggers = document.querySelectorAll('[data-modal-target]');
    const closeButtons = document.querySelectorAll('[data-close-modal]');

    modalTriggers.forEach(trigger => {
        trigger.addEventListener('click', () => {
            const targetId = trigger.getAttribute('data-modal-target');
            document.getElementById(targetId).classList.add('active');
        });
    });

    closeButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            btn.closest('.modal-overlay').classList.remove('active');
        });
    });

    // Close modal on outside click
    modals.forEach(modal => {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.classList.remove('active');
            }
        });
    });

    // Confirm form submissions (e.g. Delete, Cancel Registration)
    const confirmForms = document.querySelectorAll('.confirm-form');
    confirmForms.forEach(form => {
        form.addEventListener('submit', (e) => {
            const msg = form.getAttribute('data-confirm-msg') || 'Are you sure you want to proceed?';
            if (!confirm(msg)) {
                e.preventDefault();
            }
        });
    });
});

// Admin Edit Modal Data Population
function openEditModal(eventData) {
    document.getElementById('editModal').classList.add('active');
    
    // Set form action dynamically
    document.getElementById('editForm').action = `/admin/event/edit/${eventData.id}`;
    
    // Populate fields
    document.getElementById('edit_name').value = eventData.name;
    document.getElementById('edit_date').value = eventData.date;
    document.getElementById('edit_time').value = eventData.time;
    document.getElementById('edit_venue').value = eventData.venue;
    document.getElementById('edit_category').value = eventData.category;
    document.getElementById('edit_description').value = eventData.description;
    document.getElementById('edit_rules').value = eventData.rules;
    document.getElementById('edit_total_seats').value = eventData.total_seats;
    document.getElementById('edit_organizer').value = eventData.organizer;
}
