from typing import Any

import httpx


class BaseConnector:
    """Classe de base pour tous les connecteurs API"""

    def __init__(self, base_url: str, api_key: str, port: int | None = None, timeout: int = 30):
        # Si un port est fourni et pas déjà dans l'URL, l'ajouter
        if port and f":{port}" not in base_url:
            # Supprimer le / final si présent
            base_url = base_url.rstrip("/")
            # Vérifier si l'URL a déjà un port
            if not any(f":{p}" in base_url for p in range(1, 65536)):
                base_url = f"{base_url}:{port}"

        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)

    async def close(self):
        """Fermer la connexion HTTP"""
        await self.client.aclose()

    async def _get(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        Effectuer une requête GET

        Args:
            endpoint: Chemin de l'endpoint (ex: '/api/v3/movie')
            params: Paramètres query string optionnels

        Returns:
            Réponse JSON

        Raises:
            httpx.HTTPError: En cas d'erreur HTTP
        """
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()

        try:
            response = await self.client.get(url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            print(f"❌ Erreur HTTP {endpoint}: {e}")
            raise

    async def _post(
        self, endpoint: str, data: dict[str, Any] | None = None, json: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Effectuer une requête POST

        Args:
            endpoint: Chemin de l'endpoint
            data: Données à envoyer (alias pour json)
            json: Données JSON à envoyer

        Returns:
            Réponse JSON
        """
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()

        # Utiliser json si fourni, sinon data
        payload = json if json is not None else data

        try:
            response = await self.client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json() if response.content else {}
        except httpx.HTTPError as e:
            print(f"❌ Erreur HTTP POST {endpoint}: {e}")
            raise

    async def _put(self, endpoint: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
        """Effectuer une requête PUT"""
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()

        try:
            response = await self.client.put(url, headers=headers, json=data)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            print(f"❌ Erreur HTTP PUT {endpoint}: {e}")
            raise

    async def _delete(self, endpoint: str) -> dict[str, Any]:
        """Effectuer une requête DELETE"""
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()

        try:
            response = await self.client.delete(url, headers=headers)
            response.raise_for_status()
            return response.json() if response.content else {}
        except httpx.HTTPError as e:
            print(f"❌ Erreur HTTP DELETE {endpoint}: {e}")
            raise

    def _get_headers(self) -> dict[str, str]:
        """
        Headers par défaut (à surcharger dans les classes filles)
        """
        return {"Content-Type": "application/json", "Accept": "application/json"}

    async def test_connection(self) -> tuple[bool, str]:
        """
        Tester la connexion à l'API

        Returns:
            (success: bool, message: str)
        """
        raise NotImplementedError("Méthode à implémenter dans la classe fille")
