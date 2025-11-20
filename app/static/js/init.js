// app/static/js/init.js
import { initEventModal } from './calendar/events.js';
import { initTimeSlotClicks } from './calendar/time-slots.js';
import { initScheduleCollapse, autoScrollToNow } from './calendar/schedule.js';
import { initKanban } from './kanban/standard.js';  // NEW UNIFIED
import { initDayCalendar } from './calendar/calendar-day.js';

document.addEventListener('DOMContentLoaded', () => {
  initEventModal();
  initTimeSlotClicks();
  initScheduleCollapse();
  autoScrollToNow();
  initKanban();  // NEW — handles both goals and tasks
});

document.addEventListener('DOMContentLoaded', function () {
  // All page-specific inits go here
  initDayCalendar();
});