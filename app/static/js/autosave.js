// app/static/js/autosave.js — FINAL, CLEAN, UNBREAKABLE
document.addEventListener('DOMContentLoaded', function () {

    document.querySelectorAll('.autosave').forEach(textarea => {
        const { scope, year, quarter, month, week, day, type, time, index } = textarea.dataset;

        // YOUR SACRED KEY LOGIC — 100% UNTOUCHED, BROTHER!
        const parts = ['note', scope, year];
        if (quarter) parts.push(quarter);
        if (month) parts.push(month);
        if (week) parts.push(week);
        if (day) parts.push(day);
        parts.push(type);
        if (time) parts.push(time);
        if (index !== undefined) parts.push(index);
        const key = parts.join('-');

        // === LOAD NOTE — CREDENTIALS INCLUDED AUTOMATICALLY ===
        fetch(`/api/note/${key}`, { credentials: 'include' })
            .then(r => r.ok ? r.json() : Promise.reject())
            .then(data => {
                textarea.value = data.content || '';
            })
            .catch(() => {
                // Silently fail — just leave empty
                textarea.value = '';
            });

        // === SAVE NOTE — DEBOUNCED & UNLIMITED ===
        let timeout;
        textarea.addEventListener('input', function () {
            clearTimeout(timeout);
            timeout = setTimeout(() => {
                fetch(`/api/note/${key}`, {
                    method: 'POST',
                    credentials: 'include',  // This sends your Basic Auth automatically
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ content: this.value })
                })
                .then(r => {
                    if (!r.ok) console.warn('Autosave failed:', r.status);
                    // else console.log('Saved like a champ!');
                })
                .catch(err => console.warn('Autosave failed:', err));
            }, 300);
        });
    });
});