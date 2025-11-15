// static/js/calendar/events.js
const apiBase = '/api';

let editingEventId = null;
let isProcessingClick = false;
let clickDebugId = 0;

export function initEventModal() {
  const modalEl = document.getElementById('eventModal');
  if (!modalEl) return;

  const modal = new bootstrap.Modal(modalEl);
  const form = document.getElementById('eventForm');
  const titleEl = document.getElementById('eventModalLabel');
  const allDayCheckbox = document.getElementById('allDay');
  const recurringCheckbox = document.getElementById('recurring');
  const recurrenceOptions = document.getElementById('recurrenceOptions');

    // RESET isProcessingClick ON CANCEL
    modalEl.querySelectorAll('[data-bs-dismiss="modal"]').forEach(btn => {
    btn.addEventListener('click', () => {
        isProcessingClick = false;
    });
    });

  // Reset modal
  function resetModal() {
    editingEventId = null;
    titleEl.textContent = 'Add Event';
    form.reset();
    document.getElementById('startTime').disabled = false;
    document.getElementById('endTime').disabled = false;
    recurrenceOptions.classList.add('d-none');
    const delBtn = document.getElementById('deleteEventBtn');
    if (delBtn) delBtn.remove();
  }

  // All-day toggle
  allDayCheckbox.addEventListener('change', () => {
    const disabled = allDayCheckbox.checked;
    document.getElementById('startTime').disabled = disabled;
    document.getElementById('endTime').disabled = disabled;
    if (disabled) {
      document.getElementById('startTime').value = '';
      document.getElementById('endTime').value = '';
    }
  });

  // Recurring toggle
  recurringCheckbox.addEventListener('change', () => {
    recurrenceOptions.classList.toggle('d-none', !recurringCheckbox.checked);
  });

  // Form submit
  form.addEventListener('submit', (e) => {
    e.preventDefault();
    const allDay = allDayCheckbox.checked;
    const payload = {
      title: document.getElementById('eventTitle').value.trim(),
      start_date: document.getElementById('startDate').value,
      end_date: document.getElementById('endDate').value,
      all_day: allDay,
      start_time: allDay ? null : document.getElementById('startTime').value,
      end_time: allDay ? null : document.getElementById('endTime').value,
      is_recurring: recurringCheckbox.checked,
      recurrence_rule: recurringCheckbox.checked ? document.getElementById('recurrenceRule').value : null
    };

    const method = editingEventId ? 'PUT' : 'POST';
    const url = editingEventId ? `${apiBase}/event/${editingEventId}` : `${apiBase}/event`;

    fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
    .then(r => {
      if (!r.ok) throw r;
      location.reload();
    })
    .catch(err => {
      console.error('Event save failed:', err);
      alert('Failed to save event.');
    });
  });

// Click handler (edit badge or add from cell)
document.addEventListener('click', (e) => {
  const debugId = ++clickDebugId;

  // === 1. ADD EVENT FROM CELL (month/week) ===
  const addArea = e.target.closest('.add-event-area');
  if (addArea) {
    //console.log(`[EVENT CLICK ${debugId}] Add area clicked`);
    if (isProcessingClick) return;
    isProcessingClick = true;

    const cell = addArea.closest('.calendar-day');
    if (!cell || !cell.dataset.date) {
      isProcessingClick = false;
      return;
    }

    resetModal();
    modal.show();
    modalEl.addEventListener('shown.bs.modal', function fill() {
      document.getElementById('eventDate').value = cell.dataset.date;
      document.getElementById('startDate').value = cell.dataset.date;
      document.getElementById('endDate').value = cell.dataset.date;
      document.getElementById('startTime').value = '09:00';
      document.getElementById('endTime').value = '10:00';
      this.removeEventListener('shown.bs.modal', fill);
      isProcessingClick = false;
    }, { once: true });
    return;
  }

  // === 2. EDIT EXISTING EVENT ===
  const badge = e.target.closest('.event-badge[data-event-id]');
  if (!badge) {
    //console.log(`[EVENT CLICK ${debugId}] No badge or add-area`);
    return;
  }

  //console.log(`[EVENT CLICK ${debugId}] Badge ID:`, badge.dataset.eventId);

  if (isProcessingClick) return;
  isProcessingClick = true;
  e.stopPropagation();

  const id = badge.dataset.eventId;
  fetch(`${apiBase}/event/${id}`)
    .then(r => r.json())
    .then(ev => {
      editingEventId = ev.id;
      titleEl.textContent = 'Edit Event';
      form.reset();
      document.getElementById('eventTitle').value = ev.title || '';
      document.getElementById('startDate').value = ev.start_date;
      document.getElementById('endDate').value = ev.end_date;
      document.getElementById('startTime').value = ev.start_time || '';
      document.getElementById('endTime').value = ev.end_time || '';
      allDayCheckbox.checked = ev.all_day;
      document.getElementById('startTime').disabled = ev.all_day;
      document.getElementById('endTime').disabled = ev.all_day;
      recurringCheckbox.checked = ev.is_recurring || false;
      recurrenceOptions.classList.toggle('d-none', !ev.is_recurring);
      if (ev.recurrence_rule) document.getElementById('recurrenceRule').value = ev.recurrence_rule;

      let delBtn = document.getElementById('deleteEventBtn');
      if (!delBtn) {
        delBtn = document.createElement('button');
        delBtn.id = 'deleteEventBtn';
        delBtn.type = 'button';
        delBtn.className = 'btn btn-danger';
        delBtn.textContent = 'Delete';
        modalEl.querySelector('.modal-footer').appendChild(delBtn);
      }
      delBtn.onclick = () => {
        if (confirm('Delete this event?')) {
          fetch(`${apiBase}/event/${id}`, { method: 'DELETE' })
            .then(() => location.reload());
        }
      };

      modal.show();
    })
    .finally(() => {
      modalEl.addEventListener('shown.bs.modal', () => {
        isProcessingClick = false;
      }, { once: true });
    });
});

  // Modal cleanup
  modalEl.addEventListener('hidden.bs.modal', () => {
    resetModal();
    isProcessingClick = false;
    document.querySelectorAll('.modal-backdrop').forEach(b => b.remove());
    document.body.classList.remove('modal-open');
    document.body.style.overflow = '';
    document.body.style.paddingRight = '';
  });
}