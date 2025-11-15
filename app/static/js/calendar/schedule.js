// static/js/calendar/schedule.js
export function initScheduleCollapse() {
  const collapse = document.getElementById('scheduleCollapse');
  const btn = document.querySelector('[data-bs-target="#scheduleCollapse"]');
  if (!collapse || !btn) return;

  if (localStorage.getItem('scheduleCollapsed') === 'true') {
    bootstrap.Collapse.getInstance(collapse)?.hide();
  }

  btn.addEventListener('click', () => {
    const collapsed = collapse.classList.contains('show');
    localStorage.setItem('scheduleCollapsed', collapsed ? 'true' : 'false');
  });
}

export function autoScrollToNow() {
  const container = document.getElementById('schedule-container');
  const dayDate = document.getElementById('dayDateData')?.textContent.trim();
  if (!container || !dayDate || dayDate !== new Date().toISOString().slice(0,10)) return;

  const now = new Date();
  const h = now.getHours();
  const m = Math.ceil(now.getMinutes() / 30) * 30;
  const row = document.querySelector(`[data-hour="${h}"][data-minutes="${m}"]`);
  if (row) {
    setTimeout(() => {
      container.scrollTop = row.offsetTop - container.offsetTop;
    }, 100);
  }
}