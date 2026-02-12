# Pilotarr

A full-stack dashboard for managing your home media server stack. Pilotarr provides a unified interface to monitor and control **Radarr**, **Sonarr**, **qBittorrent**, **Jellyfin**, and **Jellyseerr** from a single place.

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

- **Python 3.10+**
- **Node.js 18+**
- **MySQL** (or MariaDB) instance
- (Optional) **Docker** & **Docker Compose**

## Installation

### 1. Clone the repository

```bash
git clone <repo-url>
cd pilotarr
```

### 2. Backend setup

```bash
cd backend

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt
```

Create a `.env` file in `backend/` with the following variables:

```env
# Database
DB_HOST=localhost
DB_PORT=3306
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_NAME=pilotarr

# Security
SECRET_KEY=your_secret_key
API_KEY=your_api_key

# Jellyfin
JELLYFIN_PUBLIC_URL=http://your-jellyfin-url
```

Start the backend:

```bash
uvicorn app.main:app --reload
```

The API is available at `http://localhost:8000` with interactive docs at `http://localhost:8000/docs`.

### 3. Frontend setup

```bash
cd frontend

# Install dependencies
npm install

# Start the dev server
npm start
```

The frontend is available at `http://localhost:5173`.

### 4. Docker (alternative)

Run the backend with Docker Compose:

```bash
cd backend
docker-compose up
```

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
