// app/static/js/goals.js
// WFM PLANNER — HIERARCHICAL GOALS MODULE
// Single source of truth for the entire goal tree UI on /goals page
// Responsibilities:
//   • Render & manage goal tree (annual → quarterly → … → daily)
//   • Create top-level goals & sub-goals via unified modal
//   • Inline editing of any goal
//   • Expand/collapse tree nodes with localStorage persistence
//   • Delete goals (cascading)
//   • Full CSRF protection on all mutations
//   • Zero inline JS remaining (Tenet #1 complete forever)

import { showToast } from './utils.js';

// ===================================================================
// 1. ONE SOURCE OF TRUTH — mirrored from Python constants (Tenet #3)
// ===================================================================
const CSRF_TOKEN = document.querySelector('input[name="csrf_token"]')?.value || '';

// What child type is allowed under each parent (drives "Add Sub-Goal" button)
const TYPE_HIERARCHY = {
  annual: 'quarterly',
  quarterly: 'monthly',
  monthly: 'weekly',
  weekly: 'daily',
  daily: 'daily'        // daily goals have no children
};

// Used to populate <select> elements in modal & inline edit forms
const GOAL_TYPES   = [ { value: 'annual',     label: 'Annual'     },
                       { value: 'quarterly',  label: 'Quarterly'  },
                       { value: 'monthly',    label: 'Monthly'    },
                       { value: 'weekly',     label: 'Weekly'     },
                       { value: 'daily',      label: 'Daily'      } ];

const CATEGORIES   = ['Work','Marital','Family','Physical','Mental','Hobby','Social','Financial'];

const STATUSES     = [ { value: 'todo',        label: 'To Do'        },
                       { value: 'in_progress', label: 'In Progress' },
                       { value: 'blocked',     label: 'Blocked'     },
                       { value: 'done',        label: 'Done'        } ];

// ===================================================================
// 2. HELPER FUNCTIONS
// ===================================================================

// Helper: convert status value → human label
function getStatusLabel(value) {
  const status = STATUSES.find(s => s.value === value);
  return status ? status.label : value; // fallback if unknown
}

// Re-populate all <select> dropdowns inside the modal or inline edit cards
function populateSelects() {
  const typeEl   = document.querySelector('[name="type"]');
  const catEl    = document.querySelector('[name="category"]');
  const statusEl = document.querySelector('[name="status"]');

  if (!typeEl || !catEl || !statusEl) return;

  typeEl.innerHTML   = GOAL_TYPES.map(t => `<option value="${t.value}">${t.label}</option>`).join('');
  catEl.innerHTML    = CATEGORIES.map(c => `<option value="${c}">${c}</option>`).join('');
  statusEl.innerHTML = STATUSES.map(s => `<option value="${s.value}">${s.label}</option>`).join('');

  typeEl.value   = 'annual';    // default for new top-level goals
  statusEl.value = 'todo';
}

// Open the unified goal modal (used for both top-level goals & sub-goals)
function openModal(title, parentId = null, childType = null) {
  document.getElementById('modalTitle').textContent = title;

  const form = document.getElementById('unified-goal-form');
  form.reset();
  populateSelects();

  // Hidden fields used by backend
  form.querySelector('[name="parent_id"]').value = parentId || '';
  form.querySelector('[name="goal_id"]').value   = '';   // blank = create mode

  if (childType) document.querySelector('[name="type"]').value = childType;

  // Make sure submit button is enabled after previous failed submit
  form.querySelector('button[type="submit"]').disabled = false;

  new bootstrap.Modal(document.getElementById('goalModal')).show();
}

// Smooth expand/collapse animation + chevron flip + localStorage sync
function toggleCollapse(collapseEl, expand) {
  collapseEl.dataset.collapsed = !expand;
  collapseEl.style.maxHeight = expand ? collapseEl.scrollHeight + 'px' : '0';

  const chevron = collapseEl.closest('.goal-item')?.querySelector('.toggle-chevron');
  if (chevron) {
    chevron.classList.toggle('bi-chevron-right', !expand);
    chevron.classList.toggle('bi-chevron-down',  expand);
  }

  // After animation, remove max-height so content can grow/shrink freely
  collapseEl.addEventListener('transitionend', function cleanup() {
    if (expand) collapseEl.style.maxHeight = 'none';
    collapseEl.removeEventListener('transitionend', cleanup);
  }, { once: true });
}

