document.addEventListener('DOMContentLoaded', () => {
    const modal = new bootstrap.Modal(document.getElementById('eventModal'));
    let selectedDate = null;
    let selectedHour = null;

    // === CLICK HANDLER (SAFE) ===
    document.querySelectorAll('.add-event-area').forEach(area => {
        area.addEventListener('click', (e) => {
            e.stopPropagation();
            const cell = e.target.closest('.calendar-day') || e.target.closest('[data-hour]');
            if (!cell) return;

            if (cell.dataset.date) {
                selectedDate = cell.dataset.date;
            } else if (cell.dataset.hour) {
                selectedHour = cell.dataset.hour;
                const yearMatch = window.location.pathname.match(/\/(20\d{2})\//);
                const monthMatch = window.location.pathname.match(/\/(\d{1,2})\//);
                const dayMatch = window.location.pathname.match(/\/(\d{1,2})$/);
                if (yearMatch && monthMatch && dayMatch) {
                    selectedDate = `${yearMatch[1]}-${String(monthMatch[1]).padStart(2, '0')}-${String(dayMatch[1]).padStart(2, '0')}`;
                }
            }

            if (selectedDate) {
                document.getElementById('eventDate').value = selectedDate;
                document.getElementById('startDate').value = selectedDate;
                document.getElementById('endDate').value = selectedDate;
                if (selectedHour) {
                    document.getElementById('startTime').value = `${selectedHour.padStart(2, '0')}:00`;
                }
                modal.show();
                // ENSURE BACKDROP REMOVES ON HIDE
                modal._element.addEventListener('hidden.bs.modal', () => {
                    document.querySelectorAll('.modal-backdrop').forEach(backdrop => {
                        backdrop.remove();
                    });
                    document.body.classList.remove('modal-open');
                    document.body.style.overflow = '';
                    document.body.style.paddingRight = '';
                });
            }
        });
    });

    // === SUBMIT HANDLER — ONLY ONCE ===
    const form = document.getElementById('eventForm');
    if (form && !form.dataset.listenerAttached) {
        form.dataset.listenerAttached = 'true'; // MARK AS ATTACHED

        form.addEventListener('submit', (e) => {
            e.preventDefault();
            const data = {
                title: document.getElementById('eventTitle').value,
                start_date: document.getElementById('startDate').value,
                end_date: document.getElementById('endDate').value,
                start_time: document.getElementById('allDay').checked ? null : document.getElementById('startTime').value,
                end_time: document.getElementById('allDay').checked ? null : document.getElementById('endTime').value,
                all_day: document.getElementById('allDay').checked,
                is_recurring: document.getElementById('recurring').checked,
                recurrence_rule: document.getElementById('recurring').checked ? document.getElementById('recurrenceRule').value : null
            };

            fetch('/api/event', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            }).then(() => location.reload());
        });
    }

    // === RECURRING & ALL DAY (SAFE) ===
    document.getElementById('recurring')?.addEventListener('change', (e) => {
        document.getElementById('recurrenceOptions')?.classList.toggle('d-none', !e.target.checked);
    });

    document.getElementById('allDay')?.addEventListener('change', (e) => {
        const timeFields = document.querySelectorAll('#startTime, #endTime');
        timeFields.forEach(f => f.disabled = e.target.checked);
    });
});

// AFTER THE ADD EVENT LISTENER
document.querySelectorAll('.event-badge').forEach(badge => {
    badge.addEventListener('click', (e) => {
        e.stopPropagation();
        const eventId = badge.dataset.eventId;
        if (!eventId) return;

        fetch(`/api/event/${eventId}`)
            .then(res => res.json())
            .then(event => {
                document.getElementById('eventModalLabel').textContent = 'Edit Event';
                document.getElementById('eventTitle').value = event.title;
                document.getElementById('startDate').value = event.start_date;
                document.getElementById('endDate').value = event.end_date;
                document.getElementById('startTime').value = event.start_time || '';
                document.getElementById('endTime').value = event.end_time || '';
                document.getElementById('allDay').checked = event.all_day;
                document.getElementById('recurring').checked = event.is_recurring;
                document.getElementById('recurrenceRule').value = event.recurrence_rule || 'daily';

                // SHOW DELETE BUTTON
                let deleteBtn = document.getElementById('deleteEventBtn');
                if (!deleteBtn) {
                    deleteBtn = document.createElement('button');
                    deleteBtn.id = 'deleteEventBtn';
                    deleteBtn.className = 'btn btn-danger';
                    deleteBtn.textContent = 'Delete';
                    deleteBtn.type = 'button';
                    document.querySelector('#eventForm .modal-footer').appendChild(deleteBtn);
                }
                deleteBtn.onclick = () => {
                    if (confirm('Delete this event?')) {
                        fetch(`/api/event/${eventId}`, { method: 'DELETE' })
                            .then(() => location.reload());
                    }
                };

                modal.show();
                // ENSURE BACKDROP REMOVES ON HIDE
                modal._element.addEventListener('hidden.bs.modal', () => {
                    document.querySelectorAll('.modal-backdrop').forEach(backdrop => {
                        backdrop.remove();
                    });
                    document.body.classList.remove('modal-open');
                    document.body.style.overflow = '';
                    document.body.style.paddingRight = '';
                });
            });
    });
});