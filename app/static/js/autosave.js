// app/static/js/autosave.js — CLEAN, FAST, BULLETPROOF
document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('.autosave').forEach(textarea => {
        const { scope, year, quarter, month, week, day, type, time, index } = textarea.dataset;

        const parts = ['note', scope, year];
        if (quarter) parts.push(quarter);
        if (month) parts.push(month);
        if (week) parts.push(week);
        if (day) parts.push(day);
        parts.push(type);
        if (time) parts.push(time);
        if (index !== undefined) parts.push(index);
        const key = parts.join('-');

        // LOAD
        fetch(`/api/note/${key}`)
            .then(r => r.ok ? r.json() : { content: '' })
            .then(data => textarea.value = data.content || '')
            .catch(() => {});

        // SAVE — DEBOUNCED
        let timeout;
        textarea.addEventListener('input', function() {
            clearTimeout(timeout);
            timeout = setTimeout(() => {
                fetch(`/api/note/${key}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ content: this.value })
                })
                .catch(err => console.warn('Autosave failed:', err));
            }, 300);
        });
    });
});