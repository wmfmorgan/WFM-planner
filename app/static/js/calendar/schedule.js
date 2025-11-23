// static/js/calendar/schedule.js
// THE ULTIMATE SCHEDULE SCRIPT — FINAL VERSION — WORKS EVERY TIME

// 1. Schedule Collapse — Remembers open/closed state
export function initScheduleCollapse() {
  const collapse = document.getElementById('scheduleCollapse');
  const btn = document.querySelector('[data-bs-target="#scheduleCollapse"]');
  if (!collapse || !btn) return;

  const saved = localStorage.getItem('scheduleCollapsed');

  if (saved === 'true') {
    collapse.classList.remove('show');
    btn.classList.add('collapsed');
    btn.setAttribute('aria-expanded', 'false');
  } else {
    // Default: open (or if saved === 'false' or null)
    collapse.classList.add('show');
    btn.classList.remove('collapsed');
    btn.setAttribute('aria-expanded', 'true');
  }

  collapse.addEventListener('shown.bs.collapse', () => {
    localStorage.setItem('scheduleCollapsed', 'false');
  });

  collapse.addEventListener('hidden.bs.collapse', () => {
    localStorage.setItem('scheduleCollapsed', 'true');
  });
}

// 2. Auto-scroll to current time on today's page
export function autoScrollToNow() {
  const container = document.getElementById('scheduleGrid');
  const dayDateData = document.getElementById('dayDateData');
  if (!container || !dayDateData) return;

  const today = new Date().toISOString().slice(0, 10);
  const pageDate = `${dayDateData.dataset.year}-${String(dayDateData.dataset.month).padStart(2, '0')}-${String(dayDateData.dataset.day).padStart(2, '0')}`;

  if (pageDate !== today) return;

  const now = new Date();
  let hours = now.getHours();
  let minutes = now.getMinutes() < 30 ? 30 : 60;
  if (minutes === 60) {
    hours += 1;
    minutes = 0;
  }
  if (hours < 5) hours = 5; // Your schedule starts at 5 AM

  const targetSlot = document.querySelector(`.time-slot-clickable[data-hour="${hours}"][data-minutes="${minutes}"]`);
  if (targetSlot) {
    setTimeout(() => {
      container.scrollTo({
        top: targetSlot.offsetTop - 150,
        behavior: 'smooth'
      });
    }, 400);
  }
}

// 3. Toast notification system
function showToast(message, type = 'success') {
  // Remove old toasts
  document.querySelectorAll('.calendar-import-toast').forEach(t => t.remove());

  const toast = document.createElement('div');
  toast.className = `toast calendar-import-toast align-items-center text-bg-${type === 'danger' ? 'danger' : 'success'} border-0 position-fixed bottom-0 end-0 p-3 m-4`;
  toast.style.zIndex = '1080';
  toast.innerHTML = `
    <div class="d-flex">
      <div class="toast-body fw-medium">
        <i class="bi ${type === 'danger' ? 'bi-exclamation-triangle-fill' : 'bi-check-circle-fill'} me-2"></i>
        ${message}
      </div>
      <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast"></button>
    </div>
  `;

  document.body.appendChild(toast);
  const bsToast = new bootstrap.Toast(toast, { delay: 5000 });
  bsToast.show();

  toast.addEventListener('hidden.bs.toast', () => toast.remove());
}

// 4. MAIN EVENT: Import calendar for THIS day — WORKS 100%
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.js-import-calendar-btn').forEach(button => {
    button.addEventListener('click', async (e) => {
      e.preventDefault();
      e.stopPropagation();

      // console.log('Gear clicked! Starting calendar import...');

      const dayDateData = document.getElementById('dayDateData');
      if (!dayDateData) {
        showToast('Error: Cannot read date from page', 'danger');
        return;
      }

      const year = dayDateData.dataset.year;
      const month = String(dayDateData.dataset.month).padStart(2, '0');
      const day = String(dayDateData.dataset.day).padStart(2, '0');
      const datestr = `${year}${month}${day}`;

      // console.log('Importing calendar for:', datestr);

      const originalHTML = button.innerHTML;
      button.disabled = true;
      button.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';

      try {
        const response = await fetch(`/api/import-calendar/${datestr}`, {
          method: 'GET',
          headers: {
            'X-Requested-With': 'XMLHttpRequest'
          }
        });

        const data = await response.json();

        if (!response.ok) {
          throw new Error(data.error || `Server error: ${response.status}`);
        }

        if (data.success) {
          const count = data.imported || 0;
          showToast(`Calendar synced! ${count} event${count !== 1 ? 's' : ''} imported`, 'success');
          setTimeout(() => location.reload(), 1800);
        } else {
          throw new Error(data.error || 'Import failed');
        }
      } catch (err) {
        console.error('Calendar import failed:', err);
        showToast(err.message || 'Import failed — try again later', 'danger');
      } finally {
        button.disabled = false;
        button.innerHTML = originalHTML;
      }
    });
  });
});