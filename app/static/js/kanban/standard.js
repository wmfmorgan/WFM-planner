// app/static/js/kanban/standard.js
let isSubmittingItem = false;

export function initKanban() {
  if (!window.Sortable) {
    console.error('Sortable.js not loaded');
    return;
  }

  document.querySelectorAll('.kanban-column').forEach(col => {
    Sortable.create(col, {
      group: col.dataset.type === 'tasks' ? 'tasks' : 'goals',
      animation: 150,
      forceFallback: true,
      fallbackTolerance: 3,
      filter: '.mt-auto',
      preventOnFilter: false,
      ghostClass: 'sortable-ghost',
      chosenClass: 'sortable-chosen',
      handle: '.drag-handle',   // ← THIS IS THE KEY

      onEnd: function (evt) {
        if (evt.newIndex === evt.oldIndex && evt.from === evt.to) return;

        const itemId = evt.item.dataset.itemId;
        const newStatus = evt.to.dataset.status;
        const type = evt.to.dataset.type || 'goals';

        let handled = false;

        // 1. Backlog → Today
        if (evt.from.dataset.status === 'backlog' && type === 'tasks' && newStatus !== 'backlog') {
          fetch(`/api/task/${itemId}/today`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
          }).then(() => {
            location.reload();
          });
          handled = true;
        }

        // 2. Normal status change
        if (!handled) {
          fetch(`/api/${type === 'goals' ? 'goals' : 'task'}/${itemId}/status`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status: newStatus })
          });
        }

        // 3. Priority ranking — always runs
        const items = Array.from(evt.to.children).filter(el => el.dataset.itemId);
        items.forEach((item, index) => {
          const id = item.dataset.itemId;
          fetch(`/api/${type === 'goals' ? 'goals' : 'task'}/${id}/rank`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ rank: index })
          }).catch(() => {});
        });

        // Update badges
        document.querySelectorAll(`.kanban-column[data-type="${type}"]`).forEach(c => {
          const badge = c.closest('.card')?.querySelector('.badge');
          if (badge) badge.textContent = c.children.length;
        });
      } // ← closes onEnd    

    });  // ← THIS CLOSES Sortable.create()

  }); // ← closes forEach column
    // Goals add (modal trigger)
    document.addEventListener('click', function(e) {
    if (e.target.closest('.add-kanban-item-btn')) {
        const btn = e.target.closest('.add-kanban-item-btn');
        const parentType = btn.dataset.parentType;
        const pageType = btn.dataset.pageType;
        const typeMap = {
        'year': 'annual',
        'annual': 'quarterly',
        'quarterly': 'monthly',
        'monthly': 'weekly',
        'weekly': 'daily',
        'day': 'daily'
        };
        const childType = typeMap[parentType || pageType] || 'daily';  // Prefer parentType if set, fallback to pageType
        const form = document.getElementById('kanban_unified-goal-form');
        form.reset();
        document.getElementById('modalTitle').textContent = `Add ${childType.charAt(0).toUpperCase() + childType.slice(1)} Goal`;
        const typeSelect = form.querySelector('.goal-type-select');
        if (typeSelect) {
        typeSelect.value = childType;
        typeSelect.disabled = true;  // Lock to default
        }
        const hidden = document.getElementById('kanban-hidden-type');
        if (hidden) hidden.value = childType;
        new bootstrap.Modal(document.getElementById('goalModal')).show();
    }
    });

  // Tasks add form
  document.querySelectorAll('#add-task-form').forEach(form => {
    form.addEventListener('submit', function(e) {
      e.preventDefault();
      const input = this.querySelector('.add-task-input');
      const desc = input?.value.trim();
      if (!desc || isSubmittingItem) return;
      isSubmittingItem = true;
      const [y, m, d] = (document.getElementById('dayDateData')?.textContent.trim() || '').split('-');
      fetch('/api/task', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ description: desc, year: +y, month: +m, day: +d })
      }).then(r => r.json()).then(data => {
        const list = document.querySelector('[data-status="todo"][data-type="tasks"]');
        const card = document.createElement('div');
        card.className = 'kanban-item card mb-2 d-flex align-items-center edit-goal-card';
        card.dataset.itemId = data.id;
        card.innerHTML = `
        <div class="drag-handle text-muted flex-shrink-0 d-flex align-items-center justify-content-center px-3">
          <i class="bi bi-grip-vertical fs-5"></i>
        </div>
        <div class="flex-grow-1 pe-3 py-2">
          <div class="task-text card-title mb-0 fw-medium">${desc}</div>
          <input type="text" class="task-edit form-control form-control-sm d-none" value="${desc}">
        </div>
        <button type="button" class="btn btn-icon-danger btn-sm position-absolute top-0 end-0 m-1 opacity-0 opacity-0">
          <i class="bi bi-x-lg"></i>
        </button>
        `;
        list.appendChild(card);
        input.value = '';
        input.focus();
        const badge = list.closest('.card').querySelector('.badge');
        if (badge) badge.textContent = list.children.length;
      }).catch(console.error).finally(() => isSubmittingItem = false);
    });
  });

  // Goal add modal submit (live append, no reload)
  const goalForm = document.getElementById('kanban_unified-goal-form');
  if (goalForm) {
    goalForm.addEventListener('submit', function(e) {
      e.preventDefault();
      e.stopPropagation();

      const formData = new FormData(this);
      const data = Object.fromEntries(formData);
      data.completed = formData.get('completed') === 'on';

      const goalId = data.goal_id || null;
      const parentId = data.parent_id || null;

      // EDIT = PUT, ADD = POST
      let url = '/goals';
      let method = 'POST';

      if (goalId) {
        url = `/api/goals/${goalId}`;
        method = 'PUT';
      } else if (parentId) {
        url = `/api/goals/${parentId}/subgoal`;
      }

      fetch(url, {
        method: method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      })
      .then(r => {
        if (!r.ok) throw new Error('Save failed');
        return r.json();
      })
      .then(result => {
        if (result.success) {
          if (goalId) {
            // EDIT: just reload (simplest) or update card title live
            location.reload();
          } else {
            // ADD: live append
            const list = document.querySelector('.kanban-column[data-status="todo"][data-type="goals"]');
            const card = document.createElement('div');
            card.className = 'kanban-item card mb-2 d-flex align-items-center edit-goal-card';
            card.dataset.itemId = result.goal.id;
            card.innerHTML = `
              <div class="drag-handle text-muted flex-shrink-0 d-flex align-items-center justify-content-center px-3">
                <i class="bi bi-grip-vertical fs-5"></i>
              </div>
              <div class="flex-grow-1 text-truncate pe-3">
                <h6 class="card-title mb-0 fw-medium">${result.goal.title}</h6>
              </div>
            `;
            list.appendChild(card);
            const badge = list.closest('.card').querySelector('.badge');
            if (badge) badge.textContent = parseInt(badge.textContent) + 1;
          }
          bootstrap.Modal.getInstance(document.getElementById('goalModal')).hide();
          this.reset();
        }
      })
      .catch(err => {
        console.error('Save failed:', err);
        alert('Failed to save goal.');
      });
    });
  }

  // Goal edit (click card to open modal prepopulated)
  document.addEventListener('click', function(e) {
    const card = e.target.closest('.edit-goal-card');
    if (card) {
      const goalId = card.dataset.itemId;
      fetch(`/api/goals/${goalId}`)
        .then(r => r.json())
        .then(goal => {
          const form = document.getElementById('kanban_unified-goal-form');
          form.reset();
          
          const typeSelect = form.querySelector('.goal-type-select');
          if (typeSelect) {
          typeSelect.value = goal.type;
          typeSelect.disabled = true;  // Lock to default
          }
          const hidden = document.getElementById('kanban-hidden-type');
          if (hidden) hidden.value = goal.type;


          document.getElementById('modalTitle').textContent = 'Edit Goal';
          form.querySelector('[name="goal_id"]').value = goalId;  // Fixed: .value assignment
          form.querySelector('[name="title"]').value = goal.title || '';
          //document.getElementById('kanban-hidden-type').value = goal.type || 'daily';
          //alert(document.getElementById('kanban-hidden-type').value); alert(goal.type);
          form.querySelector('[name="type"]').value = goal.type || 'daily';
          form.querySelector('[name="type"]').disabled = false;  // Allow change
          form.querySelector('[name="category"]').value = goal.category || '';
          form.querySelector('[name="description"]').value = goal.description || '';
          form.querySelector('[name="motivation"]').value = goal.motivation || '';
          form.querySelector('[name="due_date"]').value = goal.due_date || '';
          form.querySelector('[name="status"]').value = goal.status || 'todo';
          form.querySelector('[name="completed"]').checked = goal.completed || false;
          form.querySelector('[name="parent_id"]').value = goal.parent_id || '';
          new bootstrap.Modal(document.getElementById('goalModal')).show();
        }).catch(err => console.error('Fetch goal failed', err));
    }
  });

  // ——— BACKLOG: ADD TASK ———
  document.getElementById('add-backlog-task-form')?.addEventListener('submit', function(e) {
    e.preventDefault();
    const input = this.querySelector('.add-task-input');
    const desc = input.value.trim();
    if (!desc) return;

    fetch('/api/task', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        description: desc,
        backlog: true          // ← this sends it to backlog
      })
    })
    .then(r => r.json())
    .then(task => {
      // Live-append to backlog column
      const backlogCol = document.querySelector('.kanban-column[data-status="backlog"]');
      const card = document.createElement('div');
      card.className = 'kanban-item card mb-2 d-flex align-items-center';
      card.dataset.itemId = task.id;
      card.innerHTML = `
        <div class="drag-handle text-muted flex-shrink-0 d-flex align-items-center justify-content-center px-3">
          <i class="bi bi-grip-vertical fs-5"></i>
        </div>
        <div class="flex-grow-1 text-truncate pe-3">
          <h6 class="card-title mb-0 fw-medium">${task.description}</h6>
        </div>
      `;
      backlogCol.appendChild(card);
      input.value = '';
      input.focus();
    })
    .catch(err => {
      console.error('Failed to add backlog task:', err);
      alert('Failed to add task');
    });
  });

  // ——— TASK INLINE EDITING + DELETE — MACHO MADNESS EDITION ———
  document.addEventListener('click', (e) => {
    const item = e.target.closest('.kanban-item[data-item-id]');
    if (!item || item.querySelector('.edit-goal-card')) return; // Skip goals

    // Ignore clicks on drag handle or delete button
    if (e.target.closest('.drag-handle') || e.target.closest('.btn-icon-danger')) return;

    const textDiv = item.querySelector('.task-text');
    const input = item.querySelector('.task-edit');
    if (!textDiv || !input) return;

    // Enter edit mode
    
    if (!item.classList.contains('editing')) {
      item.classList.add('editing');
      textDiv.classList.add('d-none');
      input.classList.remove('d-none');
      input.focus();
      input.select();
    }
  });

  // Save on Enter / Cancel on Escape
  document.addEventListener('keydown', (e) => {
    if (!e.target.classList.contains('task-edit')) return;

    if (e.key === 'Enter') {
      e.preventDefault();
      saveTaskEdit(e.target);
    } else if (e.key === 'Escape') {
      cancelTaskEdit(e.target);
    }
  });

  // Save on blur too
  document.addEventListener('focusout', (e) => {
    if (e.target.classList.contains('task-edit')) {
      saveTaskEdit(e.target);
    }
  });

  function saveTaskEdit(input) {
    const item = input.closest('.kanban-item');
    const newText = input.value.trim();
    const oldText = item.querySelector('.task-text').textContent.trim();
    const taskId = item.dataset.itemId;

    // If no change or empty → revert
    if (!newText || newText === oldText) {
      cancelTaskEdit(input);
      return;
    }

    fetch(`/api/task/${taskId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ description: newText })
    })
    .then(r => {
      if (!r.ok) throw new Error();
      item.querySelector('.task-text').textContent = newText;
      cancelTaskEdit(input);
    })
    .catch(() => {
      alert('Save failed, brother! Try again.');
      cancelTaskEdit(input);
    });
  }

  function cancelTaskEdit(input) {
    const item = input.closest('.kanban-item');
    input.classList.add('d-none');
    item.querySelector('.task-text').classList.remove('d-none');
    item.classList.remove('editing');
    input.value = item.querySelector('.task-text').textContent.trim();
  }

  // ——— DELETE TASK — SAY YOUR PRAYERS! ———
  document.addEventListener('click', (e) => {
    const btn = e.target.closest('.btn-icon-danger');
    if (!btn) return;

    if (!confirm('Delete this task? NO TURNING BACK, BROTHER!')) return;

    const item = btn.closest('.kanban-item');
    const taskId = item.dataset.itemId;

    fetch(`/api/task/${taskId}`, { method: 'DELETE' })
      .then(r => {
        if (r.ok) {
          item.style.transition = 'all 0.3s ease';
          item.style.opacity = '0';
          item.style.transform = 'scale(0.8)';
          setTimeout(() => item.remove(), 300);
        }
      });
  });


}