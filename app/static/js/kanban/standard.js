let isSubmittingItem = false;

export function initKanban() {
  if (!window.Sortable) {
    console.error('Sortable.js not loaded');
    return;
  }

  document.querySelectorAll('.kanban-column').forEach(col => {
    Sortable.create(col, {
      group: col.dataset.type || 'goals',
      animation: 150,
      forceFallback: true,  // Force native drag ghost for browser issues
      fallbackTolerance: 3,  // Increase sensitivity for drop
      filter: '.mt-auto',  // Ignore add form during drag
      preventOnFilter: false,  // Allow click on filter
      ghostClass: 'sortable-ghost',
      chosenClass: 'sortable-chosen',
      onEnd: function (evt) {
        if (evt.newIndex === evt.oldIndex && evt.from === evt.to) {
          //console.log('No move detected - skipping POST');
          return;  // Don't POST if not moved to new column
        }
        const itemId = evt.item.dataset.itemId;
        const newStatus = evt.to.dataset.status;
        const type = evt.to.dataset.type || 'goals';
        //console.log('Move detected - POST to', type, newStatus);
        const url = type === 'goals' ? `/api/goals/${itemId}/status` : `/api/task/${itemId}/status`;
        fetch(url, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ status: newStatus })
        }).then(() => {
          document.querySelectorAll(`.kanban-column[data-type="${type}"]`).forEach(c => {
            const badge = c.closest('.card').querySelector('.badge');
            if (badge) badge.textContent = c.children.length;
          });
        }).catch(err => console.error('Update failed:', err));
      }
    });
  });

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
        const form = document.getElementById('unified-goal-form');
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
        card.className = 'kanban-item card mb-2';
        card.dataset.itemId = data.id;
        card.innerHTML = `<div class="p-2"><h6 class="card-title mb-1">${desc}</h6></div>`;
        list.appendChild(card);
        input.value = '';
        input.focus();
        const badge = list.closest('.card').querySelector('.badge');
        if (badge) badge.textContent = list.children.length;
      }).catch(console.error).finally(() => isSubmittingItem = false);
    });
  });

  // Goal add modal submit (live append, no reload)
    // Goal add modal submit (live append, no reload)
    const goalForm = document.getElementById('unified-goal-form');
    if (goalForm) {
    goalForm.addEventListener('submit', function(e) {
        e.preventDefault();
        e.stopPropagation();  // Prevent bubbling
        const formData = new FormData(this);
        const data = Object.fromEntries(formData);
        data.completed = formData.get('completed') === 'on';
        const parentId = data.parent_id || null;
        const url = parentId ? `/api/goals/${parentId}/subgoal` : '/goals';
        fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
        }).then(r => {
        if (!r.ok) {
            r.text().then(text => alert(`Error: ${text}`));
            return;
        }
        return r.json();
        }).then(result => {
        if (result.success && result.goal) {
            const list = document.querySelector('.kanban-column[data-status="todo"][data-type="goals"]');
            const card = document.createElement('div');
            card.className = 'kanban-item card mb-2';
            card.dataset.itemId = result.goal.id;
            card.innerHTML = `<div class="p-2"><h6 class="card-title mb-1">${result.goal.title}</h6></div>`;
            list.appendChild(card);
            const badge = list.closest('.card').querySelector('.badge');
            if (badge) badge.textContent = parseInt(badge.textContent) + 1;
        }
        bootstrap.Modal.getInstance(this.closest('.modal')).hide();
        this.reset();  // Clear form for next add
        }).catch(err => {
        console.error('Add failed', err);
        alert('Failed to add goal.');
        });
    }, { once: true });  // Fire only once per load
    }

  // Goal edit (click card to open modal prepopulated)
  document.addEventListener('click', function(e) {
    const card = e.target.closest('.edit-goal-card');
    if (card) {
      const goalId = card.dataset.itemId;
      fetch(`/api/goals/${goalId}`)
        .then(r => r.json())
        .then(goal => {
          const form = document.getElementById('unified-goal-form');
          form.reset();
          document.getElementById('modalTitle').textContent = 'Edit Goal';
          form.querySelector('[name="goal_id"]').value = goalId;  // Fixed: .value assignment
          form.querySelector('[name="title"]').value = goal.title || '';
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

  // Update modal submit to handle edit (PUT) or add (POST)
  //const goalForm = document.getElementById('unified-goal-form');
  if (goalForm) {
    goalForm.addEventListener('submit', function(e) {
      e.preventDefault();
      const formData = new FormData(this);
      const data = Object.fromEntries(formData);
      data.completed = formData.get('completed') === 'on';
      const goalId = data.goal_id || null;
      const parentId = data.parent_id || null;
      let url = goalId ? `/api/goals/${goalId}` : (parentId ? `/api/goals/${parentId}/subgoal` : '/goals');
      let method = goalId ? 'PUT' : 'POST';
      fetch(url, {
        method: method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      }).then(r => r.json()).then(result => {
        if (result.success) {
          // Live update or reload — for simplicity, reload for now
          location.reload();
        }
      }).catch(err => console.error('Save failed', err));
    });
  }

}