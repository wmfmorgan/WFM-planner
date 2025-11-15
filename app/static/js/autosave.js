// app/static/js/autosave.js — FULL HIERARCHY + DAILY + PERSISTENCE
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

            fetch(`/api/goals/${parentId}/subgoal`, {
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

            fetch(`/api/goals/${goalId}/toggle`, { method: 'POST' })
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

            fetch(`/api/goals/${goalId}`, {
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

            fetch(`/api/goals/${goalId}`, { method: 'DELETE' })
                .then(() => {
                    showToast('Goal deleted!', 'danger');
                    card.remove();
                })
                .catch(() => showToast('Failed to delete.', 'danger'));
        }
    });

    // ========================================
    // 5. AUTOSAVE ALL INPUTS (TEXT, CHECKBOX)
    // ========================================
    document.addEventListener('input', function (e) {
        if (e.target.dataset.key) {
            localStorage.setItem(e.target.dataset.key, e.target.value);
        }
    });

    document.addEventListener('change', function (e) {
        if (e.target.type === 'checkbox' && e.target.dataset.key) {
            localStorage.setItem(e.target.dataset.key, e.target.checked);
        }
    });

    // ========================================
    // 6. LOAD ALL SAVED DATA ON EVERY PAGE LOAD
    // ========================================
    function loadAllSavedData() {
        document.querySelectorAll('[data-key]').forEach(el => {
            const key = el.dataset.key;
            if (key) {
                const saved = localStorage.getItem(key);
                if (saved !== null) {
                    if (el.type === 'checkbox') {
                        el.checked = saved === 'true';
                    } else {
                        el.value = saved;
                    }
                }
            }
        });
    }

    // RUN ON EVERY PAGE LOAD
    loadAllSavedData();

    // ALSO RUN ON DOMCONTENTLOADED (FOR SPAs)
    document.addEventListener('DOMContentLoaded', loadAllSavedData);

    // ========================================
    // 7. TOAST NOTIFICATIONS
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

document.querySelectorAll('.autosave').forEach(textarea => {
    const scope = textarea.dataset.scope;
    const year = textarea.dataset.year;
    const quarter = textarea.dataset.quarter;
    const month = textarea.dataset.month;
    const week = textarea.dataset.week;
    const day = textarea.dataset.day;
    const type = textarea.dataset.type;
    const time = textarea.dataset.time;      // ← NEW: 14:00
    const index = textarea.dataset.index;
    
    
    // BUILD KEY TO MATCH API PARSING
    const parts = ['note', scope, year];
    if (quarter) parts.push(quarter);
    if (month) parts.push(month);
    if (week) parts.push(week);
    if (day) parts.push(day);
    parts.push(type);
    if (time) parts.push(time);           // ← ADD time
    if (index !== undefined) parts.push(index);  // ← ADD index
    const key = parts.join('-');

    // LOAD
    fetch(`/api/note/${key}`)
        .then(r => r.json())
        .then(data => textarea.value = data.content || '')
        .catch(() => {});

    // SAVE
    textarea.addEventListener('input', function() {
        fetch(`/api/note/${key}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content: this.value })
        });
    });
});


// TASK COMPLETION
document.querySelectorAll('.task-complete').forEach(checkbox => {
    const scope = checkbox.dataset.scope;
    const year = checkbox.dataset.year;
    const month = checkbox.dataset.month;
    const day = checkbox.dataset.day;
    const index = checkbox.dataset.index;
    const type = checkbox.dataset.type;

    const key = `note-${scope}-${year}-${month}-${day}-${type}-${index}`;

    // LOAD
    fetch(`/api/note/${key}`)
        .then(r => r.json())
        .then(data => checkbox.checked = data.completed || false)
        .catch(() => {});

    // SAVE
    checkbox.addEventListener('change', function() {
        fetch(`/api/note/${key}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ completed: this.checked })
        });
    });
});
});