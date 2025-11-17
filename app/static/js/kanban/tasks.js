let isSubmittingTask = false;

export function initTaskKanban() {
  const allowDrop = (e) => e.preventDefault();

  const dragStart = (e) => {
    e.dataTransfer.setData('text/plain', e.target.dataset.taskId);
    setTimeout(() => e.target.classList.add('dragging'), 0);
  };

  const drop = (e) => {
    e.preventDefault();
    const taskId = e.dataTransfer.getData('text/plain');
    const task = document.querySelector(`[data-task-id="${taskId}"]`);
    if (!task) return;
    const col = e.target.closest('.kanban-col');
    if (!col) return;
    col.querySelector('.task-list').appendChild(task);
    task.classList.remove('dragging');
    const status = col.dataset.status;
    fetch(`/api/task/${taskId}/status`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status })
    }).catch(console.error);
  };

  // Attach listeners dynamically
  document.querySelectorAll('.kanban-col').forEach(col => {
    col.addEventListener('dragover', allowDrop);
    col.addEventListener('drop', drop);
  });

  document.querySelectorAll('.task-card[draggable="true"]').forEach(card => {
    card.addEventListener('dragstart', dragStart);
    card.addEventListener('dragend', () => card.classList.remove('dragging'));
  });
}

export function initAddTaskForm() {
  document.querySelectorAll('#add-task-form').forEach(form => {
    form.addEventListener('submit', function(e) {
      e.preventDefault();
      e.stopImmediatePropagation();
      const input = this.querySelector('.add-task-input');
      const desc = input?.value.trim();
      if (!desc || isSubmittingTask) return;
      isSubmittingTask = true;
      const [y, m, d] = (document.getElementById('dayDateData')?.textContent.trim() || '').split('-');
      fetch('/api/task', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ description: desc, year: +y, month: +m, day: +d })
      })
      .then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then(data => {
        const list = document.querySelector('[data-status="todo"] .task-list');
        const card = document.createElement('div');
        card.className = 'task-card bg-white p-3 rounded shadow-sm border';
        card.draggable = true;
        card.dataset.taskId = data.id;
        card.innerHTML = `<div class="task-desc fw-medium">${desc}</div>`;
        card.addEventListener('dragstart', dragStart);
        card.addEventListener('dragend', () => card.classList.remove('dragging'));
        list.appendChild(card);
        input.value = '';
        input.focus();
      })
      .catch(err => {
        console.error(err);
        alert('Failed to add task.');
      })
      .finally(() => {
        setTimeout(() => isSubmittingTask = false, 600);
      });
    });
  });
}