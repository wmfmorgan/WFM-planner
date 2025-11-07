document.addEventListener('DOMContentLoaded', () => {
    const modal = new bootstrap.Modal(document.getElementById('eventModal'));
    let selectedDate = null;
    let selectedHour = null; // ← ADD THIS

    // CLICK + ADD EVENT — SUPPORT ALL PAGES
    document.querySelectorAll('.add-event-area').forEach(area => {
        area.addEventListener('click', (e) => {
            e.stopPropagation();
            //console.log('Add Event clicked:', area);

            const cell = e.target.closest('.calendar-day') || e.target.closest('[data-hour]');
            if (!cell) return;

            // GET DATE
            if (cell.dataset.date) {
                selectedDate = cell.dataset.date;
            } else if (cell.dataset.hour) {
                selectedHour = cell.dataset.hour;
                // GET DATE FROM URL OR HIDDEN INPUT
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

    // RECURRING & ALL DAY
    document.getElementById('recurring')?.addEventListener('change', (e) => {
        document.getElementById('recurrenceOptions')?.classList.toggle('d-none', !e.target.checked);
    });

    document.getElementById('allDay')?.addEventListener('change', (e) => {
        const timeFields = document.querySelectorAll('#startTime, #endTime');
        timeFields.forEach(f => f.disabled = e.target.checked);
    });

    // SUBMIT FORM
    document.getElementById('eventForm')?.addEventListener('submit', (e) => {
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
});