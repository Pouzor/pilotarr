"""
Connecteur pour qBittorrent
"""

import logging
from typing import Any

import aiohttp

from app.services.base_connector import BaseConnector

logger = logging.getLogger(__name__)


class QBittorrentConnector(BaseConnector):
    """Connecteur pour interagir avec l'API qBittorrent"""

    def __init__(self, base_url: str, username: str, password: str, port: int | None = None):
        """
        Initialise le connecteur qBittorrent

        Args:
            base_url: URL de base de qBittorrent (ex: http://192.168.1.58)
            username: Nom d'utilisateur
            password: Mot de passe
            port: Port (optionnel, ex: 8090)
        """
        # Construire l'URL complète
        if port:
            full_url = f"{base_url}:{port}"
        else:
            full_url = base_url

        super().__init__(base_url=full_url, api_key="")  # api_key vide car non utilisé

        self.username = username
        self.password = password
        self.session: aiohttp.ClientSession | None = None
        self._authenticated = False

    async def _ensure_session(self):
        """Crée une session HTTP si elle n'existe pas"""
        if self.session is None or self.session.closed:
            # Créer une session avec gestion automatique des cookies
            jar = aiohttp.CookieJar(unsafe=True)  # unsafe=True pour accepter les cookies de toutes les IPs
            self.session = aiohttp.ClientSession(cookie_jar=jar)
            self._authenticated = False

    async def _ensure_authenticated(self):
        """S'assure que la session est authentifiée"""
        if not self._authenticated:
            await self.login()

    async def login(self) -> bool:
        """
        qBittorrent Auth

        Returns:
            True or False
        """
        try:
            await self._ensure_session()

            login_url = f"{self.base_url}/api/v2/auth/login"

            data = aiohttp.FormData()
            data.add_field("username", self.username)
            data.add_field("password", self.password)

            logger.info(f"🔐 Try to connect {login_url}")

            async with self.session.post(login_url, data=data) as response:
                text = await response.text()
                logger.info(f"📥 Response login : status={response.status}, body={text}")

                if response.status == 200 and text.strip() == "Ok.":
                    # Vérifier qu'on a bien reçu un cookie SID
                    cookies = self.session.cookie_jar.filter_cookies(self.base_url)
                    logger.info(f"🍪 Cookies reçus : {cookies}")

                    self._authenticated = True
                    logger.info("✅ Auth qBittorent success")
                    return True
                else:
                    logger.error(f"❌ Auth failed : status={response.status}, body={text}")
                    return False

        except Exception as e:
            logger.error(f"❌ Error Auth failed : {e}")
            return False

    async def get_torrent_info(self, torrent_hash: str) -> dict[str, Any] | None:
        """
        Get torrent information by hash

        Args:
            torrent_hash: Hash

        Returns:
            Torrent informations
        """
        try:
            await self._ensure_authenticated()

            # Récupérer les infos du torrent
            url = f"{self.base_url}/api/v2/torrents/info"
            params = {"hashes": torrent_hash}

            logger.info(f"🔍 Récupération infos torrent : {url}?hashes={torrent_hash}")

            async with self.session.get(url, params=params) as response:
                logger.info(f"📥 Response get_torrent_info : status={response.status}")

                if response.status == 200:
                    torrents = await response.json()

                    if torrents and len(torrents) > 0:
                        torrent = torrents[0]

                        # Formater les données
                        return {
                            "hash": torrent.get("hash"),
                            "name": torrent.get("name"),
                            "status": self._map_status(torrent.get("state")),
                            "ratio": round(torrent.get("ratio", 0), 2),
                            "tags": torrent.get("tags", "").split(",") if torrent.get("tags") else [],
                            "seeding_time": torrent.get("seeding_time", 0),  # en secondes
                            "download_date": torrent.get("completion_on"),  # timestamp
                            "size": torrent.get("size", 0),
                            "progress": round(torrent.get("progress", 0) * 100, 1),
                        }
                    else:
                        logger.warning(f"⚠️  Torrent {torrent_hash} not found")
                        return None
                elif response.status == 403:
                    logger.error("❌ 403 Forbidden - Expired session ?")
                    # Réessayer avec une nouvelle authentification
                    self._authenticated = False
                    return None
                else:
                    logger.error(f"❌ Error HTTP {response.status}")
                    return None

        except Exception as e:
            logger.error(f"❌ Error from getting torrent : {e}")
            return None

    async def get_torrents_info(self, hashes: list[str]) -> dict[str, dict[str, Any]]:
        """
        Batch-fetch torrent info for multiple hashes in a single API call.

        Args:
            hashes: List of torrent hashes

        Returns:
            Dict mapping hash -> torrent info dict. Missing torrents are omitted.
        """
        if not hashes:
            return {}

        try:
            await self._ensure_authenticated()

            url = f"{self.base_url}/api/v2/torrents/info"
            params = {"hashes": "|".join(hashes)}

            logger.info(f"🔍 Batch fetch {len(hashes)} torrents")

            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    torrents = await response.json()
                    result = {}
                    for torrent in torrents:
                        h = torrent.get("hash", "").upper()
                        result[h] = {
                            "hash": h,
                            "name": torrent.get("name"),
                            "status": self._map_status(torrent.get("state")),
                            "ratio": round(torrent.get("ratio", 0), 2),
                            "tags": torrent.get("tags", "").split(",") if torrent.get("tags") else [],
                            "seeding_time": torrent.get("seeding_time", 0),
                            "download_date": torrent.get("completion_on"),
                            "size": torrent.get("size", 0),
                            "progress": round(torrent.get("progress", 0) * 100, 1),
                        }
                    logger.info(f"✅ Batch fetch: {len(result)}/{len(hashes)} torrents found")
                    return result
                elif response.status == 403:
                    logger.error("❌ 403 Forbidden - Expired session ?")
                    self._authenticated = False
                    return {}
                else:
                    logger.error(f"❌ HTTP Error {response.status}")
                    return {}

        except Exception as e:
            logger.error(f"❌ Error from fetching torrents : {e}")
            return {}

    def _map_status(self, qbt_state: str) -> str:
        """
        Map qBittorrent states

        Args:
            qbt_state: State qBittorrent (ex: "uploading", "downloading", etc.)

        Returns:
            clean state : "seeding", "downloading", "paused", "queued", "checking", "error", "unknown"
        """
        state_mapping = {
            "uploading": "seeding",
            "stalledUP": "seeding",
            "forcedUP": "seeding",
            "downloading": "downloading",
            "stalledDL": "downloading",
            "forcedDL": "downloading",
            "pausedUP": "paused",
            "pausedDL": "paused",
            "queuedUP": "queued",
            "queuedDL": "queued",
            "checkingUP": "checking",
            "checkingDL": "checking",
            "checkingResumeData": "checking",
            "moving": "checking",
            "error": "error",
            "missingFiles": "error",
        }

        return state_mapping.get(qbt_state, "unknown")

    @staticmethod
    def _parse_tracker_hostname(tracker_url: str) -> str | None:
        """Extracts hostname from a tracker URL, returns None for empty/invalid."""
        if not tracker_url:
            return None
        try:
            from urllib.parse import urlparse

            hostname = urlparse(tracker_url).hostname
            return hostname or None
        except Exception:
            return None

    @staticmethod
    def _unix_to_iso(ts: int | None) -> str | None:
        """Converts a unix timestamp to ISO 8601 string. Returns None for -1 or None."""
        if ts is None or ts == -1:
            return None
        from datetime import datetime, timezone

        return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()

    def _map_torrent(self, torrent: dict) -> dict:
        """Maps a raw qBittorrent torrent dict to the client-agnostic schema."""
        category = torrent.get("category") or None
        tags_raw = torrent.get("tags", "")
        tags = [t.strip() for t in tags_raw.split(",") if t.strip()] if tags_raw else []
        return {
            "id": torrent.get("hash", "").upper(),
            "name": torrent.get("name"),
            "status": self._map_status(torrent.get("state", "")),
            "category": category,
            "size": torrent.get("size", 0),
            "downloaded": torrent.get("downloaded", 0),
            "uploaded": torrent.get("uploaded", 0),
            "progress": torrent.get("progress", 0.0),
            "dlSpeed": torrent.get("dlspeed", 0),
            "ulSpeed": torrent.get("upspeed", 0),
            "seeds": torrent.get("num_seeds", 0),
            "peers": torrent.get("num_leechs", 0),
            "ratio": round(torrent.get("ratio", 0.0), 3),
            "eta": torrent.get("eta", -1),
            "tracker": self._parse_tracker_hostname(torrent.get("tracker", "")),
            "tags": tags,
            "addedOn": self._unix_to_iso(torrent.get("added_on")),
            "completedOn": self._unix_to_iso(torrent.get("completion_on")),
            "savePath": torrent.get("save_path"),
        }

    async def get_all_torrents(self) -> list[dict]:
        """
        Returns all torrents in the client-agnostic schema.

        Returns:
            List of torrent dicts
        """
        try:
            await self._ensure_authenticated()

            url = f"{self.base_url}/api/v2/torrents/info"
            logger.info("🔍 Fetching all torrents")

            async with self.session.get(url) as response:
                if response.status == 200:
                    torrents = await response.json()
                    result = [self._map_torrent(t) for t in torrents]
                    logger.info(f"✅ get_all_torrents: {len(result)} torrents")
                    return result
                elif response.status == 403:
                    logger.error("❌ 403 Forbidden - session expired?")
                    self._authenticated = False
                    return []
                else:
                    logger.error(f"❌ HTTP {response.status}")
                    return []

        except Exception as e:
            logger.error(f"❌ get_all_torrents error: {e}")
            return []

    async def get_transfer_info(self) -> dict:
        """
        Returns global transfer stats from qBittorrent.

        Returns:
            Dict with dl_speed, ul_speed, connection_status
        """
        try:
            await self._ensure_authenticated()

            url = f"{self.base_url}/api/v2/transfer/info"
            logger.info("🔍 Fetching transfer info")

            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "dl_speed": data.get("dl_info_speed", 0),
                        "ul_speed": data.get("up_info_speed", 0),
                        "connection_status": data.get("connection_status", "disconnected"),
                    }
                elif response.status == 403:
                    logger.error("❌ 403 Forbidden - session expired?")
                    self._authenticated = False
                    return {"dl_speed": 0, "ul_speed": 0, "connection_status": "disconnected"}
                else:
                    logger.error(f"❌ HTTP {response.status}")
                    return {"dl_speed": 0, "ul_speed": 0, "connection_status": "disconnected"}

        except Exception as e:
            logger.error(f"❌ get_transfer_info error: {e}")
            return {"dl_speed": 0, "ul_speed": 0, "connection_status": "disconnected"}

    async def test_connection(self) -> tuple[bool, str]:
        """
        Teste la connexion à qBittorrent

        Returns:
            Tuple (succès, message)
        """
        try:
            await self._ensure_session()

            # Tenter l'authentification
            if not await self.login():
                return False, "Échec de l'authentification. Vérifiez username/password."

            # Récupérer la version de qBittorrent
            url = f"{self.base_url}/api/v2/app/version"

            logger.info(f"🔍 Test connexion : {url}")

            async with self.session.get(url) as response:
                logger.info(f"📥 Réponse version : status={response.status}")

                if response.status == 200:
                    version = await response.text()
                    return True, f"Connecté à qBittorrent v{version}"
                else:
                    body = await response.text()
                    return False, f"Erreur HTTP {response.status} : {body}"

        except Exception as e:
            return False, f"Erreur de connexion : {str(e)}"

    async def close(self):
        """Ferme la session HTTP"""
        if self.session and not self.session.closed:
            await self.session.close()
            logger.info("🔒 Session qBittorrent fermée")
