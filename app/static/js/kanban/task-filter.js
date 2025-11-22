export function initTaskCategoryFilter() {
    const filters = document.querySelectorAll('.task-category-filter');
    if (filters.length === 0) return;

    // Populate all dropdowns
    fetch('/api/tasks/categories')
        .then(r => r.json())
        .then(categories => {
            filters.forEach(filter => {
                filter.innerHTML = '<option value="">All Categories</option>';
                categories.forEach(cat => {
                    const opt = document.createElement('option');
                    opt.value = cat;
                    opt.textContent = cat;
                    filter.appendChild(opt);
                });
            });
        });

    // GLOBAL FILTER — AFFECTS ALL TASKS ON PAGE
    document.addEventListener('change', e => {
        if (!e.target.classList.contains('task-category-filter')) return;

        const selected = e.target.value;

        // FILTER EVERY TASK CARD ON THE ENTIRE PAGE
        document.querySelectorAll('.kanban-item[data-item-id]').forEach(card => {
            const catBadge = card.querySelector('.task-category-badge');
            const cat = catBadge?.textContent.trim() || '';
            const shouldHide = selected && cat !== selected;
            card.classList.toggle('hidden', shouldHide);
        });
    });
}