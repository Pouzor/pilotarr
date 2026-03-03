# Test Coverage Report

> Generated: 2026-03-03 — v1.5.1
> Both suites: **500 backend tests passed / 451 frontend tests passed — 0 failures**

---

## Backend — pytest + coverage.py

**Total: 64% (2721 / 4276 statements)**
Python 3.14 · SQLite in-memory DB

| File | Stmts | Miss | Cover | Notes |
|------|------:|-----:|------:|-------|
| `app/core/config.py` | 17 | 0 | **100%** | |
| `app/core/security.py` | 21 | 10 | 52% | Cookie auth path untested |
| `app/models/models.py` | 241 | 0 | **100%** | |
| `app/models/enums.py` | 63 | 0 | **100%** | |
| `app/schemas.py` | 238 | 18 | 92% | |
| `app/api/routes/analytics.py` | 263 | 32 | 88% | |
| `app/api/routes/auth.py` | 34 | 1 | 97% | |
| `app/api/routes/jellyseerr.py` | 44 | 0 | **100%** | |
| `app/api/routes/prowlarr.py` | 48 | 0 | **100%** | |
| `app/api/routes/services.py` | 58 | 2 | 97% | |
| `app/api/routes/library.py` | 141 | 33 | 77% | |
| `app/api/routes/torrents.py` | 47 | 16 | 66% | |
| `app/api/routes/dashboard.py` | 66 | 34 | 48% | |
| `app/api/routes/monitoring.py` | 88 | 74 | 16% | |
| `app/api/routes/sync.py` | 168 | 111 | 34% | |
| `app/services/auth_service.py` | 45 | 9 | 80% | |
| `app/services/analytics_service.py` | 209 | 26 | 88% | |
| `app/services/torrent_enrichment_service.py` | 193 | 8 | 96% | |
| `app/services/radarr_connector.py` | 98 | 0 | **100%** | |
| `app/services/prowlarr_connector.py` | 76 | 0 | **100%** | |
| `app/services/base_connector.py` | 59 | 14 | 76% | |
| `app/services/metrics_service.py` | 81 | 29 | 64% | |
| `app/services/connector_factory.py` | 24 | 16 | 33% | |
| `app/services/jellyfin_connector.py` | 125 | 108 | 14% | Needs integration tests |
| `app/services/jellyfin_streams_service.py` | 115 | 103 | 10% | Needs integration tests |
| `app/services/jellyseerr_connector.py` | 55 | 45 | 18% | Needs integration tests |
| `app/services/qbittorrent_connector.py` | 177 | 151 | 15% | Needs integration tests |
| `app/services/sonarr_connector.py` | 154 | 125 | 19% | Needs integration tests |
| `app/schedulers/analytics_scheduler.py` | 53 | 0 | **100%** | |
| `app/schedulers/sync_service.py` | 615 | 81 | 87% | |
| `app/schedulers/scheduler.py` | 42 | 28 | 33% | |
| `app/main.py` | 51 | 13 | 75% | |
| `app/db.py` | 27 | 12 | 56% | |
| `app/db_migrations.py` | 422 | 355 | 16% | Migration scripts, low priority |
| `app/db_migrations_episodes.py` | 77 | 77 | 0% | Not tested |
| `app/apply_torrent_migration.py` | 24 | 24 | 0% | Not tested |

### Backend coverage by area

| Area | Coverage |
|------|----------|
| Models & enums | **100%** |
| Core (config, security) | 76% |
| API routes (business logic) | ~75% avg |
| Services — business logic | ~85% avg |
| Services — external connectors | ~15% avg (require live services) |
| Schedulers | ~75% avg |
| DB / migrations | ~30% avg |

---

## Frontend — Vitest + v8

**Total: 36% statements / 37% lines** (451 tests, 30 test files)
Note: untested pages (library, torrents, main-dashboard, media-detail) are mostly UI-only and currently have 0% coverage — this drags the overall average down significantly.

