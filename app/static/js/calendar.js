document.addEventListener('DOMContentLoaded', () => {
    const modal = new bootstrap.Modal(document.getElementById('eventModal'));
    let selectedDate = null;
    let selectedHour = null;

    // MONTHLY/WEEKLY: CLICK CELL
    document.querySelectorAll('.calendar-day[data-date] .add-event-area').forEach(area => {
        area.addEventListener('click', (e) => {
            const cell = e.target.closest('.calendar-day');
            selectedDate = cell.dataset.date;
            document.getElementById('eventDate').value = selectedDate;
            document.getElementById('startDate').value = selectedDate;
            document.getElementById('endDate').value = selectedDate;
            modal.show();
        });
    });

    // DAILY PAGE: CLICK HOUR ROW
    document.querySelectorAll('.add-event-area[data-hour]').forEach(area => {
        area.addEventListener('click', (e) => {
            selectedHour = e.target.dataset.hour;
            const dateInput = document.querySelector('input[name="year"], input[type="hidden"][value*="2025"]');
            const year = {{ year }};
            const month = {{ month }};
            const day = {{ day }};
            selectedDate = `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;

            document.getElementById('eventDate').value = selectedDate;
            document.getElementById('startDate').value = selectedDate;
            document.getElementById('endDate').value = selectedDate;
            document.getElementById('startTime').value = `${selectedHour.padStart(2, '0')}:00`;
            modal.show();
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

// DAILY PAGE: CLICK + ADD IN HOUR
document.querySelectorAll('.add-event-area[data-hour]').forEach(area => {
    area.addEventListener('click', (e) => {
        const hour = e.target.dataset.hour;
        const date = document.querySelector('.calendar-day[data-date]')?.dataset.date || 
                     `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
        document.getElementById('eventDate').value = date;
        document.getElementById('startDate').value = date;
        document.getElementById('endDate').value = date;
        document.getElementById('startTime').value = `${hour.padStart(2, '0')}:00`;
        document.getElementById('eventHour').value = hour;
        modal.show();
    });
});