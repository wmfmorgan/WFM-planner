// static/js/calendar/time-slots.js
const pad = n => n.toString().padStart(2, '0');

export function initTimeSlotClicks() {
  let isProcessing = false;

  document.addEventListener('click', e => {
    if (isProcessing) return;
    const slot = e.target.closest('.schedule-time-slot');
    if (!slot) return;

    isProcessing = true;
    e.stopPropagation();

    const hour = parseInt(slot.dataset.hour, 10);
    const minutes = parseInt(slot.dataset.minutes, 10) || 0;

    const modalEl = document.getElementById('eventModal');
    const modal = new bootstrap.Modal(modalEl);
    modal.show();

    modalEl.addEventListener('shown.bs.modal', function fill() {
      const dayDate = document.getElementById('dayDateData')?.textContent.trim() || new Date().toISOString().slice(0,10);
      document.getElementById('eventDate').value = dayDate;
      document.getElementById('startDate').value = dayDate;
      document.getElementById('endDate').value = dayDate;
      document.getElementById('startTime').value = `${pad(hour)}:${pad(minutes)}`;
      const endH = (hour + (minutes >= 30 ? 1 : 0)) % 24;
      const endM = minutes >= 30 ? 0 : 30;
      document.getElementById('endTime').value = `${pad(endH)}:${pad(endM)}`;
      this.removeEventListener('shown.bs.modal', fill);
      isProcessing = false;
    }, { once: true });
  });
}