| Area / File | Stmts | Branch | Funcs | Lines |
|-------------|------:|-------:|------:|------:|
| **All files** | 36.09% | 27.14% | 30.66% | 37.27% |
| `src/contexts/AuthContext.jsx` | 97% | 50% | 88% | 97% |
| `src/services/authService.js` | **100%** | **100%** | **100%** | **100%** |
| `src/services/analyticsService.js` | **100%** | 81% | **100%** | **100%** |
| `src/services/calendarService.js` | **100%** | 88% | **100%** | **100%** |
| `src/services/monitoringService.js` | **100%** | **100%** | **100%** | **100%** |
| `src/services/torrentService.js` | **100%** | **100%** | **100%** | **100%** |
| `src/services/configService.js` | 96% | 78% | **100%** | **100%** |
| `src/services/prowlarrService.js` | **100%** | 75% | **100%** | **100%** |
| `src/services/dashboardService.js` | **100%** | 64% | **100%** | **100%** |
| `src/services/syncService.js` | **100%** | 60% | **100%** | **100%** |
| `src/services/libraryService.js` | 86% | 44% | 88% | 86% |
| `src/services/requestService.js` | 88% | 67% | 86% | 87% |
| `src/utils/cn.js` | **100%** | **100%** | **100%** | **100%** |
| `src/utils/quality.js` | **100%** | 95% | **100%** | **100%** |
| `src/pages/login/index.jsx` | **100%** | 93% | **100%** | **100%** |
| `src/pages/jellyseerr-requests/index.jsx` | 93% | 78% | 88% | 93% |
| `src/pages/jellyseerr-requests/components/FilterToolbar.jsx` | **100%** | **100%** | **100%** | **100%** |
| `src/pages/monitoring/index.jsx` | 72% | 69% | 48% | 76% |
| `src/pages/monitoring/components/ExpandableRow.jsx` | **100%** | 84% | **100%** | **100%** |
| `src/pages/monitoring/components/FilterToolbar.jsx` | 92% | **100%** | 83% | 92% |
| `src/pages/monitoring/components/MonitoringTable.jsx` | 79% | 83% | 64% | 79% |
| `src/pages/monitoring/components/StatusIndicator.jsx` | **100%** | **100%** | **100%** | **100%** |
| `src/pages/main-dashboard/components/RequestCard.jsx` | **100%** | 95% | **100%** | **100%** |
| `src/pages/calendar/index.jsx` | 82% | 56% | 79% | 83% |
| `src/pages/initial-configuration/index.jsx` | 90% | 67% | 82% | 91% |
| `src/pages/library/index.jsx` | 0% | 0% | 0% | 0% | No tests yet |
| `src/pages/torrents/index.jsx` | 0% | 0% | 0% | 0% | No tests yet |
| `src/pages/main-dashboard/index.jsx` | 0% | 0% | 0% | 0% | No tests yet |
| `src/pages/media-detail/index.jsx` | 0% | 0% | 0% | 0% | No tests yet |
| `src/lib/pilotarrClient.js` | 0% | 0% | 0% | 0% | No tests yet |

### Frontend coverage by area

| Area | Coverage |
|------|----------|
| Services (API clients) | ~96% avg |
| Auth context | 97% |
| Utils | **100%** |
| Tested pages & components | ~85% avg |
| Untested pages (library, torrents, dashboard, media-detail) | 0% |

---

## Coverage gaps — priorities

| Priority | Item | Impact |
|----------|------|--------|
| High | Backend: external connectors (Jellyfin, Jellyseerr, qBittorrent, Sonarr) — all ~15% | Need mock/integration tests |
| High | Frontend: `src/pages/main-dashboard`, `library`, `torrents`, `media-detail` — all 0% | Core UI pages untested |
| Medium | Backend: `monitoring.py` route (16%), `sync.py` route (34%) | |
| Medium | Frontend: `src/lib/pilotarrClient.js` (0%) | Axios client untested |
| Low | Backend: DB migration scripts (0–16%) | Low-risk, rarely change |
