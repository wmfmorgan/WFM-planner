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
                    showToast('Goal added! SMASH!', 'success');
                    location.reload();
                } else {
                    showToast('Error saving goal!', 'danger');
                }
            })
            .catch(err => {
                console.error('Goal save error:', err);
                showToast('Network error. Check connection!', 'danger');
            });
        });
    }

    // ========================================
    // 2. ADD STEP WITH TYPE + DATE LOGIC
    // ========================================
    goalsContainer.addEventListener('click', function (e) {
        if (e.target.classList.contains('add-step')) {
            const card = e.target.closest('[data-goal-id']);
            if (!card) return;

            const goalId = card.dataset.goalId;
            const titleInput = card.querySelector('.new-step');
            const dateInput = card.querySelector('.date-input');
            const typeSelect = card.querySelector('.type-select');

            const title = titleInput.value.trim();
            const due_date = dateInput.value || null;
            const selected_type = typeSelect.value;

            if (!title) {
                showToast('Step title required!', 'warning');
                titleInput.focus();
                return;
            }

            // === DETERMINE FINAL STEP TYPE ===
            let step_type = 'day';
            if (selected_type !== 'auto' && selected_type) {
                step_type = selected_type;
            } else if (due_date) {
                // Auto-detect from date
                const date = new Date(due_date);
                const day = date.getDate();
                const month = date.getMonth() + 1;  // JS months are 0-indexed
                const weekday = date.getDay();      // 0=Sun, 1=Mon

                if (day === 1 && [1, 4, 7, 10].includes(month)) {
                    step_type = 'quarter';
                } else if (day === 1) {
                    step_type = 'month';
                } else if (weekday === 1) {
                    step_type = 'week';
                } else {
                    step_type = 'day';
                }
            }

            fetch(`/api/goal/${goalId}/step`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    title, 
                    due_date, 
                    step_type  // ← SEND FINAL TYPE
                })
            })
            .then(res => {
                if (!res.ok) throw new Error(`HTTP ${res.status}`);
                return res.json();
            })
            .then(data => {
                showToast(`Step added: ${data.step_type.toUpperCase()}!`, 'success');
                titleInput.value = '';
                dateInput.value = '';
                typeSelect.value = 'auto';  // Reset to Auto
                location.reload();
            })
            .catch(err => {
                console.error('Step add error:', err);
                showToast('Failed to add step!', 'danger');
            });
        }
    });

    // ========================================
    // 3. TOGGLE STEP COMPLETION
    // ========================================
    goalsContainer.addEventListener('change', function (e) {
        if (e.target.classList.contains('step-checkbox')) {
            const stepItem = e.target.closest('.step-item');
            const stepId = stepItem.dataset.stepId;
            const card = e.target.closest('[data-goal-id]');
            const progressBar = card.querySelector('.progress-bar');

            fetch(`/api/step/${stepId}/toggle`, {
                method: 'POST'
            })
            .then(res => res.json())
            .then(data => {
                if (data.status === 'success') {
                    progressBar.style.width = data.progress + '%';
                    progressBar.textContent = data.progress + '%';

                    const label = stepItem.querySelector('.form-check-label');
                    if (data.completed) {
                        label.classList.add('text-decoration-line-through', 'text-muted');
                    } else {
                        label.classList.remove('text-decoration-line-through', 'text-muted');
                    }

                    showToast(data.completed ? 'Step completed!' : 'Step reopened!', 'info');
                }
            })
            .catch(err => {
                console.error('Toggle error:', err);
                e.target.checked = !e.target.checked;
                showToast('Failed to update step!', 'danger');
            });
        }
    });

    // ========================================
    // 4. BONUS: AUTO-FILL TYPE WHEN DATE CHANGES
    // ========================================
    goalsContainer.addEventListener('change', function (e) {
        if (e.target.classList.contains('date-input')) {
            const dateInput = e.target;
            const typeSelect = dateInput.closest('.input-group').querySelector('.type-select');
            
            // Only auto-fill if currently set to 'auto'
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
            if (day === 1 && [1, 4, 7, 10].includes(month)) {
                detected = 'quarter';
            } else if (day === 1) {
                detected = 'month';
            } else if (weekday === 1) {
                detected = 'week';
            }

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

    console.log('AUTOSAVE.JS LOADED — WFM PLANNER IS RUNNING WILD!');
});