// ===================================================================
// 3. MAIN — DOM READY
// ===================================================================
document.addEventListener('DOMContentLoaded', () => {
  populateSelects();

  // ── Restore user’s last expand/collapse preferences ─────────────────────
  document.querySelectorAll('.goal-collapse').forEach(collapse => {
    const goalId = collapse.closest('.goal-item')?.dataset.goalId;
    if (goalId && localStorage.getItem(`expanded-goal-${goalId}`) === 'true') {
      toggleCollapse(collapse, true);
    }
  });

  // ── SINGLE CLICK DELEGATION (one listener rules the entire page) ───────
  document.addEventListener('click', e => {
    const t = e.target;

    // 1. Open modal to create a brand-new top-level goal
    if (t.matches('[data-bs-target="#goalModal"]') || t.closest('[data-bs-target="#goalModal"]')) {
      openModal('Create Goal');
      return;
    }

    // 2. Chevron → expand/collapse (Ctrl/Cmd = recursive)
    const chevron = t.closest('.toggle-chevron');
    if (chevron) {
      const collapse = chevron.closest('.goal-item')?.querySelector('.goal-collapse');
      if (!collapse) return;

      const goalId = chevron.closest('.goal-item')?.dataset.goalId;

      if (e.ctrlKey || e.metaKey) {
        // Expand/collapse EVERY child recursively
        const all = chevron.closest('.goal-item').querySelectorAll('.goal-collapse');
        const allOpen = Array.from(all).every(c => c.dataset.collapsed === 'false');
        all.forEach(c => toggleCollapse(c, allOpen ? false : true));
        if (goalId) localStorage.setItem(`expanded-goal-${goalId}`, (!allOpen).toString());
      } else {
        const shouldExpand = collapse.dataset.collapsed !== 'false';
        toggleCollapse(collapse, shouldExpand);
        if (goalId) localStorage.setItem(`expanded-goal-${goalId}`, shouldExpand);
      }
      return;
    }

    // 3. Inline edit toggles
    if (t.closest('.edit-goal-btn')) {
      const card = t.closest('.goal-card');
      card.querySelector('.view-mode').classList.add('d-none');
      card.querySelector('.edit-mode').classList.remove('d-none');
      return;
    }
    if (t.closest('.cancel-edit')) {
      const card = t.closest('.goal-card');
      card.querySelector('.edit-mode').classList.add('d-none');
      card.querySelector('.view-mode').classList.remove('d-none');
      return;
    }

    // 4. Delete goal + cascade
    if (t.closest('.delete-goal-btn')) {
      if (!confirm('Delete this goal and ALL sub-goals permanently?')) return;
      const id = t.closest('.delete-goal-btn').dataset.goalId;

      fetch(`/api/goals/${id}`, {
        method: 'DELETE',
        headers: { 'X-CSRFToken': CSRF_TOKEN }
      })
        .then(r => r.ok ? r.json() : Promise.reject())
        .then(() => {
          t.closest('.goal-item').remove();
          showToast('Goal erased from history!', 'danger');
        })
        .catch(() => showToast('Delete failed — check server', 'danger'));
      return;
    }

    // 5. Add sub-goal button
    if (t.closest('.add-subgoal-btn')) {
      const parentId   = t.closest('.add-subgoal-btn').dataset.parentId;
      const parentType = t.closest('.goal-card').dataset.goalType;
      const childType  = TYPE_HIERARCHY[parentType] || 'daily';
      openModal('Add Sub-Goal', parentId, childType);
      return;
    }
  });

  // ── INLINE EDIT SAVE (PUT) ─────────────────────────────────────────────
  document.addEventListener('submit', e => {
    if (!e.target.matches('.edit-goal-form')) return;
    e.preventDefault();

    const form = e.target;
    const id   = form.querySelector('[name="goal_id"]').value;

    const payload = {
      title:       form.querySelector('.goal-title-input').value.trim(),
      type:        form.querySelector('.goal-type-input').value,
      category:    form.querySelector('.goal-category-input').value,
      description: form.querySelector('.goal-description-input').value,
      motivation:  form.querySelector('.goal-motivation-input').value,
      due_date:    form.querySelector('.goal-due-date-input').value || null,
      status:      form.querySelector('.goal-status-input').value,
      completed:   form.querySelector('.goal-completed-input').checked
    };

    fetch(`/api/goals/${id}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': CSRF_TOKEN
      },
      body: JSON.stringify(payload)
    })
      .then(r => r.ok ? r.json() : Promise.reject())
      .then(() => {
        // Update only the title in DOM (fast feedback)
        form.closest('.goal-card').querySelector('.goal-title-text').textContent = payload.title;
        form.closest('.goal-card').querySelector('.view-mode').classList.remove('d-none');
        form.closest('.goal-card').querySelector('.edit-mode').classList.add('d-none');
        showToast('Goal updated — YEAH!', 'success');
      })
      .catch(() => showToast('Update failed', 'danger'));
  });

  // ── MODAL CREATE NEW GOAL OR SUB-GOAL (POST) ───────────────────────────
  const modalForm = document.getElementById('unified-goal-form');
  modalForm.addEventListener('submit', e => {
    e.preventDefault();
    const submitBtn = modalForm.querySelector('button[type="submit"]');
    submitBtn.disabled = true;

    const formData = Object.fromEntries(new FormData(modalForm));
    formData.completed = !!modalForm.querySelector('[name="completed"]').checked;

    const parentId = formData.parent_id || null;
    const url = parentId ? `/api/goals/${parentId}/subgoal` : '/api/goals';

    fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': CSRF_TOKEN
      },
      body: JSON.stringify(formData)
    })
      .then(r => r.ok ? r.json() : r.json().then(err => { throw err; }))
      .then(res => {
        if (res.success) {
          showToast('New goal locked in — SAY YEAH!', 'success');
          location.reload(); // Full refresh = simplest & most reliable for tree rebuild
        }
      })
      .catch(err => {
        console.error('Goal creation failed:', err);
        showToast('Creation failed: ' + (err.message || 'Unknown error'), 'danger');
      })
      .finally(() => submitBtn.disabled = false);
  });
});