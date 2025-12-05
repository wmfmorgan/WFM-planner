# PROJECT.md — WFM PLANNER (2025 Goal Domination System)

> **“Train. Plan. DOMINATE.”**  
> A private, offline-first, pure-white personal operating system built for people who are serious about winning 2025 and beyond.

Last updated: 2025-12-04

## 1. Summary & Core Functionality
WFM Planner is a full-life management system that combines:
- Hierarchical Goals (Annual → Quarterly → Monthly → Weekly → Daily)
- Full Calendar (Year / Quarter / Month / Week / Day views)
- 30-minute Daily Schedule Grid (5 AM – 11 PM)
- Kanban Task System (To Do / In Progress / Blocked / Done + Backlog)
- Autosaving Prep / Notes / Wins / Improve at every time horizon
- Event Management (single + recurring, all-day)
- Category filtering, drag-and-drop reordering, live inline editing
- Full JSON export / import (preserves goal tree)
- Database backup / restore
- Zero external dependencies — runs locally or self-hosted forever

## 2. High-Level Architecture (Mermaid)
```mermaid
graph TD
    A[Browser] -->|HTTPS / HTTP| B(Flask App)
    B --> C[SQLite DB (wfm_planner.db)]
    B --> D[instance/backups/]
    B --> E[static/ (CSS + JS + images)]

    subgraph Routes & Views
        B --> R1[index, year, quarter, month, week, day, goals]
        B --> R2[API: /api/goals, /api/task, /api/event, /api/note, /api/import-calendar]
        B --> R3[Backup / Restore / Export / Import]
    end

    subgraph Frontend
        F[Bootstrap 5.3 + Bootstrap Icons] --> G[Custom CSS (pure white)]
        F --> H[Vanilla JS modules + Sortable.js]
    end
    A --> F
```

## 3. Tech Stack & Versions (Dec 2025)
| Layer          | Technology                     | Version / Note                                    |
|----------------|--------------------------------|---------------------------------------------------|
| Backend        | Python                         | 3.11+                                             |
| Framework      | Flask                          | 3.x                                               |
| ORM            | Flask-SQLAlchemy               | Latest                                            |
| Migrations     | Flask-Migrate (Alembic)        | Latest                                            |
| Templating     | Jinja2                         | Built-in                                          |
| Auth           | HTTP Basic Auth + Flask-Limiter| Rate-limited + admin bypass                       |
| Database       | SQLite                         | Single-file, zero-config                          |
| Frontend       | Bootstrap 5.3 + Bootstrap Icons| CDN                                               |
| JS Libraries   | Sortable.js 1.15               | Drag-and-drop                                     |
| CSS            | Custom (1200+ lines)           | Pure white, no dark mode, heavy !important       |
| Deployment     | Any WSGI server                | Works on Raspberry Pi, VPS, Docker, or localhost |

## 4. Folder Structure
```
wfm-planner/
├── app/
│   ├── __init__.py
│   ├── forms.py
│   ├── models.py
│   ├── routes.py
│   ├── static/
│   │   ├── css/style.css
│   │   └── js/ (all modular files)
│   └── templates/
├── instance/
│   ├── wfm_planner.db
│   └── backups/
├── migrations/
├── Sources/PROJECT.md       ← YOU ARE HERE
└── run.py / wsgi.py
```

## 5. Key Decisions & Rationale
- SQLite → zero setup, portable
- Vanilla JS + Bootstrap → lightning fast, no build step
- Pure white UI → uncompromising aesthetic
- Unified kanban for goals & tasks → consistent UX
- Autosave everywhere → zero friction
- Full JSON export/import with tree repair → data ownership

## 6. Architectural Tenets (The Sacred Rules)
1. **No inline JS** – All JavaScript lives in `static/js/`, modular, importable.
2. **No inline CSS** – All styles live in `static/css/`. No `<style>` blocks, no `style=""`.
3. **One source of truth for strings & magic values** – Colors, statuses, categories → constants in Python & mirrored in JS.
4. **All user input goes through JSON API** – Even classic forms end up as `fetch(..., JSON)`.
5. **All state-changing endpoints return JSON** – Never HTML snippets or redirects from API routes.
6. **Zero global variables in JS** – Everything scoped inside modules.
7. **Templates are dumb** – Jinja only loops & conditionals. No business logic.
8. **Database writes happen in one place** – Service functions or repository pattern.
9. **All flash messages come from the backend** – Never client-side `alert()` for server errors.
10. **Pure white is the default and only mode** – Dark mode only as opt-in override.
11. **No external build step** – No Webpack, no npm scripts required.
12. **Every new feature must work offline-first** – PWA-ready from day one.
13. **Data ownership is sacred** – Full export/import must always work perfectly.
14. **If it hurts maintainability, it gets refactored before merge** – Long functions, copy-paste = red flag.
15. **Hulkamania runs eternal** – Must still work in 10 years with zero dependency updates.
16. **Comments must be championship-caliber**  
    Every JS module, Python service file, and complex template block shall carry enough clear, sectioned comments that a brand-new warrior (or future AI Hulkster) can pick it up cold in 2035 and instantly know:
    - What the file owns
    - Why it exists
    - How the major sections flow
    - Any non-obvious tricks or gotchas  
    We don’t comment every line — we comment like architects dropping blueprints on the announce table. Headers, responsibilities, and section breaks only. If a future brother has to guess, we failed.  
    Hulkamania-level commenting runs eternal.

