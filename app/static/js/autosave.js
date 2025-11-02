// app/static/js/autosave.js
document.addEventListener('DOMContentLoaded', function () {
    const goalForm = document.getElementById('goalForm');
    const goalsContainer = document.getElementById('goalsContainer');

    // Add Goal
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
                location.reload(); // Refresh to show new goal
            }
        });
    });

    // Add Step
    goalsContainer.addEventListener('click', function (e) {
        if (e.target.classList.contains('add-step')) {
            const card = e.target.closest('[data-goal-id]');
            const goalId = card.dataset.goalId;
            const input = card.querySelector('.new-step');
            const dateInput = card.querySelector('input[type="date"]');
            const title = input.value.trim();
            if (!title) return;

            fetch(`/api/goal/${goalId}/step`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title, due_date: dateInput.value || null })
            })
            .then(() => {
                input.value = ''; dateInput.value = '';
                location.reload();
            });
        }
    });

    // Toggle Step
    goalsContainer.addEventListener('change', function (e) {
        if (e.target.classList.contains('step-checkbox')) {
            const stepItem = e.target.closest('.step-item');
            const stepId = stepItem.dataset.stepId;
            const progressBar = stepItem.closest('.card').querySelector('.progress-bar');

            fetch(`/api/step/${stepId}/toggle`, { method: 'POST' })
            .then(res => res.json())
            .then(data => {
                progressBar.style.width = data.progress + '%';
                progressBar.textContent = data.progress + '%';
                progressBar.dataset.progress = data.progress;
            });
        }
    });
});