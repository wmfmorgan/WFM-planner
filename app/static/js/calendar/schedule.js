// static/js/calendar/schedule.js
export function initScheduleCollapse() {
  const collapse = document.getElementById('scheduleCollapse');
  const btn = document.querySelector('[data-bs-target="#scheduleCollapse"]');
  if (!collapse || !btn) return;

  // Restore saved state on load
  const saved = localStorage.getItem('scheduleCollapsed');
  if (saved === 'true') {
    collapse.classList.remove('show');
    btn.classList.add('collapsed');
    btn.setAttribute('aria-expanded', 'false');
  } else if (saved === 'false') {
    collapse.classList.add('show');
    btn.classList.remove('collapsed');
    btn.setAttribute('aria-expanded', 'true');
  }
  // If no saved state → defaults to collapsed (your current HTML)

  // Save state AFTER Bootstrap finishes toggling
  collapse.addEventListener('shown.bs.collapse', () => {
    localStorage.setItem('scheduleCollapsed', 'false'); // now open
  });

  collapse.addEventListener('hidden.bs.collapse', () => {
    localStorage.setItem('scheduleCollapsed', 'true');  // now closed
  });
}

export function autoScrollToNow() {
  const container = document.getElementById('schedule-container');
  const dayDate = document.getElementById('dayDateData')?.textContent.trim();
  if (!container || !dayDate || dayDate !== new Date().toISOString().slice(0,10)) return;

  const now = new Date();
  const h = now.getHours();
  const m = Math.ceil(now.getMinutes() / 30) * 30;
  const row = document.querySelector(`[data-hour="${h}"][data-minutes="${m === 60 ? 0 : m}"]`);
  if (row) {
    setTimeout(() => {
      container.scrollTop = row.offsetTop - container.offsetTop - 100;
    }, 150);
  }
}