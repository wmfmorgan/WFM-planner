// app/static/js/calendar-day.js
export function initDayCalendar(){
  const container = document.getElementById('eventContainer');
  if (!container) return;

  const events = Array.from(container.querySelectorAll('.raw-event'));

  events.forEach(ev => {
    ev.start = parseInt(ev.dataset.start);
    ev.end = parseInt(ev.dataset.end);
    ev.eventId = ev.dataset.id;
  });

  const columns = [];
  events.forEach(event => {
    let placed = false;
    for (let col of columns) {
      const overlaps = col.some(e => event.start < e.end && event.end > e.start);
      if (!overlaps) {
        col.push(event);
        placed = true;
        break;
      }
    }
    if (!placed) columns.push([event]);
  });

  const colCount = columns.length;
  if (colCount === 0) return;
  const width = 100 / colCount;

  columns.forEach((col, colIdx) => {
    col.forEach(eventEl => {
    const duration = eventEl.end - eventEl.start;

    eventEl.style.position = 'absolute';
    eventEl.style.top = eventEl.start + 'px';
    
    eventEl.style.height = Math.max(duration, 30) + 'px';   // ← THIS LINE
    eventEl.style.left = (colIdx * width + 1) + '%';
    eventEl.style.width = (width - 2) + '%';
    eventEl.style.zIndex = '20';

    // Optional: make text smaller on short events
    if (duration < 50) {
        eventEl.style.padding = '3px 8px';
        eventEl.style.fontSize = '0.75rem';
    }

    eventEl.setAttribute('data-event-id', eventEl.eventId);
    eventEl.classList.remove('raw-event');
    });
  });
};