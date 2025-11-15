// static/js/kanban/tasks.js
let isSubmittingTask = false;

export function initTaskKanban() {
  let dragged = null;

  const allow = e => e.preventDefault();
  const start = e => {
    dragged = e.target;
    e.dataTransfer.setData('text/plain', e.target.dataset.taskId);
    setTimeout(() => e.target.classList.add('dragging'), 0);
  };

  document.addEventListener('dragover', allow);
  document.addEventListener('drop', e => {
    e.preventDefault();
    if (!dragged) return;
    const col = e.target.closest('.kanban-col');
    if (!col) return;

    const taskId = dragged.dataset.taskId;
    const status = col.dataset.status;

    dragged.classList.remove('dragging');
    col.querySelector('.task-list').appendChild(dragged);

    fetch(`/api/task/${taskId}/status`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status })
    }).catch(console.error);
  });

  document.querySelectorAll('.task-card[draggable="true"]')
    .forEach(c => c.addEventListener('dragstart', start));
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
        card.addEventListener('dragstart', e => {
          e.dataTransfer.setData('text/plain', data.id);
          setTimeout(() => card.classList.add('dragging'), 0);
        });
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