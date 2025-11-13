/* --------------------------------------------------------------
   calendar.js – all day-page logic in ONE place
   -------------------------------------------------------------- */
document.addEventListener('DOMContentLoaded', () => {
    // GLOBAL TASK ADD GUARD — BLOCKS DUPES

    let isSubmittingTask = false;
    //const debugLog = (msg) => console.log(`[TASK ADD] ${msg}`);
    
    // -----------------------------------------------------------------
    // 1. CONFIG – these values are injected by the Flask template
    // -----------------------------------------------------------------
    const apiBase   = '/api';
    const dayDate = (function() {
    const el = document.getElementById('dayDateData');
        return el ? el.textContent.replace(/\s/g, '') : '';
    })();
    const isToday   = (new Date().toISOString().slice(0,10) === dayDate);

    // -----------------------------------------------------------------
    // 2. DOM ELEMENTS
    // -----------------------------------------------------------------
    const modalEl   = document.getElementById('eventModal');
    const modal     = new bootstrap.Modal(modalEl);
    const form      = document.getElementById('eventForm');
    const titleEl   = document.getElementById('eventModalLabel');

    let editingEventId = null;

    // -----------------------------------------------------------------
    // 3. HELPERS
    // -----------------------------------------------------------------
    const pad = n => n.toString().padStart(2, '0');

    const resetModal = () => {
        editingEventId = null;
        titleEl.textContent = 'Add Event';
        form.reset();
        document.getElementById('startTime').disabled = false;
        document.getElementById('endTime').disabled   = false;
        document.getElementById('recurrenceOptions').classList.add('d-none');
        const del = document.getElementById('deleteEventBtn');
        if (del) del.remove();
    };

    // -----------------------------------------------------------------
    // 4+5. SINGLE CLICK HANDLER – ADD OR EDIT (NO DUPLICATES)
    // -----------------------------------------------------------------
    let isProcessingClick = false;
    let clickDebugId = 0;

    document.addEventListener('click', e => {
        const debugId = ++clickDebugId;
        //console.log(`[DEBUG ${debugId}] Click detected. isProcessingClick = ${isProcessingClick}`);

        if (isProcessingClick) {
            //console.log(`[DEBUG ${debugId}] BLOCKED – already processing`);
            return;
        }

        // --- 1. EDIT EVENT (badge) ---
        const badge = e.target.closest('.event-badge[data-event-id]');
        if (badge) {
            //console.log(`[DEBUG ${debugId}] EDIT badge clicked (id=${badge.dataset.eventId})`);
            isProcessingClick = true;
            e.stopPropagation();

            const id = badge.dataset.eventId;
            fetch(`${apiBase}/event/${id}`)
                .then(r => r.json())
                .then(ev => {
                    //console.log(`[DEBUG ${debugId}] EDIT loaded – opening modal`);
                    editingEventId = ev.id;
                    titleEl.textContent = 'Edit Event';

                    form.reset();
                    document.getElementById('eventTitle').value = ev.title || '';
                    document.getElementById('startDate').value  = ev.start_date;
                    document.getElementById('endDate').value    = ev.end_date;
                    document.getElementById('startTime').value = ev.start_time || '';
                    document.getElementById('endTime').value   = ev.end_time   || '';

                    const allDay = ev.all_day;
                    document.getElementById('allDay').checked = allDay;
                    document.getElementById('startTime').disabled = allDay;
                    document.getElementById('endTime').disabled   = allDay;

                    document.getElementById('recurring').checked = ev.is_recurring || false;
                    document.getElementById('recurrenceOptions')
                        .classList.toggle('d-none', !ev.is_recurring);
                    if (ev.recurrence_rule) {
                        document.getElementById('recurrenceRule').value = ev.recurrence_rule;
                    }

                    // Delete button
                    let del = document.getElementById('deleteEventBtn');
                    if (!del) {
                        del = document.createElement('button');
                        del.id = 'deleteEventBtn';
                        del.type = 'button';
                        del.className = 'btn btn-danger';
                        del.textContent = 'Delete';
                        modalEl.querySelector('.modal-footer').appendChild(del);
                    }
                    del.onclick = () => {
                        if (confirm('Delete this event?')) {
                            fetch(`${apiBase}/event/${id}`, {method: 'DELETE'})
                                .then(() => location.reload());
                        }
                    };

                    modal.show();
                })
                .catch(err => {
                    console.error(`[DEBUG ${debugId}] Load event failed`, err);
                    alert('Could not load event.');
                })
                .finally(() => {
                    // Re-enable after modal is fully shown
                    modalEl.addEventListener('shown.bs.modal', () => {
                        //console.log(`[DEBUG ${debugId}] Modal shown – re-enabling clicks`);
                        isProcessingClick = false;
                    }, { once: true });
                });
            return;
        }

        // --- 3. ADD EVENT FROM MONTH (+ Add Event) ---
        const addArea = e.target.closest('.add-event-area');
        if (addArea) {
            isProcessingClick = true;
            e.stopPropagation();

            const cell = addArea.closest('.calendar-day');
            if (!cell || !cell.dataset.date) {
                isProcessingClick = false;
                return;
            }

            const dateStr = cell.dataset.date;

            resetModal();
            modal.show();

            modalEl.addEventListener('shown.bs.modal', function fillForm() {
                document.getElementById('eventDate').value = dateStr;
                document.getElementById('startDate').value = dateStr;
                document.getElementById('endDate').value   = dateStr;
                document.getElementById('startTime').value = '09:00';
                document.getElementById('endTime').value   = '10:00';
                this.removeEventListener('shown.bs.modal', fillForm);
                isProcessingClick = false;
            }, { once: true });

            return;
        }

        // --- 2. ADD EVENT (time slot) ---
        const slot = e.target.closest('.schedule-time-slot');
        if (!slot) {
            //console.log(`[DEBUG ${debugId}] No slot or badge – ignoring`);
            return;
        }

        //console.log(`[DEBUG ${debugId}] ADD slot clicked (${slot.dataset.hour}:${slot.dataset.minutes})`);
        isProcessingClick = true;
        e.stopPropagation();

        const hour    = parseInt(slot.dataset.hour, 10);
        const minutes = parseInt(slot.dataset.minutes, 10) || 0;

        resetModal();
        modal.show();

        modalEl.addEventListener('shown.bs.modal', function fillForm() {
            //console.log(`[DEBUG ${debugId}] ADD modal shown – filling form`);
            document.getElementById('eventDate').value = dayDate;
            document.getElementById('startDate').value = dayDate;
            document.getElementById('endDate').value   = dayDate;
            document.getElementById('startTime').value = `${pad(hour)}:${pad(minutes)}`;
            const endH = (hour + (minutes >= 30 ? 1 : 0)) % 24;
            const endM = minutes >= 30 ? 0 : 30;
            document.getElementById('endTime').value = `${pad(endH)}:${pad(endM)}`;
            this.removeEventListener('shown.bs.modal', fillForm);
            isProcessingClick = false;
        }, { once: true });
    });    
    // -----------------------------------------------------------------
    // 6. ALL-DAY / RECURRING TOGGLES
    // -----------------------------------------------------------------
    document.getElementById('allDay').addEventListener('change', e => {
        const disabled = e.target.checked;
        document.getElementById('startTime').disabled = disabled;
        document.getElementById('endTime').disabled   = disabled;
        if (disabled) {
            document.getElementById('startTime').value = '';
            document.getElementById('endTime').value   = '';
        }
    });

    document.getElementById('recurring').addEventListener('change', e => {
        document.getElementById('recurrenceOptions')
            .classList.toggle('d-none', !e.target.checked);
    });

    // -----------------------------------------------------------------
    // 7. FORM SUBMIT – CREATE OR UPDATE (ONLY ONCE)
    // -----------------------------------------------------------------
    if (!form.dataset.submitListenerAttached) {
        form.dataset.submitListenerAttached = 'true';

        form.addEventListener('submit', e => {
            e.preventDefault();

            const allDay = document.getElementById('allDay').checked;
            const payload = {
                title:          document.getElementById('eventTitle').value.trim(),
                start_date:     document.getElementById('startDate').value,
                end_date:       document.getElementById('endDate').value,
                all_day:        allDay,
                start_time:     allDay ? null : document.getElementById('startTime').value,
                end_time:       allDay ? null : document.getElementById('endTime').value,
                is_recurring:   document.getElementById('recurring').checked,
                recurrence_rule: document.getElementById('recurring').checked
                                   ? document.getElementById('recurrenceRule').value
                                   : null
            };

            const method = editingEventId ? 'PUT' : 'POST';
            const url    = editingEventId ? `${apiBase}/event/${editingEventId}` : `${apiBase}/event`;

            //console.log(`[SUBMIT] ${method} → ${url}`, payload);

            fetch(url, {
                method,
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            })
            .then(r => {
                if (!r.ok) throw r;
                //console.log('[SUBMIT] Success – reloading');
                location.reload();
            })
            .catch(err => {
                console.error('[SUBMIT] Failed:', err);
                alert('Failed to save event.');
            });
        });
    }

    // -----------------------------------------------------------------
    // 8. MODAL CLEAN-UP
    // -----------------------------------------------------------------
    modalEl.addEventListener('hidden.bs.modal', () => {
        resetModal();
        document.querySelectorAll('.modal-backdrop').forEach(b => b.remove());
        document.body.classList.remove('modal-open');
        document.body.style.overflow = '';
        document.body.style.paddingRight = '';
    });

    // -----------------------------------------------------------------
    // 9. KANBAN DRAG-AND-DROP
    // -----------------------------------------------------------------
    let dragged = null;
    const allow = e => e.preventDefault();
    const start = e => {
        dragged = e.target;
        e.dataTransfer.setData('text/plain', e.target.dataset.taskId);
        setTimeout(() => e.target.classList.add('dragging'), 0);
    };

    document.addEventListener('dragover', allow);
    document.addEventListener('drop', e => {
        e.preventDefault();
        if (!dragged) return;
        const col = e.target.closest('.kanban-col');
        if (!col) return;

        const taskId = dragged.dataset.taskId;
        const status = col.dataset.status;

        dragged.classList.remove('dragging');
        col.querySelector('.task-list').appendChild(dragged);

        fetch(`${apiBase}/task/${taskId}/status`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({status})
        }).catch(console.error);
    });

    document.querySelectorAll('.task-card[draggable="true"]')
            .forEach(c => c.addEventListener('dragstart', start));

// ——— REPLACE YOUR CURRENT add-task-form LISTENER WITH THIS ———
document.querySelectorAll('#add-task-form').forEach((form, index) => {
    //debugLog(`Binding submit listener to form #${index}`);

    form.addEventListener('submit', function(e) {
        e.preventDefault();
        e.stopImmediatePropagation(); // KILL ANY OTHER LISTENERS

        const input = this.querySelector('.add-task-input');
        const desc = input?.value.trim() || '';
        const formId = this.id || 'unknown';

        //debugLog(`Form submit triggered: "${desc}" (form: ${formId})`);

        if (!desc) {
            //debugLog('Blocked: empty description');
            return;
        }
        if (isSubmittingTask) {
            //debugLog('BLOCKED: already submitting');
            alert('Please wait — task is being added.');
            return;
        }

        isSubmittingTask = true;
        //debugLog('SUBMITTING TASK...');

        const [y, m, d] = dayDate.split('-');
        fetch(`${apiBase}/task`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ description: desc, year: +y, month: +m, day: +d })
        })
        .then(r => {
            if (!r.ok) throw new Error(`HTTP ${r.status}`);
            return r.json();
        })
        .then(data => {
            //debugLog(`SUCCESS: Task ID ${data.id}`);
            const list = document.querySelector('[data-status="todo"] .task-list');
            const card = document.createElement('div');
            card.className = 'task-card bg-white p-3 rounded shadow-sm border';
            card.draggable = true;
            card.dataset.taskId = data.id;
            card.innerHTML = `<div class="task-desc fw-medium">${desc}</div>`;
            card.addEventListener('dragstart', start);
            list.appendChild(card);
            input.value = '';
            input.focus();
        })
        .catch(err => {
            //debugLog(`ERROR: ${err.message}`);
            alert('Failed to add task. Check console.');
            console.error(err);
        })
        .finally(() => {
            setTimeout(() => {
                isSubmittingTask = false;
                //debugLog('READY FOR NEXT ADD');
            }, 600);
        });
    });
});

// 11. AUTO-SCROLL TO CURRENT TIME (only on today)
    // -----------------------------------------------------------------
    const container = document.getElementById('schedule-container');
    if (container && isToday) {
        const now = new Date();
        const h   = now.getHours();
        const m   = Math.ceil(now.getMinutes() / 30) * 30;
        const row = document.querySelector(`[data-hour="${h}"][data-minutes="${m}"]`);
        if (row) {
            setTimeout(() => {
                container.scrollTop = row.offsetTop - container.offsetTop;
            }, 100);
        }
    }
    // Remember collapse state
    const scheduleCollapse = document.getElementById('scheduleCollapse');
    const collapseBtn = document.querySelector('[data-bs-target="#scheduleCollapse"]');

    if (localStorage.getItem('scheduleCollapsed') === 'true') {
        bootstrap.Collapse.getInstance(scheduleCollapse)?.hide();
    }

    collapseBtn.addEventListener('click', () => {
        const collapsed = scheduleCollapse.classList.contains('show');
        localStorage.setItem('scheduleCollapsed', collapsed ? 'true' : 'false');
    });

});

