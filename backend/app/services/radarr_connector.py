from datetime import UTC, datetime, timedelta
from typing import Any

from app.services.base_connector import BaseConnector


class RadarrConnector(BaseConnector):
    """Connecteur pour l'API Radarr"""

    def _get_headers(self) -> dict[str, str]:
        """Headers spécifiques à Radarr"""
        return {**super()._get_headers(), "X-Api-Key": self.api_key}

    async def test_connection(self) -> tuple[bool, str]:
        """Tester la connexion à Radarr"""
        try:
            response = await self._get("/api/v3/system/status")
            version = response.get("version", "unknown")
            return True, f"Connecté à Radarr v{version}"
        except Exception as e:
            return False, f"Erreur de connexion: {str(e)}"

    async def get_movies(self) -> list[dict[str, Any]]:
        """
        Récupérer tous les films

        Returns:
            Liste des films avec leurs détails
        """
        try:
            movies = await self._get("/api/v3/movie")
            return movies
        except Exception as e:
            print(f"❌ Erreur récupération films Radarr: {e}")
            return []

    async def get_calendar(self, days_ahead: int = 30, days_behind: int = 30) -> list[dict[str, Any]]:
        """
        Récupérer le calendrier des sorties

        Args:
            days_ahead: Nombre de jours à venir
            days_behind: Nombre de jours passés à inclure

        Returns:
            Liste des films
        """
        try:
            today = datetime.now(UTC).date()
            start_date = today - timedelta(days=days_behind)
            end_date = today + timedelta(days=days_ahead)

            params = {"start": start_date.isoformat(), "end": end_date.isoformat()}

            calendar = await self._get("/api/v3/calendar", params=params)
            return calendar
        except Exception as e:
            print(f"❌ Erreur récupération calendrier Radarr: {e}")
            return []

    async def get_recent_additions(self, days: int = 7) -> list[dict[str, Any]]:
        """
        Récupérer les films récemment ajoutés

        Args:
            days: Nombre de jours en arrière

        Returns:
            Liste des films récemment ajoutés
        """
        try:
            movies = await self.get_movies()

            # Filtrer par date d'ajout
            cutoff_date = datetime.now(UTC) - timedelta(days=days)

            recent = []
            for movie in movies:
                if not movie.get("added"):
                    continue

                try:
                    # Convertir la date en timezone-aware
                    added_dt = datetime.fromisoformat(movie["added"].replace("Z", "+00:00"))
                    if added_dt > cutoff_date:
                        recent.append(movie)
                except (ValueError, AttributeError):
                    # Ignorer les films avec des dates invalides
                    continue

            # Trier par date d'ajout (plus récent en premier)
            recent.sort(key=lambda x: x.get("added", ""), reverse=True)
            return recent

        except Exception as e:
            print(f"❌ Erreur récupération films récents: {e}")
            return []

    async def get_history(self, page_size: int = 50) -> list[dict[str, Any]]:
        """
        Récupérer l'historique des téléchargements

        Args:
            page_size: Nombre d'enregistrements à récupérer

        Returns:
            Liste des événements d'historique avec downloadId
        """
        try:
            params = {
                "pageSize": page_size,
                "sortKey": "date",
                "sortDirection": "descending",
                "eventType": 1,  # 1 = Downloaded
            }

            response = await self._get("/api/v3/history", params=params)
            records = response.get("records", [])

            return records

        except Exception as e:
            print(f"❌ Erreur récupération historique Radarr: {e}")
            return []

    async def get_movie_history_map(self) -> dict[int, str]:
        """
        Créer une map {movieId: torrent_hash}

        Returns:
            Dictionnaire associant les IDs de films aux hash de torrents
        """
        history = await self.get_history(page_size=200)
        movie_hash_map = {}

        for record in history:
            movie_id = record.get("movieId")
            download_id = record.get("downloadId", "")

            if movie_id and download_id:
                # Extraire le hash du downloadId
                # Format possible: "qBittorrent-HASH" ou juste "HASH"
                hash_value = self._extract_hash(download_id)
                if hash_value:
                    movie_hash_map[movie_id] = hash_value

        return movie_hash_map

    def _extract_hash(self, download_id: str) -> str | None:
        """
        Extraire le hash du torrent depuis le downloadId

        Args:
            download_id: ID du téléchargement (ex: "qBittorrent-HASH" ou "HASH")

        Returns:
            Hash du torrent ou None
        """
        if not download_id:
            return None

        # Si format "qBittorrent-HASH"
        if "-" in download_id:
            parts = download_id.split("-", 1)
            if len(parts) == 2:
                return parts[1].upper()

        # Si c'est directement le hash (40 caractères hexadécimaux)
        if len(download_id) == 40 and all(c in "0123456789ABCDEFabcdef" for c in download_id):
            return download_id.upper()

        return None

    async def find_movie_id_by_title(self, title: str) -> int | None:
        """Find Radarr movie ID by title (case-insensitive)."""
        try:
            movies = await self.get_movies()
            for movie in movies:
                if movie.get("title", "").lower() == title.lower():
                    return movie.get("id")
            return None
        except Exception as e:
            print(f"❌ Erreur recherche film '{title}': {e}")
            return None

    async def refresh_movie(self, radarr_movie_id: int) -> bool:
        """Trigger a metadata refresh for a movie via POST /api/v3/command RefreshMovie."""
        try:
            await self._post("/api/v3/command", json={"name": "RefreshMovie", "movieIds": [radarr_movie_id]})
            return True
        except Exception as e:
            print(f"❌ Erreur refresh film {radarr_movie_id}: {e}")
            return False

    async def rescan_movie(self, radarr_movie_id: int) -> bool:
        """Trigger a disk rescan for a movie via POST /api/v3/command RescanMovie."""
        try:
            await self._post("/api/v3/command", json={"name": "RescanMovie", "movieIds": [radarr_movie_id]})
            return True
        except Exception as e:
            print(f"❌ Erreur rescan film {radarr_movie_id}: {e}")
            return False

    async def get_quality_profiles(self) -> dict[int, str]:
        """Retourne un mapping {id: name} des profils de qualité Radarr"""
        try:
            profiles = await self._get("/api/v3/qualityprofile")
            return {p["id"]: p["name"] for p in profiles if "id" in p and "name" in p}
        except Exception as e:
            print(f"❌ Erreur récupération profils qualité Radarr: {e}")
            return {}

    async def get_statistics(self) -> dict[str, Any]:
        """
        Récupérer les statistiques Radarr

        Returns:
            Statistiques (nombre de films monitorés, téléchargés, etc.)
        """
        try:
            movies = await self.get_movies()

            total = len(movies)
            monitored = sum(1 for m in movies if m.get("monitored"))
            downloaded = sum(1 for m in movies if m.get("hasFile"))
            missing = monitored - downloaded

            return {
                "total_movies": total,
                "monitored_movies": monitored,
                "downloaded_movies": downloaded,
                "missing_movies": missing,
            }

        except Exception as e:
            print(f"❌ Erreur récupération stats Radarr: {e}")
            return {}
