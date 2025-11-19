// app/static/js/calendar/time-slots.js
const pad = n => n.toString().padStart(2, '0');

export function initTimeSlotClicks() {
  document.addEventListener('click', e => {
    // Find the nearest time slot — even if event is on top
    let slot = e.target.closest('.time-slot-clickable');
    if (!slot) {
      // If clicked on an event, go up to find the time slot
      const event = e.target.closest('[data-event-id]');
      if (event) {
        slot = event.closest('.time-slot-clickable') || 
               event.parentElement.closest('.time-slot-clickable');
      }
    }
    if (!slot) return;

    e.stopPropagation();

    const hour = parseInt(slot.dataset.hour, 10);
    const minutes = parseInt(slot.dataset.minutes, 10) || 0;

    const modalEl = document.getElementById('eventModal');
    if (!modalEl) {
      console.error('Event modal not found!');
      return;
    }

    const modal = new bootstrap.Modal(modalEl);
    modal.show();

    modalEl.addEventListener('shown.bs.modal', () => {
      const dayDate = document.getElementById('dayDateData')?.textContent.trim() || 
                      new Date().toISOString().slice(0,10);

      const startInput = document.getElementById('startTime');
      const endInput = document.getElementById('endTime');
      const dateInputs = ['startDate', 'endDate'];

      if (startInput) startInput.value = `${pad(hour)}:${pad(minutes)}`;
      if (endInput) {
        const endH = minutes >= 30 ? hour + 1 : hour;
        const endM = minutes >= 30 ? 0 : 30;
        endInput.value = `${pad(endH)}:${pad(endM)}`;
      }

      dateInputs.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.value = dayDate;
      });

      // Focus title
      document.getElementById('eventTitle')?.focus();
    }, { once: true });
  });
}