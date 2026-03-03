# Pilotarr

A full-stack dashboard for managing your home media server stack. Pilotarr provides a unified interface to monitor and control **Radarr**, **Sonarr**, **qBittorrent**, **Jellyfin**, and **Jellyseerr** from a single place.

![Pilotarr dashboard](docs/pilotarr-1.png)
![Pilotarr library](docs/pilotarr-2.png)
[More screenshots here](docs/)

## Features

- **Unified Dashboard** - Overview of all services with stats, recent additions, and upcoming releases
- **Library Management** - Browse and filter your media library (movies & TV shows)
- **Jellyseerr Requests** - View and manage media requests
- **Torrent Monitoring** - Track active downloads and torrent status
- **Jellyfin Analytics** - Usage charts, device breakdown, user stats, and server performance
- **Calendar** - Upcoming releases from Radarr and Sonarr
- **Alerts** - Notifications and alert history across services
- **Auto-Sync** - Background scheduler syncs data from all services every 15 minutes

## Tech Stack

| Layer      | Technology                                            |
| ---------- | ----------------------------------------------------- |
| Backend    | Python 3, FastAPI, SQLAlchemy, Pydantic               |
| Frontend   | React 18 (JSX), Vite, Tailwind CSS, Redux Toolkit     |
| Database   | MySQL (PyMySQL driver)                                |
| Charts     | Recharts, D3                                          |
| HTTP       | Axios (frontend), HTTPX / aiohttp (backend)           |
| Scheduling | APScheduler                                           |
| Deployment | Docker / Docker Compose                               |

## Prerequisites

- **Docker** & **Docker Compose** (Options 1 & 2)
- Python 3.10+ and Node.js 18+ only needed if building from source (Option 3)

## Installation

### Option 1 — One-line install (recommended)

```bash
curl -fsSL https://raw.githubusercontent.com/Pouzor/pilotarr/main/install.sh | bash
```

This downloads the latest release files into a `pilotarr/` folder, creates a `.env` from the example, then tells you what to edit. Once secrets are set:

```bash
cd pilotarr && docker compose up -d
```

To **update** to a newer release, run the same command again from the parent directory — it detects the existing install and updates `docker-compose.yml` automatically, leaving your `.env` untouched.

---

### Option 2 — Manual (pre-built images, no git clone)

Download the two files into an empty folder:

```bash
curl -fsSL https://raw.githubusercontent.com/Pouzor/pilotarr/main/docker-compose.release.yml -o docker-compose.yml
curl -fsSL https://raw.githubusercontent.com/Pouzor/pilotarr/main/.env.example -o .env.example
cp .env.example .env
```

Edit `.env` and set `DB_PASSWORD`, `MYSQL_ROOT_PASSWORD`, `SECRET_KEY`, `API_KEY`, then:

```bash
docker compose up -d
```

To update: `docker compose pull && docker compose up -d`

---

### Option 3 — From source (dev / self-build)

```bash
git clone https://github.com/Pouzor/pilotarr.git
cd pilotarr
cp .env.example .env
# Edit .env: set DB_PASSWORD, MYSQL_ROOT_PASSWORD, SECRET_KEY, API_KEY
docker compose up -d --build
```

---

The app is available at `http://localhost` (or the port set by `PILOTARR_PORT` in `.env`).

| Service | Internal address | Exposed |
|---|---|---|
| Frontend (nginx) | — | `:80` (configurable via `PILOTARR_PORT`) |
| Backend (FastAPI) | `http://backend:8000` | not exposed externally |
| MySQL | `mysql:3306` | not exposed externally |

#### Useful commands

```bash
docker compose logs -f           # follow all logs
docker compose logs backend      # backend logs only
docker compose down              # stop all
docker compose down -v           # stop + wipe DB volume
```

#### First Login
user : pilotarr

password : rratolip

## Jellyfin Integration

Pilotarr receives real-time playback events from Jellyfin via webhooks. This powers the analytics page (user leaderboard, usage charts, session history) and automatically marks episodes/movies as watched.

Two Jellyfin plugins are required.

### Required plugins

#### 1. Jellyfin Webhook plugin

Sends playback events (play, pause, resume, stop) to Pilotarr in real time.

**Install:**
1. In Jellyfin, go to **Dashboard > Plugins > Catalog**
2. Search for **Webhook** and install it
3. Restart Jellyfin

**Configure:**
1. Go to **Dashboard > Plugins > Webhook**
2. Click **Add** to create a new webhook
3. Set the following:
   - **URL**: `http://<pilotarr-host>:8000/api/analytics/webhook/playback?apiKey=<your_api_key>`
   - **Notification type**: check all playback events — `Play`, `Pause`, `Resume`, `Stop`
   - **Send All Properties**: enabled
4. Save

The `apiKey` must match the `API_KEY` value in your backend `.env`.

> If you configured a `WEBHOOK_SECRET` in `.env`, also add the header `X-Webhook-Secret: <your_secret>` in the webhook plugin settings.

#### 2. Playback Reporting plugin

Stores detailed playback history on the Jellyfin side (used to compute watched duration, enabling the 30%-threshold auto-mark-as-watched logic in Pilotarr).

**Install:**
1. In Jellyfin, go to **Dashboard > Plugins > Catalog**
2. Search for **Playback Reporting** and install it
3. Restart Jellyfin

No additional configuration is needed — the plugin activates automatically and Pilotarr reads the data through the webhook events.

### How it works

| Event | What Pilotarr does |
|---|---|
| `Play` | Opens a playback session, links it to a library item |
| `Pause` / `Resume` | Updates session state |
| `Stop` | Closes the session; if >= 30% watched, marks the episode/movie as watched |

## Project Structure

```
pilotarr/
├── backend/
│   ├── app/
│   │   ├── api/routes/      # API route handlers
│   │   ├── core/            # Configuration & security
│   │   ├── models/          # SQLAlchemy models
│   │   ├── schedulers/      # Background tasks (APScheduler)
│   │   └── services/        # Service connectors (Radarr, Sonarr, etc.)
│   ├── docker-compose.yml
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/      # Shared UI components
│   │   ├── contexts/        # React context providers
│   │   ├── pages/           # Page components (folder per feature)
│   │   ├── services/        # API client services
│   │   └── utils/           # Utility functions
│   └── package.json
└── README.md
```

## License

This project is for personal / self-hosted use.
