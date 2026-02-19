"""
Service de synchronisation des MediaStreams (sous-titres, audio) depuis Jellyfin.

- TV Shows : info au niveau épisode (Episode.media_streams)
- Movies   : info au niveau item (LibraryItem.media_streams)
"""

from typing import Any

from sqlalchemy.orm import Session

from app.models import Episode, LibraryItem, MediaType, Season, ServiceConfiguration, ServiceType
from app.services.jellyfin_connector import JellyfinConnector


def _parse_streams(media_streams: list[dict[str, Any]]) -> dict[str, Any]:
    """Convert Jellyfin MediaStreams array into a compact dict with subtitles and audio lists."""
    subtitles = []
    audio = []

    for stream in media_streams:
        stream_type = stream.get("Type", "")
        if stream_type == "Subtitle":
            subtitles.append(
                {
                    "language": stream.get("Language") or "Unknown",
                    "codec": stream.get("Codec") or "",
                    "title": stream.get("DisplayTitle") or "",
                    "forced": bool(stream.get("IsForced", False)),
                    "default": bool(stream.get("IsDefault", False)),
                }
            )
        elif stream_type == "Audio":
            audio.append(
                {
                    "language": stream.get("Language") or "Unknown",
                    "codec": stream.get("Codec") or "",
                    "channels": stream.get("Channels") or 0,
                    "title": stream.get("DisplayTitle") or "",
                }
            )

    return {"subtitles": subtitles, "audio": audio}


class JellyfinStreamsService:
    """Synchronise les informations de sous-titres/audio depuis l'API Jellyfin."""

    def __init__(self, db: Session):
        self.db = db

    def _get_connector(self) -> JellyfinConnector | None:
        config = (
            self.db.query(ServiceConfiguration)
            .filter(
                ServiceConfiguration.service_name == ServiceType.JELLYFIN,
                ServiceConfiguration.is_active.is_(True),
            )
            .first()
        )
        if not config:
            print("⚠️  Jellyfin non configuré, skip sync des streams")
            return None
        return JellyfinConnector(base_url=config.url, api_key=config.api_key, port=config.port)

    async def sync_movie_streams(self) -> dict[str, int]:
        """Sync media_streams for all movies in LibraryItem."""
        connector = self._get_connector()
        if not connector:
            return {"total": 0, "updated": 0, "skipped": 0}

        print("🎬 Récupération des films Jellyfin avec streams...")
        jellyfin_movies = await connector.get_movies_with_streams()
        print(f"   → {len(jellyfin_movies)} films trouvés sur Jellyfin")

        # Build a lookup: (normalized_title, year) → parsed streams
        jf_index: dict[tuple[str, int | None], dict] = {}
        for jf in jellyfin_movies:
            name = (jf.get("Name") or "").strip().lower()
            year = jf.get("ProductionYear")
            streams = _parse_streams(jf.get("MediaStreams") or [])
            jf_index[(name, year)] = streams

        # Load all movie LibraryItems
        movies = self.db.query(LibraryItem).filter(LibraryItem.media_type == MediaType.MOVIE).all()

        updated = 0
        skipped = 0
        for item in movies:
            title_norm = item.title.strip().lower()
            streams = jf_index.get((title_norm, item.year))
            if streams is None:
                # Try without year as fallback
                streams = next(
                    (v for (t, _y), v in jf_index.items() if t == title_norm),
                    None,
                )

            if streams is not None:
                item.media_streams = streams
                updated += 1
            else:
                skipped += 1

        self.db.commit()
        print(f"✅ Films : {updated} mis à jour, {skipped} non trouvés sur Jellyfin")
        return {"total": len(movies), "updated": updated, "skipped": skipped}

    async def sync_tv_streams(self) -> dict[str, int]:
        """Sync media_streams for all TV episodes in Episode."""
        connector = self._get_connector()
        if not connector:
            return {"total": 0, "updated": 0, "skipped": 0}

        # Load all TV LibraryItems
        tv_items = self.db.query(LibraryItem).filter(LibraryItem.media_type == MediaType.TV).all()
        print(f"📺 Sync streams pour {len(tv_items)} séries TV...")

        total_episodes = 0
        total_updated = 0
        total_skipped = 0

        for item in tv_items:
            # Find Jellyfin series ID by title
            jf_series_id = await connector.get_series_id_by_title(item.title)
            if not jf_series_id:
                print(f"   ⚠️  Série non trouvée sur Jellyfin : {item.title}")
                continue

            # Fetch all episodes with streams for this series
            jf_episodes = await connector.get_episodes_with_streams(jf_series_id)

            # Build lookup: (season_number, episode_number) → streams
            jf_ep_index: dict[tuple[int, int], dict] = {}
            for jf_ep in jf_episodes:
                s = jf_ep.get("ParentIndexNumber")
                e = jf_ep.get("IndexNumber")
                if s is not None and e is not None:
                    jf_ep_index[(int(s), int(e))] = _parse_streams(jf_ep.get("MediaStreams") or [])

            # Load DB episodes for this series
            seasons = self.db.query(Season).filter(Season.library_item_id == item.id).all()
            season_ids = [s.id for s in seasons]

            if not season_ids:
                continue

            episodes = (
                self.db.query(Episode).filter(Episode.season_id.in_(season_ids), Episode.has_file.is_(True)).all()
            )

            for ep in episodes:
                key = (ep.season_number, ep.episode_number)
                streams = jf_ep_index.get(key)
                if streams is not None:
                    ep.media_streams = streams
                    total_updated += 1
                else:
                    total_skipped += 1
                total_episodes += 1

            print(f"   ✅ {item.title}: {len(episodes)} épisodes traités ({len(jf_ep_index)} trouvés sur Jellyfin)")

        self.db.commit()
        print(f"✅ Séries TV : {total_updated}/{total_episodes} épisodes mis à jour")
        return {"total": total_episodes, "updated": total_updated, "skipped": total_skipped}

    async def sync_all(self) -> dict[str, Any]:
        """Sync streams for both movies and TV episodes."""
        print("\n🎞️  Synchronisation des MediaStreams Jellyfin...")
        movie_stats = await self.sync_movie_streams()
        tv_stats = await self.sync_tv_streams()
        return {"movies": movie_stats, "tv": tv_stats}
