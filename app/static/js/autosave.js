// app/static/js/autosave.js
document.addEventListener('DOMContentLoaded', function () {
    const goalForm = document.getElementById('goalForm');
    const goalsContainer = document.getElementById('goalsContainer');

    // ========================================
    // 1. ADD NEW GOAL
    // ========================================
    if (goalForm) {
        goalForm.addEventListener('submit', function (e) {
            e.preventDefault();
            const formData = new FormData(this);

            fetch('/goals', {
                method: 'POST',
                body: formData
            })
            .then(res => res.json())
            .then(data => {
                if (data.status === 'success') {
                    showToast('Goal added successfully!', 'success');
                    location.reload();
                } else {
                    showToast('Error saving goal.', 'danger');
                }
            })
            .catch(err => {
                console.error('Goal save error:', err);
                showToast('Network error. Try again.', 'danger');
            });
        });
    }

    // ========================================
    // 2. ADD STEP
    // ========================================
    goalsContainer.addEventListener('click', function (e) {
        if (e.target.classList.contains('add-step')) {
            console.log('ADD STEP BUTTON CLICKED!'); // ← DEBUG LOG

            const card = e.target.closest('[data-goal-id]');
            if (!card) return;

            const goalId = card.dataset.goalId;
            const titleInput = card.querySelector('.new-step');
            const dateInput = card.querySelector('.date-input');
            const typeSelect = card.querySelector('.type-select');

            const title = titleInput.value.trim();
            const due_date = dateInput.value || null;
            const selected_type = typeSelect.value;

            if (!title) {
                showToast('Step title is required.', 'warning');
                titleInput.focus();
                return;
            }

            // Determine final step type
            let step_type = 'day';
            if (selected_type !== 'auto') {
                step_type = selected_type;
            } else if (due_date) {
                const date = new Date(due_date);
                const day = date.getDate();
                const month = date.getMonth() + 1;
                const weekday = date.getDay();

                if (day === 1 && [1, 4, 7, 10].includes(month)) {
                    step_type = 'quarter';
                } else if (day === 1) {
                    step_type = 'month';
                } else if (weekday === 1) {
                    step_type = 'week';
                }
            }

            fetch(`/api/goal/${goalId}/step`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title, due_date, step_type })
            })
            .then(res => {
                if (!res.ok) {
                    return res.json().then(err => { throw err; });
                }
                return res.json();
            })
            .then(data => {
                if (data.status === 'success') {
                    showToast(`Step added: ${data.step_type.toUpperCase()}`, 'success');
                    titleInput.value = '';
                    dateInput.value = '';
                    typeSelect.value = 'auto';
                    setTimeout(() => location.reload(), 300);
                }
            })
            .catch(err => {
                console.error('Step add failed:', err);
                showToast(err.message || 'Failed to add step.', 'danger');
            });
        }
    });

    // ========================================
    // 3. TOGGLE STEP
    // ========================================
    goalsContainer.addEventListener('change', function (e) {
        if (e.target.classList.contains('step-checkbox')) {
            const stepId = e.target.closest('.step-item').dataset.stepId;
            const card = e.target.closest('[data-goal-id]');
            const progressBar = card.querySelector('.progress-bar');

            fetch(`/api/step/${stepId}/toggle`, { method: 'POST' })
                .then(res => res.json())
                .then(data => {
                    progressBar.style.width = data.progress + '%';
                    progressBar.textContent = data.progress + '%';

                    const label = e.target.closest('.form-check').querySelector('.form-check-label');
                    if (data.completed) {
                        label.classList.add('text-decoration-line-through', 'text-muted');
                    } else {
                        label.classList.remove('text-decoration-line-through', 'text-muted');
                    }

                    showToast(data.completed ? 'Step completed!' : 'Step reopened!', 'info');
                })
                .catch(err => {
                    console.error('Toggle error:', err);
                    e.target.checked = !e.target.checked;
                    showToast('Failed to update step.', 'danger');
                });
        }
    });

    // ========================================
    // 4. AUTO-FILL TYPE ON DATE CHANGE
    // ========================================
    goalsContainer.addEventListener('change', function (e) {
        if (e.target.classList.contains('date-input')) {
            const dateInput = e.target;
            const typeSelect = dateInput.closest('.input-group').querySelector('.type-select');
            if (typeSelect.value !== 'auto') return;

            const dateStr = dateInput.value;
            if (!dateStr) {
                typeSelect.value = 'auto';
                return;
            }

            const date = new Date(dateStr);
            const day = date.getDate();
            const month = date.getMonth() + 1;
            const weekday = date.getDay();

            let detected = 'day';
            if (day === 1 && [1, 4, 7, 10].includes(month)) detected = 'quarter';
            else if (day === 1) detected = 'month';
            else if (weekday === 1) detected = 'week';

            typeSelect.value = detected;
        }
    });

    // ========================================
    // 5. ENTER KEY SUPPORT
    // ========================================
    goalsContainer.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' && e.target.classList.contains('new-step')) {
            e.preventDefault();
            const addButton = e.target.closest('.input-group').querySelector('.add-step');
            if (addButton) addButton.click();
        }
    });

    // ========================================
    // 6. TOAST FUNCTION
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

    // ========================================
    // DELETE GOAL
    // ========================================
    goalsContainer.addEventListener('click', function (e) {
        if (e.target.classList.contains('delete-goal')) {
            const card = e.target.closest('[data-goal-id]');
            const goalId = card.dataset.goalId;
            if (!confirm('Delete this goal and all steps?')) return;

            fetch(`/api/goal/${goalId}`, { method: 'DELETE' })
                .then(res => res.json())
                .then(() => {
                    showToast('Goal deleted!', 'danger');
                    card.remove();
                })
                .catch(() => showToast('Failed to delete goal.', 'danger'));
        }
    });

    // ========================================
    // EDIT GOAL
    // ========================================
    goalsContainer.addEventListener('click', function (e) {
        if (e.target.classList.contains('edit-goal')) {
            const card = e.target.closest('[data-goal-id]');
            const goalId = card.dataset.goalId;
            const titleSpan = card.querySelector('.goal-title');
            const currentTitle = titleSpan.textContent.trim();

            const newTitle = prompt('Edit goal title:', currentTitle);
            if (!newTitle || newTitle === currentTitle) return;

            fetch(`/api/goal/${goalId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title: newTitle })
            })
            .then(() => {
                titleSpan.textContent = newTitle;
                showToast('Goal updated!', 'success');
            })
            .catch(() => showToast('Failed to update.', 'danger'));
        }
    });

    // ========================================
    // DELETE STEP — FIXED!
    // ========================================
    goalsContainer.addEventListener('click', function (e) {
        if (e.target.classList.contains('delete-step')) {
            const stepItem = e.target.closest('.step-item');
            const stepId = stepItem.dataset.stepId;
            const card = stepItem.closest('[data-goal-id]');

            if (!confirm('Delete this step?')) return;

            fetch(`/api/step/${stepId}`, { 
                method: 'DELETE' 
            })
            .then(res => {
                if (!res.ok) {
                    // Only throw if server error
                    return res.json().then(err => { throw err; });
                }
                return res.json();
            })
            .then(data => {
                showToast('Step deleted!', 'danger');
                stepItem.remove();
                updateProgress(card);
            })
            .catch(err => {
                console.error('Delete error:', err);
                showToast(err.message || 'Failed to delete step.', 'danger');
            });
        }
    });

    // ========================================
    // EDIT STEP
    // ========================================
    goalsContainer.addEventListener('click', function (e) {
        if (e.target.classList.contains('edit-step')) {
            const stepItem = e.target.closest('.step-item');
            const stepId = stepItem.dataset.stepId;
            const titleSpan = stepItem.querySelector('.step-title');
            const currentTitle = titleSpan.textContent.trim();

            const newTitle = prompt('Edit step:', currentTitle);
            if (!newTitle || newTitle === currentTitle) return;

            fetch(`/api/step/${stepId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title: newTitle })
            })
            .then(() => {
                titleSpan.textContent = newTitle;
                showToast('Step updated!', 'success');
            })
            .catch(() => showToast('Failed to update.', 'danger'));
        }
    });

    // ========================================
    // UPDATE PROGRESS AFTER STEP DELETE
    // ========================================
    function updateProgress(card) {
        // Simple: Reload to recalculate nested progress & progress bars
        setTimeout(() => location.reload(), 300);
    }

    console.log('AUTOSAVE.JS LOADED — READY TO DOMINATE!');

});