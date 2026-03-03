from typing import Any

from app.services.base_connector import BaseConnector


class JellyseerrConnector(BaseConnector):
    """Connecteur pour l'API Jellyseerr"""

    def _get_headers(self) -> dict[str, str]:
        """Headers spécifiques à Jellyseerr"""
        return {**super()._get_headers(), "X-Api-Key": self.api_key}

    async def test_connection(self) -> tuple[bool, str]:
        """Tester la connexion à Jellyseerr"""
        try:
            response = await self._get("/api/v1/status")
            version = response.get("version", "unknown")
            return True, f"Connecté à Jellyseerr v{version}"
        except Exception as e:
            return False, f"Erreur de connexion: {str(e)}"

    async def get_requests(self, limit: int = 100, status: str = "all") -> list[dict[str, Any]]:
        """
        Récupérer les demandes de médias avec pagination

        Args:
            limit: Nombre maximum de requêtes par page
            status: Statut des requêtes (pending, approved, declined, all)

        Returns:
            Liste de toutes les demandes
        """
        try:
            all_results = []
            skip = 0

            while True:
                params = {"take": limit, "skip": skip, "filter": status}
                response = await self._get("/api/v1/request", params=params)

                results = response.get("results", [])
                if not results:
                    break

                all_results.extend(results)

                # Arrêter si on a tout récupéré
                total = response.get("pageInfo", {}).get("results", 0)
                if len(all_results) >= total:
                    break

                skip += limit

            return all_results
        except Exception as e:
            print(f"❌ Erreur récupération requêtes Jellyseerr: {e}")
            return []

    async def get_media_details(self, tmdb_id: int, media_type: str) -> dict[str, Any]:
        """
        Récupérer les détails d'un média via son tmdbId

        Args:
            tmdb_id: ID TMDB du média
            media_type: Type de média ("movie" ou "tv")

        Returns:
            Détails du média (title, posterPath, releaseDate, overview, etc.)
        """
        try:
            endpoint = f"/api/v1/{'movie' if media_type == 'movie' else 'tv'}/{tmdb_id}"
            return await self._get(endpoint)
        except Exception as e:
            print(f"⚠️  Erreur récupération détails média {tmdb_id}: {e}")
            return {}

    async def approve_request(self, request_id: int) -> dict[str, Any]:
        """
        Approuver une demande

        Args:
            request_id: ID de la demande

        Returns:
            Réponse de l'API

        Raises:
            httpx.HTTPError: En cas d'erreur HTTP (propagé au caller)
        """
        response = await self._post(f"/api/v1/request/{request_id}/approve")
        return response

    async def decline_request(self, request_id: int) -> dict[str, Any]:
        """
        Refuser une demande

        Args:
            request_id: ID de la demande

        Returns:
            Réponse de l'API

        Raises:
            httpx.HTTPError: En cas d'erreur HTTP (propagé au caller)
        """
        response = await self._post(f"/api/v1/request/{request_id}/decline")
        return response

    async def get_statistics(self) -> dict[str, Any]:
        """
        Récupérer les statistiques des demandes

        Returns:
            Statistiques
        """
        try:
            all_requests = await self.get_requests(limit=1000, status="all")

            total = len(all_requests)
            pending = sum(1 for r in all_requests if r.get("status") == 1)
            approved = sum(1 for r in all_requests if r.get("status") == 2)
            declined = sum(1 for r in all_requests if r.get("status") in (3, 4))  # 3=declined, 4=failed

            return {"total": total, "pending": pending, "approved": approved, "declined": declined}
        except Exception as e:
            print(f"❌ Erreur récupération stats Jellyseerr: {e}")
            return {}
