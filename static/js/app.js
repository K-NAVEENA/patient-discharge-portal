/**
 * Patient Discharge Planning Coordination Portal
 * Client-side utilities, notification polling, and interactive helpers.
 */

document.addEventListener('DOMContentLoaded', () => {
    // 1. Notification Poller
    const notifBadge = document.getElementById('navbar-notif-count');
    
    function pollNotifications() {
        if (!notifBadge) return;
        fetch('/notifications/api/unread')
            .then(res => {
                if (!res.ok) throw new Error('Not logged in or network error');
                return res.json();
            })
            .then(data => {
                if (data.unread_count > 0) {
                    notifBadge.textContent = data.unread_count;
                    notifBadge.style.display = 'inline-block';
                } else {
                    notifBadge.textContent = '0';
                    notifBadge.style.display = 'none';
                }
            })
            .catch(() => {
                // Silently ignore if logged out or paused
            });
    }

    // Poll every 25 seconds
    if (notifBadge) {
        setInterval(pollNotifications, 25000);
    }

    // 2. Dynamic Task Status Modal / Reason field handler
    const statusSelects = document.querySelectorAll('.task-status-select');
    statusSelects.forEach(select => {
        select.addEventListener('change', (e) => {
            const form = e.target.closest('form');
            if (!form) return;
            const blockedGroup = form.querySelector('.blocked-reason-group');
            if (blockedGroup) {
                if (e.target.value === 'Blocked') {
                    blockedGroup.style.display = 'block';
                    const textarea = blockedGroup.querySelector('textarea');
                    if (textarea) textarea.required = true;
                } else {
                    blockedGroup.style.display = 'none';
                    const textarea = blockedGroup.querySelector('textarea');
                    if (textarea) textarea.required = false;
                }
            }
        });
    });

    // 3. Confirm Final Discharge Action
    const finalDischargeForms = document.querySelectorAll('.confirm-final-discharge-form');
    finalDischargeForms.forEach(form => {
        form.addEventListener('submit', (e) => {
            const confirmed = confirm(
                "Are you sure you want to finalize this patient's discharge? This will update the admission record, release the hospital room, and finalize the discharge ledger."
            );
            if (!confirmed) {
                e.preventDefault();
            }
        });
    });

    // 4. Dismiss Alerts
    const alertCloses = document.querySelectorAll('.alert-close');
    alertCloses.forEach(btn => {
        btn.addEventListener('click', () => {
            const alert = btn.closest('.alert');
            if (alert) alert.remove();
        });
    });
});
