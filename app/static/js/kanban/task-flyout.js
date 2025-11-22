// app/static/js/kanban/task-flyout.js
let currentTaskId = null;

export function initTaskFlyout() {
    const flyout = document.getElementById('taskFlyout');
    
    // CRITICAL: Guard clause — if modal doesn't exist on this page, exit silently
    if (!flyout) {
        console.warn('Task flyout modal (#taskFlyout) not found on this page. Skipping init.');
        return;
    }

    // Open flyout on task click
    document.addEventListener('click', e => {
        const card = e.target.closest('.kanban-item[data-item-id]');
        if (!card) return;

        // Skip goals entirely
        if (card.closest('.edit-goal-card') || card.classList.contains('edit-goal-card')) return;

        // Ignore drag handle and delete button
        if (e.target.closest('.drag-handle') || e.target.closest('.btn-icon-danger')) return;

        // Prevent opening flyout during inline edit
        if (card.classList.contains('editing')) return;

        const taskId = card.dataset.itemId;
        currentTaskId = taskId;

        fetch(`/api/task/${taskId}`)
            .then(r => {
                if (!r.ok) throw new Error('Task not found');
                return r.json();
            })
.then(task => {
    // Fill form
    document.getElementById('taskId').value = task.id;
    document.getElementById('taskDescription').value = task.description || '';
    document.getElementById('taskDueDate').value = task.date || '';
    document.getElementById('taskCategory').value = task.category || '';
    document.getElementById('taskStatus').value = task.status;
    document.getElementById('taskNote').value = task.notes || '';
    document.getElementById('taskCompleteToggle').checked = task.status === 'done';

    populateCategoryDatalist();

    // THE ONLY CORRECT WAY — NO MANUAL HACKING
    const flyout = document.getElementById('taskFlyout');
    
    // Remove any old show classes (in case of bug)
    flyout.classList.remove('show');
    
    // Let Bootstrap do its job — THIS IS THE MONEY LINE
    const modal = bootstrap.Modal.getInstance(flyout) || new bootstrap.Modal(flyout);
    modal.show();

    // Debug: Confirm it's really open
    flyout.addEventListener('shown.bs.modal', () => {
        
    }, { once: true });
})
            .catch(err => {
                console.error('Failed to load task:', err);
                alert('Could not load task details.');
            });
    });

    // NOW SAFE: flyout exists, so we can add listeners
    flyout.addEventListener('input', debounce(saveTask, 600));

    document.getElementById('taskCompleteToggle').addEventListener('change', () => {
        const isDone = document.getElementById('taskCompleteToggle').checked;
        document.getElementById('taskStatus').value = isDone ? 'done' : 'todo';
        saveTask();
    });

    document.getElementById('deleteTaskBtn').addEventListener('click', () => {
        if (confirm('Delete this task forever, brother? NO TURNING BACK!')) {
            fetch(`/api/task/${currentTaskId}`, { method: 'DELETE' })
                .then(r => {
                    if (r.ok) {
                        location.reload();
                    } else {
                        alert('Failed to delete task.');
                    }
                });
        }
    });

    function saveTask() {
        if (!currentTaskId) return;

        const descEl = document.getElementById('taskDescription');
        const catEl = document.getElementById('taskCategory');
        const dateEl = document.getElementById('taskDueDate');
        const statusEl = document.getElementById('taskStatus');
        const noteEl = document.getElementById('taskNote');

        const data = {
            description: descEl?.value?.trim() || '',
            date: dateEl?.value || null,
            category: catEl?.value?.trim() || null,
            status: statusEl?.value || 'todo',
            notes: noteEl?.value?.trim() || ''
        };

        fetch(`/api/task/${currentTaskId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        })
        .then(r => {
            if (!r.ok) throw new Error('Save failed');
            // Live update card
            const card = document.querySelector(`[data-item-id="${currentTaskId}"]`);
            if (card) {
                card.querySelector('.task-text').textContent = data.description;
                const badge = card.querySelector('.task-category-badge') ||
                    card.querySelector('.task-text').insertAdjacentElement('afterend',
                        Object.assign(document.createElement('small'), {
                            className: 'task-category-badge badge bg-secondary text-white px-2 py-1'
                        })
                    );
                badge.textContent = data.category || '';
                badge.style.display = data.category ? 'block' : 'none';
            }
        })
        .catch(err => {
            console.error('Save failed:', err);
            alert('Failed to save task — but don’t worry, brother, try again!');
        });
    }
    function populateCategoryDatalist() {
        fetch('/api/tasks/categories')
            .then(r => r.json())
            .then(categories => {
                const datalist = document.getElementById('categoryDatalist');
                if (datalist) {
                    datalist.innerHTML = categories.map(c => `<option value="${c}">`).join('');
                }
            })
            .catch(() => {}); // Silent fail — not critical
    }

    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
}