**Break any of these and the Hulkster will personally leg-drop your PR.**

## 7. Tenets Compliance Checklist
| Tenet                        | Status       | Notes                                           |
|------------------------------|--------------|-------------------------------------------------|
| No inline JS                 | In Progress  | goals.html still has ~250 lines                 |
| No inline CSS                | In Progress  | Small <style> in base.html                      |
| One source of truth          | Not Started  | Need constants.py + constants.js                |
| All user input via JSON API  | Mostly Done  | Only Quick FAB still uses classic form          |
| JSON responses from API      | Done         | All /api/ routes return JSON                    |
| Zero global JS vars          | Done         | All modules are clean                           |
| Dumb templates               | Mostly Done  | Some complex Jinja in day.html                  |
| DB writes centralized        | Not Started  | Still raw db.session.add() everywhere           |
| Flash from backend           | Done         | All errors use flash()                          |
| Pure white default           | Done         | And it will stay that way                       |
| No build step                | Done         | Forever                                         |
| Offline-first                | In Progress  | Needs manifest + service worker                 |
| Data ownership               | Done         | Import/export works perfectly                   |
| Maintainability first        | In Progress  | CSS & long routes are current targets           |
| Hulkamania eternal           | Done         | This app will outlive us all                    |

## 8. Known Technical Debt & Refactor Targets
| Priority | File / Location                         | Debt Description                                    | Target Fix |
|----------|-----------------------------------------|-----------------------------------------------------|------------|
| 1        | templates/goals.html                    | ~250 lines of inline JS                             | → static/js/goals.js |
| 2        | static/css/style.css                    | 1200-line monolith, !important hell                | Split + variables |
| 3        | routes.py (day_page, week_page)         | 300+ line god-functions                             | Break into services |
| 4        | Duplicate toast/import logic            | day/week/month.html                                 | → utils.js |
| 5        | Quick-task FAB form                     | Classic POST instead of JSON                        | Convert to fetch |
| 6        | Hard-coded colors / statuses            | Scattered everywhere                                | constants.py + js |

## 9. File Inventory & Responsibility Map
| File                              | Owns                                                            |
|-----------------------------------|-----------------------------------------------------------------|
| static/js/kanban/standard.js      | All drag-drop, live add, ranking, backlog pull                 |
| static/js/kanban/task-flyout.js   | Full task details modal + live save                             |
| static/js/calendar/events.js      | Event modal, click-to-add, recurring toggle                     |
| static/js/calendar/schedule.js    | Collapse state, auto-scroll, calendar import button             |
| static/js/calendar/time-slots.js  | Click time slot → pre-fill event modal                          |
| static/js/calendar/calendar-day.js| Layout overlapping events in day grid                           |
| templates/task_flyout.html        | Task flyout modal                                               |
| templates/kanban_board.html       | Reusable kanban (goals + tasks)                                 |
| templates/goals.html              | Hierarchical goal tree + inline editing (soon to be extracted) |

## 10. API Contract Summary
| Method | Endpoint                        | Request Body                              | Response                     |
|--------|---------------------------------|-------------------------------------------|------------------------------|
| POST   | /api/task                       | {description, date?, category?, backlog?} | {id, description}            |
| PUT    | /api/task/<id>                  | {description, date?, category?, status?, notes?} | success |
| DELETE | /api/task/<id>                  | —                                         | success                      |
| POST   | /api/task/<id>/status           | {status}                                  | success                      |
| POST   | /api/task/<id>/today            | —                                         | success (pulls to today)     |
| POST   | /api/goals                      | Goal JSON                                 | {success, goal}              |
| PUT    | /api/goals/<id>                 | Goal JSON                                 | {success, goal}              |
| DELETE | /api/goals/<id>                 | —                                         | success (cascades)           |
| POST   | /api/goals/<id>/subgoal         | Goal JSON                                 | {success, goal}              |
| POST   | /api/note/<key>                 | {content, completed?}                     | {status: saved}              |
| GET    | /api/note/<key>                 | —                                         | {content, completed}         |
| GET/POST| /api/import-calendar/<datestr> | —                                         | Import count + toast         |

## 11. Dependency Pinning Plan
- Bootstrap 5.3.3 CDN (locked URL)
- Bootstrap Icons 1.11.0 CDN
- Sortable.js 1.15.0 CDN
- Local fallbacks already in static/ for offline use

## 12. Testing Strategy
- Critical paths manually tested on every change:
  → Goal hierarchy import/export
  → Drag-and-drop ranking persistence
  → Autosave recovery after crash
  → Calendar import no-duplicates
- Future: add pytest + Playwright suite when we hit v2

## 13. Roadmap / Next Milestones
- Extract all inline JS
- Split & refactor CSS
- Create shared utils.js (toast + import)
- Refactor long route functions
- Add CSRF to remaining forms
- Docker + one-click deploy
- Mobile PWA support

## 14. Open Questions
- Configurable categories?
- Native recurring events?
- Global search?
- Dark mode toggle?

**OHHHHH YEAHHHH!** This is the championship blueprint.  
The belt is locked, the rules are set, and Hulkamania is running wild.

Let’s go dominate 2025, brother.