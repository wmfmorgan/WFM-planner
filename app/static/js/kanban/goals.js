// app/static/js/kanban/goals.js
export function initGoalsKanban() {
  // Sortable is now global from script tag
  if (!window.Sortable) {
    console.error('Sortable.js not loaded');
    return;
  }

  document.querySelectorAll('.kanban-column').forEach(col => {
    Sortable.create(col, {
      group: 'kanban',
      animation: 150,
      onEnd: function (evt) {
        const goalId = evt.item.dataset.goalId;
        const newStatus = evt.to.dataset.status;
        fetch(`/api/goals/${goalId}/status`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ status: newStatus })
        }).then(() => {
          // Update badge counts
          document.querySelectorAll('.kanban-column').forEach(c => {
            const badge = c.closest('.card').querySelector('.badge');
            if (badge) badge.textContent = c.children.length;
          });
        }).catch(console.error);
      }
    });
  });
}