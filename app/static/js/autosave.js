// app/static/js/autosave.js — HIERARCHY + TEXT AUTOSAVE
document.addEventListener('DOMContentLoaded', function () {
    const goalsContainer = document.querySelector('.goals-container') || document.body;

    // ========================================
    // 1. ADD SUB-GOAL
    // ========================================
    goalsContainer.addEventListener('click', function (e) {
        if (e.target.classList.contains('add-subgoal')) {
            const parentId = e.target.dataset.parentId;
            const title = prompt('Sub-goal title:');
            if (!title) return;

            const dueInput = prompt('Due date (YYYY-MM-DD) - optional:');
            const due_date = dueInput || null;

            fetch(`/api/goal/${parentId}/subgoal`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title, due_date })
            })
            .then(res => {
                if (!res.ok) throw new Error('Network error');
                return res.json();
            })
            .then(() => {
                showToast('Sub-goal added!', 'success');
                setTimeout(() => location.reload(), 300);
            })
            .catch(err => {
                console.error('Add subgoal error:', err);
                showToast('Failed to add sub-goal.', 'danger');
            });
        }
    });

    // ========================================
    // 2. TOGGLE GOAL COMPLETION
    // ========================================
    goalsContainer.addEventListener('change', function (e) {
        if (e.target.classList.contains('complete-goal')) {
            const goalId = e.target.dataset.goalId;
            const card = e.target.closest('.goal-node') || e.target.closest('.goal-card');
            const progressBar = card.querySelector('.progress-bar');

            fetch(`/api/goal/${goalId}/toggle`, { method: 'POST' })
                .then(res => res.json())
                .then(data => {
                    progressBar.style.width = data.progress + '%';
                    showToast(data.completed ? 'Goal completed!' : 'Goal reopened!', 'info');
                })
                .catch(() => {
                    e.target.checked = !e.target.checked;
                    showToast('Failed to update.', 'danger');
                });
        }
    });

    // ========================================
    // 3. EDIT GOAL — EXPAND + INLINE FORM
    // ========================================
    goalsContainer.addEventListener('click', function (e) {
        if (e.target.classList.contains('edit-goal-btn')) {
            const card = e.target.closest('.goal-card');
            card.querySelector('.view-mode').classList.add('d-none');
            card.querySelector('.edit-mode').classList.remove('d-none');
        }
    });

    // Cancel Edit
    goalsContainer.addEventListener('click', function (e) {
        if (e.target.classList.contains('cancel-edit')) {
            const card = e.target.closest('.goal-card');
            card.querySelector('.view-mode').classList.remove('d-none');
            card.querySelector('.edit-mode').classList.add('d-none');
        }
    });

    // Save Edit
    goalsContainer.addEventListener('submit', function (e) {
        if (e.target.classList.contains('edit-goal-form')) {
            e.preventDefault();
            const form = e.target;
            const goalId = form.querySelector('[name="goal_id"]').value;
            const data = {
                title: form.querySelector('.goal-title-input').value,
                description: form.querySelector('.goal-description-input').value,
                motivation: form.querySelector('.goal-motivation-input').value,
                due_date: form.querySelector('.goal-due-date-input').value || null
            };

            fetch(`/api/goal/${goalId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            })
            .then(res => {
                if (!res.ok) throw new Error('Save failed');
                return res.json();
            })
            .then(() => {
                showToast('Goal saved!', 'success');
                setTimeout(() => location.reload(), 300);
            })
            .catch(() => {
                showToast('Failed to save.', 'danger');
            });
        }
    });

    // ========================================
    // 4. DELETE GOAL
    // ========================================
    goalsContainer.addEventListener('click', function (e) {
        if (e.target.classList.contains('delete-goal')) {
            const goalId = e.target.dataset.goalId;
            const card = e.target.closest('.goal-node') || e.target.closest('.goal-card');
            if (!confirm('Delete this goal and all sub-goals?')) return;

            fetch(`/api/goal/${goalId}`, { method: 'DELETE' })
                .then(() => {
                    showToast('Goal deleted!', 'danger');
                    card.remove();
                })
                .catch(() => showToast('Failed to delete.', 'danger'));
        }
    });

    // ========================================
    // 5. AUTOSAVE TEXTAREAS (PREP/NOTES/REVIEW)
    // ========================================
    document.addEventListener('input', function (e) {
        if (e.target.classList.contains('autosave-textarea')) {
            const key = e.target.dataset.key;
            if (key) {
                localStorage.setItem(key, e.target.value);
                console.log('Autosaved:', key);
            }
        }
    });

    // LOAD SAVED TEXT ON PAGE LOAD
    const textareas = document.querySelectorAll('.autosave-textarea');
    textareas.forEach(ta => {
        const key = ta.dataset.key;
        if (key) {
            const saved = localStorage.getItem(key);
            if (saved) {
                ta.value = saved;
                console.log('Loaded:', key);
            }
        }
    });

    // ========================================
    // 6. TOAST NOTIFICATIONS
    // ========================================
    function showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-white bg-${type} border-0 position-fixed`;
        toast.style.top = '1rem';
        toast.style.right = '1rem';
        toast.style.zIndex = '9999';
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">${message}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;
        document.body.appendChild(toast);
        const bsToast = new bootstrap.Toast(toast, { delay: 3000 });
        bsToast.show();
        toast.addEventListener('hidden.bs.toast', () => toast.remove());
    }

    console.log('AUTOSAVE.JS LOADED — READY TO DOMINATE!');
});