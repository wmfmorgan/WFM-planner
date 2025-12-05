// app/static/js/utils.js
// GLOBAL UTILS — TOAST, CONFIRM, AND FUTURE MEGAPOWERS TOOLS
// NO GLOBALS, NO INLINE, PURE HULKAMANIA!

/**
 * Show a Bootstrap toast — used everywhere, brother!
 * @param {string} message 
 * @param {string} type - 'success' | 'danger' | 'warning' | 'info' (default: 'info')
 * @param {number} delay - ms before auto-hide (default: 4000)
 */
export function showToast(message, type = 'info', delay = 4000) {
  const toast = document.createElement('div');
  toast.className = `toast align-items-center text-bg-${type} border-0 position-fixed`;
  toast.style.top = '1rem';
  toast.style.right = '1rem';
  toast.style.zIndex = '9999';
  toast.style.minWidth = '280px';
  toast.style.boxShadow = '0 4px 12px rgba(0,0,0,0.15)';

  toast.innerHTML = `
    <div class="d-flex">
      <div class="toast-body fw-semibold">${message}</div>
      <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
    </div>
  `;

  document.body.appendChild(toast);
  const bsToast = new bootstrap.Toast(toast, { delay });
  bsToast.show();

  toast.addEventListener('hidden.bs.toast', () => toast.remove());
}