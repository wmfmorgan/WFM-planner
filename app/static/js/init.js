// static/js/init.js
import { initEventModal } from './calendar/events.js';
import { initTimeSlotClicks } from './calendar/time-slots.js';
import { initScheduleCollapse, autoScrollToNow } from './calendar/schedule.js';
import { initTaskKanban, initAddTaskForm } from './kanban/tasks.js';

document.addEventListener('DOMContentLoaded', () => {
  initEventModal();
  initTimeSlotClicks();
  initScheduleCollapse();
  autoScrollToNow();
  initTaskKanban();
  initAddTaskForm();
});