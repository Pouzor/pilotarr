import time
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.models import (
    CalendarEvent,
    CalendarStatus,
    DashboardStatistic,
    Episode,
    JellyseerrRequest,
    LibraryItem,
    LibraryItemTorrent,
    MediaType,
    RequestPriority,
    RequestStatus,
    Season,
    ServiceConfiguration,
    ServiceType,
    StatType,
    SyncMetadata,
    SyncStatus,
)
from app.services import JellyfinConnector, JellyseerrConnector, RadarrConnector, SonarrConnector


class SyncService:
    """Service de synchronisation des données depuis les APIs externes"""

    def __init__(self, db: Session):
        self.db = db

    def get_active_service(self, service_type: ServiceType) -> ServiceConfiguration:
        """Récupérer la configuration d'un service actif"""
        return (
            self.db.query(ServiceConfiguration)
            .filter(ServiceConfiguration.service_name == service_type, ServiceConfiguration.is_active.is_(True))
            .first()
        )

    def _upsert_torrent(
        self,
        library_item_id: str,
        torrent_hash: str,
        episode_id: int | None = None,
        season_number: int | None = None,
        is_season_pack: bool = False,
    ):
        """Insert a torrent row if it doesn't already exist for this item+hash"""
        existing = (
            self.db.query(LibraryItemTorrent)
            .filter(
                LibraryItemTorrent.library_item_id == library_item_id,
                LibraryItemTorrent.torrent_hash == torrent_hash,
            )
            .first()
        )
        if not existing:
            self.db.add(
                LibraryItemTorrent(
                    library_item_id=library_item_id,
                    torrent_hash=torrent_hash,
                    episode_id=episode_id,
                    season_number=season_number,
                    is_season_pack=is_season_pack,
                )
            )

    def update_sync_metadata(
        self, service_type: ServiceType, status: SyncStatus, records: int = 0, duration_ms: int = 0, error: str = None
    ):
        """Mettre à jour les métadonnées de sync"""
        sync_meta = self.db.query(SyncMetadata).filter(SyncMetadata.service_name == service_type).first()

        if not sync_meta:
            sync_meta = SyncMetadata(service_name=service_type)
            self.db.add(sync_meta)

        sync_meta.last_sync_time = datetime.now(UTC)
        sync_meta.sync_status = status
        sync_meta.records_synced = records
        sync_meta.sync_duration_ms = duration_ms
        sync_meta.error_message = error
        sync_meta.next_sync_time = datetime.now(UTC) + timedelta(minutes=15)

        self.db.commit()

    async def sync_monitored_items(self) -> dict[str, Any]:
        """
        Synchroniser les statistiques des items monitorés (Radarr + Sonarr)
        """
        print("📊 Synchronisation des items monitorés...")

        try:
            # Initialiser les totaux
            total_monitored = 0
            total_unmonitored = 0
            downloading = 0
            downloaded = 0
            missing = 0
            queued = 0
            unreleased = 0

            # === RADARR ===
            radarr_service = self.get_active_service(ServiceType.RADARR)
            if radarr_service:
                radarr_connector = RadarrConnector(
                    base_url=radarr_service.url, api_key=radarr_service.api_key, port=radarr_service.port
                )

                try:
                    radarr_stats = await radarr_connector.get_statistics()

                    # Ajouter les stats Radarr
                    total_monitored += radarr_stats.get("monitored_movies", 0)
                    total_unmonitored += radarr_stats.get("total_movies", 0) - radarr_stats.get("monitored_movies", 0)
                    downloaded += radarr_stats.get("downloaded_movies", 0)
                    missing += radarr_stats.get("missing_movies", 0)

                    print(f"  📽️  Radarr: {radarr_stats.get('monitored_movies', 0)} monitorés")
                except Exception as e:
                    print(f"  ⚠️  Erreur stats Radarr: {e}")
                finally:
                    await radarr_connector.close()

            # === SONARR ===
            sonarr_service = self.get_active_service(ServiceType.SONARR)
            if sonarr_service:
                sonarr_connector = SonarrConnector(
                    base_url=sonarr_service.url, api_key=sonarr_service.api_key, port=sonarr_service.port
                )

                try:
                    sonarr_stats = await sonarr_connector.get_statistics()

                    # Ajouter les stats Sonarr
                    total_monitored += sonarr_stats.get("monitored_series", 0)
                    total_unmonitored += sonarr_stats.get("total_series", 0) - sonarr_stats.get("monitored_series", 0)
                    downloaded += sonarr_stats.get("downloaded_episodes", 0)
                    missing += sonarr_stats.get("missing_episodes", 0)

                    print(f"  📺 Sonarr: {sonarr_stats.get('monitored_series', 0)} monitorés")
                except Exception as e:
                    print(f"  ⚠️  Erreur stats Sonarr: {e}")
                finally:
                    await sonarr_connector.close()

            # Mettre à jour ou créer la statistique MONITORED_ITEMS
            monitored_stat = (
                self.db.query(DashboardStatistic)
                .filter(DashboardStatistic.stat_type == StatType.MONITORED_ITEMS)
                .first()
            )

            if not monitored_stat:
                monitored_stat = DashboardStatistic(stat_type=StatType.MONITORED_ITEMS)
                self.db.add(monitored_stat)

            # Total = items monitorés
            monitored_stat.total_count = total_monitored
            monitored_stat.details = {
                "monitored": total_monitored,
                "unmonitored": total_unmonitored,
                "downloading": downloading,
                "downloaded": downloaded,
                "missing": missing,
                "queued": queued,
                "unreleased": unreleased,
            }
            monitored_stat.last_synced = datetime.now(UTC)

            self.db.commit()

            print(f"✅ Monitored Items: {total_monitored} monitorés, {missing} manquants")
            return {
                "success": True,
                "monitored": total_monitored,
                "unmonitored": total_unmonitored,
                "details": monitored_stat.details,
            }

        except Exception as e:
            print(f"❌ Erreur sync monitored items: {e}")
            return {"success": False, "error": str(e)}

    async def sync_radarr(self) -> dict[str, Any]:
        """Synchroniser les données Radarr"""
        print("🎬 Synchronisation Radarr...")
        start_time = time.time()

        service = self.get_active_service(ServiceType.RADARR)
        if not service:
            print("⚠️ Service Radarr non configuré")
            return {"success": False, "message": "Service non configuré"}

        connector = RadarrConnector(base_url=service.url, api_key=service.api_key, port=service.port)

        try:
            # Récupérer les films récents
            recent_movies = await connector.get_recent_additions(days=30)

            # Récupérer la map movieId -> torrent_hash
            movie_hash_map = await connector.get_movie_history_map()
            print(f"📥 {len(movie_hash_map)} hash de torrents récupérés depuis Radarr")

            # Ajouter à la DB (éviter les doublons)
            added_count = 0
            updated_count = 0

            for movie in recent_movies[:20]:  # Limiter à 20 pour ne pas surcharger
                # Vérifier si existe déjà (par titre + année)
                existing = (
                    self.db.query(LibraryItem)
                    .filter(
                        LibraryItem.title == movie.get("title"),
                        LibraryItem.year == movie.get("year"),
                        LibraryItem.media_type == MediaType.MOVIE,
                    )
                    .first()
                )

                # Récupérer le torrent_hash depuis la map
                movie_id = movie.get("id")
                torrent_hash = movie_hash_map.get(movie_id) if movie_id else None

                nb_media = 1 if movie.get("hasFile") else 0

                if existing:
                    # Mettre à jour le hash si on en a un et qu'il n'existe pas encore
                    if torrent_hash and not existing.torrent_hash:
                        existing.torrent_hash = torrent_hash
                        existing.updated_at = datetime.now(UTC)
                        updated_count += 1
                        print(f"  🔄 Mise à jour hash pour: {movie.get('title')} - {torrent_hash[:8]}...")
                    # Write to junction table
                    if torrent_hash:
                        self._upsert_torrent(existing.id, torrent_hash)
                    # Toujours mettre à jour nb_media
                    existing.nb_media = nb_media
                    # Mettre à jour la taille si elle était à 0
                    size_bytes = movie.get("sizeOnDisk", 0)
                    if size_bytes > 0:
                        size_gb = round(size_bytes / (1024**3), 1)
                        existing.size = f"{size_gb} GB"
                else:
                    # Calculer la taille
                    size_bytes = movie.get("sizeOnDisk", 0)
                    size_gb = round(size_bytes / (1024**3), 1)

                    # Date d'ajout
                    added_date = movie.get("added", "")
                    added_dt = None
                    if added_date:
                        try:
                            added_dt = datetime.fromisoformat(added_date.replace("Z", "+00:00"))
                        except (ValueError, TypeError):
                            pass

                    # Récupérer l'image
                    image_url = ""
                    for img in movie.get("images", []):
                        if img.get("coverType") == "poster":
                            image_url = img.get("remoteUrl", "")
                            break

                    if not image_url and movie.get("images"):
                        image_url = movie.get("images", [{}])[0].get("remoteUrl", "")

                    item = LibraryItem(
                        title=movie.get("title", "Unknown"),
                        year=movie.get("year", 0),
                        media_type=MediaType.MOVIE,
                        image_url=image_url,
                        image_alt=f"{movie.get('title')} poster",
                        quality=str(movie.get("qualityProfileId", "Unknown")),
                        rating=str(movie.get("ratings", {}).get("imdb", {}).get("value", "")),
                        description=movie.get("overview", ""),
                        added_date=added_dt,
                        size=f"{size_gb} GB",
                        torrent_hash=torrent_hash,
                        nb_media=nb_media,
                    )

                    self.db.add(item)
                    self.db.flush()  # Ensure item.id is available
                    added_count += 1

                    if torrent_hash:
                        self._upsert_torrent(item.id, torrent_hash)
                        print(f"  ✅ {movie.get('title')} - hash: {torrent_hash[:8]}...")

            # Récupérer le calendrier
            calendar = await connector.get_calendar(days_ahead=30)

            # Ajouter/mettre à jour le calendrier
            calendar_count = 0
            for event in calendar[:20]:
                release_date_str = event.get("physicalRelease") or event.get("digitalRelease")
                if not release_date_str:
                    continue

                try:
                    release_date = datetime.fromisoformat(release_date_str.replace("Z", "+00:00")).date()
                except (ValueError, TypeError):
                    continue

                title = event.get("title", "Unknown")

                # Récupérer l'image
                image_url = ""
                for img in event.get("images", []):
                    if img.get("coverType") == "poster":
                        image_url = img.get("remoteUrl", "")
                        break
                if not image_url and event.get("images"):
                    image_url = event.get("images", [{}])[0].get("remoteUrl", "")

                existing = (
                    self.db.query(CalendarEvent)
                    .filter(CalendarEvent.title == title, CalendarEvent.release_date == release_date)
                    .first()
                )

                if existing:
                    # Mettre à jour les champs potentiellement vides
                    if image_url and not existing.image_url:
                        existing.image_url = image_url
                        existing.image_alt = f"{title} poster"
                else:
                    cal_event = CalendarEvent(
                        title=title,
                        media_type=MediaType.MOVIE,
                        release_date=release_date,
                        image_url=image_url,
                        image_alt=f"{title} poster",
                        status=CalendarStatus.MONITORED,
                    )
                    self.db.add(cal_event)

                calendar_count += 1

            self.db.commit()

            duration_ms = int((time.time() - start_time) * 1000)
            self.update_sync_metadata(ServiceType.RADARR, SyncStatus.SUCCESS, added_count + calendar_count, duration_ms)

            print(f"✅ Radarr: {added_count} films ajoutés, {updated_count} mis à jour, {calendar_count} événements")
            return {"success": True, "movies_added": added_count, "calendar_events": calendar_count}

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            self.update_sync_metadata(ServiceType.RADARR, SyncStatus.FAILED, 0, duration_ms, str(e))
            print(f"❌ Erreur sync Radarr: {e}")
            return {"success": False, "error": str(e)}
        finally:
            await connector.close()

    async def sync_sonarr_seasons(self) -> dict[str, Any]:
        """
        Sync seasons for TV shows from embedded series data
        Runs as part of sync_sonarr()
        """
        print("📺 Synchronisation des saisons Sonarr...")

        service = self.get_active_service(ServiceType.SONARR)
        if not service:
            return {"success": False, "message": "Service non configuré"}

        connector = SonarrConnector(base_url=service.url, api_key=service.api_key, port=service.port)

        try:
            # Get all TV show items
            series_items = self.db.query(LibraryItem).filter(LibraryItem.media_type == MediaType.TV).all()

            # Get all series from Sonarr (with embedded seasons)
            series_list = await connector.get_series()

            seasons_synced = 0
            seasons_updated = 0

            for item in series_items:
                # Find Sonarr series by title + year
                series_data = next(
                    (s for s in series_list if s.get("title") == item.title and s.get("year") == item.year), None
                )

                if not series_data or "seasons" not in series_data:
                    continue

                # Upsert seasons from embedded data
                for season_data in series_data["seasons"]:
                    season_num = season_data.get("seasonNumber")
                    if season_num is None:
                        continue

                    stats = season_data.get("statistics", {})

                    existing = (
                        self.db.query(Season)
                        .filter(Season.library_item_id == item.id, Season.season_number == season_num)
                        .first()
                    )

                    if existing:
                        # Update existing season
                        existing.monitored = season_data.get("monitored", True)
                        existing.episode_count = stats.get("episodeCount", 0)
                        existing.episode_file_count = stats.get("episodeFileCount", 0)
                        existing.total_episode_count = stats.get("totalEpisodeCount", 0)
                        existing.size_on_disk = stats.get("sizeOnDisk", 0)
                        existing.statistics = stats
                        seasons_updated += 1
                    else:
                        # Create new season
                        new_season = Season(
                            library_item_id=item.id,
                            sonarr_series_id=series_data["id"],
                            season_number=season_num,
                            monitored=season_data.get("monitored", True),
                            episode_count=stats.get("episodeCount", 0),
                            episode_file_count=stats.get("episodeFileCount", 0),
                            total_episode_count=stats.get("totalEpisodeCount", 0),
                            size_on_disk=stats.get("sizeOnDisk", 0),
                            statistics=stats,
                        )
                        self.db.add(new_season)
                        seasons_synced += 1

            self.db.commit()

            print(f"✅ Saisons: {seasons_synced} créées, {seasons_updated} mises à jour")
            return {"success": True, "seasons_synced": seasons_synced, "seasons_updated": seasons_updated}

        except Exception as e:
            print(f"❌ Erreur sync saisons: {e}")
            return {"success": False, "error": str(e)}
        finally:
            await connector.close()

    async def sync_sonarr(self) -> dict[str, Any]:
        """Synchroniser les données Sonarr"""
        print("📺 Synchronisation Sonarr...")
        start_time = time.time()

        service = self.get_active_service(ServiceType.SONARR)
        if not service:
            print("⚠️ Service Sonarr non configuré")
            return {"success": False, "message": "Service non configuré"}

        connector = SonarrConnector(base_url=service.url, api_key=service.api_key, port=service.port)

        try:
            # Récupérer les séries récentes
            recent_series = await connector.get_recent_additions(days=30)

            # Récupérer la map seriesId -> [{hash, episode_id, season_number, is_season_pack}, ...]
            series_torrents_map = await connector.get_series_torrents_map()
            total_hashes = sum(len(v) for v in series_torrents_map.values())
            print(f"📥 {total_hashes} hash de torrents récupérés depuis Sonarr ({len(series_torrents_map)} séries)")

            added_count = 0
            updated_count = 0

            for series in recent_series[:20]:
                existing = (
                    self.db.query(LibraryItem)
                    .filter(
                        LibraryItem.title == series.get("title"),
                        LibraryItem.year == series.get("year"),
                        LibraryItem.media_type == MediaType.TV,
                    )
                    .first()
                )

                # Récupérer les torrents depuis la map
                series_id = series.get("id")
                torrent_entries = series_torrents_map.get(series_id, []) if series_id else []
                first_hash = torrent_entries[0]["hash"] if torrent_entries else None

                nb_media = series.get("statistics", {}).get("episodeFileCount", 0)

                if existing:
                    # Mettre à jour le hash si on en a un et qu'il n'existe pas encore
                    if first_hash and not existing.torrent_hash:
                        existing.torrent_hash = first_hash
                        existing.updated_at = datetime.now(UTC)
                        updated_count += 1
                        print(f"  🔄 Mise à jour hash pour: {series.get('title')} - {first_hash[:8]}...")
                    # Upsert all torrents into junction table
                    for entry in torrent_entries:
                        self._upsert_torrent(
                            existing.id,
                            entry["hash"],
                            episode_id=entry.get("episode_id"),
                            season_number=entry.get("season_number"),
                            is_season_pack=entry.get("is_season_pack", False),
                        )
                    # Toujours mettre à jour nb_media
                    existing.nb_media = nb_media
                    # Mettre à jour la taille si elle était à 0
                    size_bytes = series.get("statistics", {}).get("sizeOnDisk", 0)
                    if size_bytes > 0:
                        size_gb = round(size_bytes / (1024**3), 1)
                        existing.size = f"{size_gb} GB"
                else:
                    size_bytes = series.get("statistics", {}).get("sizeOnDisk", 0)
                    size_gb = round(size_bytes / (1024**3), 1)

                    added_date = series.get("added", "")
                    added_dt = None
                    if added_date:
                        try:
                            added_dt = datetime.fromisoformat(added_date.replace("Z", "+00:00"))
                        except (ValueError, TypeError):
                            pass

                    # Récupérer l'image
                    image_url = ""
                    for img in series.get("images", []):
                        if img.get("coverType") == "poster":
                            image_url = img.get("remoteUrl", "")
                            break

                    if not image_url and series.get("images"):
                        image_url = series.get("images", [{}])[0].get("remoteUrl", "")

                    item = LibraryItem(
                        title=series.get("title", "Unknown"),
                        year=series.get("year", 0),
                        media_type=MediaType.TV,
                        image_url=image_url,
                        image_alt=f"{series.get('title')} poster",
                        quality=str(series.get("qualityProfileId", "Unknown")),
                        rating=str(series.get("ratings", {}).get("value", "")),
                        description=series.get("overview", ""),
                        added_date=added_dt,
                        size=f"{size_gb} GB",
                        torrent_hash=first_hash,
                        nb_media=nb_media,
                    )

                    self.db.add(item)
                    self.db.flush()  # Ensure item.id is available
                    added_count += 1

                    # Write all torrents to junction table
                    for entry in torrent_entries:
                        self._upsert_torrent(
                            item.id,
                            entry["hash"],
                            episode_id=entry.get("episode_id"),
                            season_number=entry.get("season_number"),
                            is_season_pack=entry.get("is_season_pack", False),
                        )

                    if first_hash:
                        print(
                            f"  ✅ {series.get('title')} - {len(torrent_entries)} torrent(s), "
                            f"first: {first_hash[:8]}..."
                        )

            # Récupérer le calendrier (includeSeries=true dans le connector)
            calendar = await connector.get_calendar(days_ahead=30)
            calendar_count = 0

            for event in calendar[:20]:
                if not event.get("airDate"):
                    continue

                try:
                    air_date = datetime.fromisoformat(event.get("airDate") + "T00:00:00+00:00").date()
                except (ValueError, TypeError):
                    continue

                # Titre et image depuis l'objet series (inclus via includeSeries=true)
                series_data = event.get("series", {})
                series_title = series_data.get("title") or event.get("title", "Unknown")
                season = event.get("seasonNumber", 0)
                episode_num = event.get("episodeNumber", 0)
                episode_str = f"Season {season}, Episode {episode_num}"

                # Récupérer l'image depuis les images de la série
                image_url = ""
                for img in series_data.get("images", []):
                    if img.get("coverType") == "poster":
                        image_url = img.get("remoteUrl", "")
                        break
                if not image_url and series_data.get("images"):
                    image_url = series_data.get("images", [{}])[0].get("remoteUrl", "")

                # Chercher un enregistrement existant (par titre + date + épisode)
                existing = (
                    self.db.query(CalendarEvent)
                    .filter(
                        CalendarEvent.release_date == air_date,
                        CalendarEvent.episode == episode_str,
                        CalendarEvent.media_type == MediaType.TV,
                    )
                    .first()
                )

                # Aussi chercher par ancien titre "Unknown" pour corriger
                if not existing:
                    existing = (
                        self.db.query(CalendarEvent)
                        .filter(
                            CalendarEvent.title == "Unknown",
                            CalendarEvent.release_date == air_date,
                            CalendarEvent.episode == episode_str,
                            CalendarEvent.media_type == MediaType.TV,
                        )
                        .first()
                    )

                if existing:
                    # Mettre à jour les champs vides ou incorrects
                    if existing.title == "Unknown" and series_title != "Unknown":
                        existing.title = series_title
                    if image_url and not existing.image_url:
                        existing.image_url = image_url
                    existing.image_alt = f"{series_title} poster"
                else:
                    cal_event = CalendarEvent(
                        title=series_title,
                        media_type=MediaType.TV,
                        release_date=air_date,
                        episode=episode_str,
                        image_url=image_url,
                        image_alt=f"{series_title} poster",
                        status=CalendarStatus.MONITORED,
                    )
                    self.db.add(cal_event)

                calendar_count += 1

            self.db.commit()

            # Sync seasons after syncing series
            seasons_result = await self.sync_sonarr_seasons()

            duration_ms = int((time.time() - start_time) * 1000)
            self.update_sync_metadata(ServiceType.SONARR, SyncStatus.SUCCESS, added_count + calendar_count, duration_ms)

            print(
                f"✅ Sonarr: {added_count} séries, {calendar_count} événements, "
                f"{seasons_result.get('seasons_synced', 0)} saisons"
            )
            return {
                "success": True,
                "series_added": added_count,
                "calendar_events": calendar_count,
                "seasons_synced": seasons_result.get("seasons_synced", 0),
            }

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            self.update_sync_metadata(ServiceType.SONARR, SyncStatus.FAILED, 0, duration_ms, str(e))
            print(f"❌ Erreur sync Sonarr: {e}")
            return {"success": False, "error": str(e)}
        finally:
            await connector.close()

    async def sync_sonarr_episodes(self, full_sync: bool = False, series_limit: int = 5) -> dict[str, Any]:
        """
        Sync episodes for TV shows - separate job from series sync

        Args:
            full_sync: If True, sync all series. If False, only monitored.
            series_limit: Max series per run (rate limiting)
        """
        print("📺 Synchronisation des épisodes Sonarr...")
        start_time = time.time()

        service = self.get_active_service(ServiceType.SONARR)
        if not service:
            print("⚠️ Service Sonarr non configuré")
            return {"success": False, "message": "Service non configuré"}

        connector = SonarrConnector(base_url=service.url, api_key=service.api_key, port=service.port)

        try:
            # Get series to sync (limited batch)
            if full_sync:
                # Sync all TV series
                series_items = (
                    self.db.query(LibraryItem).filter(LibraryItem.media_type == MediaType.TV).limit(series_limit).all()
                )
            else:
                # Only sync series with monitored seasons (use distinct to avoid duplicates)
                series_items = (
                    self.db.query(LibraryItem)
                    .join(Season, Season.library_item_id == LibraryItem.id)
                    .filter(LibraryItem.media_type == MediaType.TV, Season.monitored)
                    .distinct()
                    .limit(series_limit)
                    .all()
                )

            print(f"  📊 Found {len(series_items)} series to sync (full_sync={full_sync}, limit={series_limit})")

            if not series_items:
                print("  ⚠️  No series found to sync")
                return {"success": True, "series_processed": 0, "episodes_synced": 0, "episodes_updated": 0}

            series_list = await connector.get_series()
            print(f"  📡 Fetched {len(series_list)} series from Sonarr")

            episodes_synced = 0
            episodes_updated = 0

            for idx, item in enumerate(series_items, 1):
                print(f"  📺 [{idx}/{len(series_items)}] Processing: {item.title} ({item.year})")

                # Find Sonarr series
                series_data = next(
                    (s for s in series_list if s.get("title") == item.title and s.get("year") == item.year), None
                )

                if not series_data:
                    print("    ⚠️  Not found in Sonarr")
                    continue

                series_id = series_data["id"]
                print(f"    🔍 Sonarr series ID: {series_id}")

                # Fetch episodes + files
                episodes = await connector.get_episodes_by_series(series_id)
                episode_files = await connector.get_episode_files_by_series(series_id)
                file_map = {f["id"]: f for f in episode_files}

                print(f"    📥 Fetched {len(episodes)} episodes, {len(episode_files)} files")

                # Upsert episodes
                series_episodes_synced = 0
                series_episodes_updated = 0

                for ep_data in episodes:
                    season_num = ep_data.get("seasonNumber")
                    episode_num = ep_data.get("episodeNumber")

                    if season_num is None or episode_num is None:
                        continue

                    # Find or create season
                    season = (
                        self.db.query(Season)
                        .filter(Season.library_item_id == item.id, Season.season_number == season_num)
                        .first()
                    )

                    if not season:
                        # Create season if it doesn't exist
                        season = Season(
                            library_item_id=item.id,
                            sonarr_series_id=series_id,
                            season_number=season_num,
                        )
                        self.db.add(season)
                        self.db.flush()

                    # Extract file info
                    has_file = ep_data.get("hasFile", False)
                    episode_file_id = ep_data.get("episodeFileId")
                    file_info = file_map.get(episode_file_id) if episode_file_id else None

                    # Parse air date
                    air_date = None
                    if ep_data.get("airDate"):
                        try:
                            air_date = datetime.fromisoformat(ep_data["airDate"]).date()
                        except (ValueError, TypeError):
                            pass

                    # Upsert episode
                    existing = self.db.query(Episode).filter(Episode.sonarr_episode_id == ep_data["id"]).first()

                    if existing:
                        # Update existing
                        existing.title = ep_data.get("title")
                        existing.overview = ep_data.get("overview")
                        existing.air_date = air_date
                        existing.monitored = ep_data.get("monitored", True)
                        existing.has_file = has_file
                        existing.downloaded = has_file
                        existing.sonarr_episode_file_id = episode_file_id

                        if file_info:
                            existing.file_size = file_info.get("size")
                            existing.quality_profile = file_info.get("quality", {}).get("quality", {}).get("name")
                            existing.relative_path = file_info.get("relativePath")
                            existing.episode_file_info = file_info

                        episodes_updated += 1
                        series_episodes_updated += 1
                    else:
                        # Insert new
                        new_episode = Episode(
                            season_id=season.id,
                            library_item_id=item.id,
                            sonarr_episode_id=ep_data["id"],
                            sonarr_series_id=series_id,
                            season_number=season_num,
                            episode_number=episode_num,
                            absolute_episode_number=ep_data.get("absoluteEpisodeNumber"),
                            title=ep_data.get("title"),
                            overview=ep_data.get("overview"),
                            air_date=air_date,
                            monitored=ep_data.get("monitored", True),
                            has_file=has_file,
                            downloaded=has_file,
                            sonarr_episode_file_id=episode_file_id,
                        )

                        if file_info:
                            new_episode.file_size = file_info.get("size")
                            new_episode.quality_profile = file_info.get("quality", {}).get("quality", {}).get("name")
                            new_episode.relative_path = file_info.get("relativePath")
                            new_episode.episode_file_info = file_info

                        self.db.add(new_episode)
                        episodes_synced += 1
                        series_episodes_synced += 1

                print(f"    ✅ {series_episodes_synced} created, {series_episodes_updated} updated")

            self.db.commit()

            duration_ms = int((time.time() - start_time) * 1000)

            print(
                f"✅ Épisodes: {episodes_synced} créés, {episodes_updated} mis à jour "
                f"({len(series_items)} séries, {duration_ms}ms)"
            )
            return {
                "success": True,
                "series_processed": len(series_items),
                "episodes_synced": episodes_synced,
                "episodes_updated": episodes_updated,
                "duration_ms": duration_ms,
            }

        except Exception as e:
            print(f"❌ Erreur sync épisodes: {e}")
            return {"success": False, "error": str(e)}
        finally:
            await connector.close()

    async def sync_jellyfin(self) -> dict[str, Any]:
        """Synchroniser les données Jellyfin"""
        print("🎥 Synchronisation Jellyfin...")
        start_time = time.time()

        service = self.get_active_service(ServiceType.JELLYFIN)
        if not service:
            print("⚠️  Service Jellyfin non configuré")
            return {"success": False, "message": "Service non configuré"}

        connector = JellyfinConnector(base_url=service.url, api_key=service.api_key, port=service.port)

        try:
            # Récupérer les stats
            users = await connector.get_users()
            library_stats = await connector.get_library_items()

            # Récupérer le temps de visionnage total des 30 derniers jours
            watch_time_data = await connector.get_total_watch_time(days=30)
            total_watch_hours = watch_time_data.get("total_hours", 0)

            # Récupérer les détails Movies (avec durée totale)
            movies_details = await connector.get_movies_details()

            # Récupérer les détails TV Shows (avec durée totale)
            tv_details = await connector.get_tv_shows_details()

            # Mettre à jour les statistiques
            # Users
            user_stat = self.db.query(DashboardStatistic).filter(DashboardStatistic.stat_type == StatType.USERS).first()

            if not user_stat:
                user_stat = DashboardStatistic(stat_type=StatType.USERS)
                self.db.add(user_stat)

            user_stat.total_count = len(users)
            user_stat.details = {
                "active_users": len([u for u in users if not u.get("Policy", {}).get("IsDisabled", False)]),
                "total_watch_hours": total_watch_hours,
            }
            user_stat.last_synced = datetime.now(UTC)

            # Movies
            movie_stat = (
                self.db.query(DashboardStatistic).filter(DashboardStatistic.stat_type == StatType.MOVIES).first()
            )

            if not movie_stat:
                movie_stat = DashboardStatistic(stat_type=StatType.MOVIES)
                self.db.add(movie_stat)

            movie_stat.total_count = movies_details.get("total_movies", 0)
            movie_stat.details = {"total_hours": movies_details.get("total_hours", 0)}
            movie_stat.last_synced = datetime.now(UTC)

            # TV Shows
            tv_stat = (
                self.db.query(DashboardStatistic).filter(DashboardStatistic.stat_type == StatType.TV_SHOWS).first()
            )

            if not tv_stat:
                tv_stat = DashboardStatistic(stat_type=StatType.TV_SHOWS)
                self.db.add(tv_stat)

            tv_stat.total_count = tv_details.get("total_series", 0)
            tv_stat.details = {
                "total_series": tv_details.get("total_series", 0),
                "total_episodes": tv_details.get("total_episodes", 0),
                "total_hours": tv_details.get("total_hours", 0),
            }
            tv_stat.last_synced = datetime.now(UTC)

            self.db.commit()

            duration_ms = int((time.time() - start_time) * 1000)
            self.update_sync_metadata(ServiceType.JELLYFIN, SyncStatus.SUCCESS, len(users), duration_ms)

            movies_count = movies_details.get("total_movies", 0)
            movies_hours = movies_details.get("total_hours", 0)
            tv_count = tv_details.get("total_series", 0)
            tv_hours = tv_details.get("total_hours", 0)
            print(
                f"✅ Jellyfin: {len(users)} users, {movies_count} films ({movies_hours}h), "
                f"{tv_count} séries ({tv_hours}h), {total_watch_hours}h visionnées"
            )
            return {
                "success": True,
                "users": len(users),
                "library_stats": library_stats,
                "movies_details": movies_details,
                "tv_details": tv_details,
                "watch_hours": total_watch_hours,
            }

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            self.update_sync_metadata(ServiceType.JELLYFIN, SyncStatus.FAILED, 0, duration_ms, str(e))
            print(f"❌ Erreur sync Jellyfin: {e}")
            return {"success": False, "error": str(e)}
        finally:
            await connector.close()

    async def sync_jellyseerr(self) -> dict[str, Any]:
        """Synchroniser les données Jellyseerr (upsert par jellyseerr_id)"""
        print("📝 Synchronisation Jellyseerr...")
        start_time = time.time()

        service = self.get_active_service(ServiceType.JELLYSEERR)
        if not service:
            print("⚠️  Service Jellyseerr non configuré")
            return {"success": False, "message": "Service non configuré"}

        connector = JellyseerrConnector(base_url=service.url, api_key=service.api_key, port=service.port)

        try:
            # Tester d'abord la connexion
            success, message = await connector.test_connection()
            if not success:
                raise Exception(f"Test de connexion échoué: {message}")

            # Récupérer toutes les requêtes (tous statuts)
            requests = await connector.get_requests(limit=100, status="all")

            # Mapper les statuts Jellyseerr vers notre enum
            status_map = {
                1: RequestStatus.PENDING,
                2: RequestStatus.APPROVED,
                3: RequestStatus.DECLINED,
            }

            # Construire un set des IDs Jellyseerr reçus depuis l'API
            api_jellyseerr_ids = set()
            # Cache des détails média pour éviter les appels dupliqués
            media_details_cache: dict[tuple[int, str], dict[str, Any]] = {}

            added_count = 0
            updated_count = 0

            for req in requests:
                try:
                    jellyseerr_id = req.get("id")
                    if not jellyseerr_id:
                        continue

                    api_jellyseerr_ids.add(jellyseerr_id)

                    media = req.get("media", {})
                    requested_by = req.get("requestedBy", {})
                    media_type_str = req.get("type", "movie")
                    tmdb_id = media.get("tmdbId")

                    # Récupérer les détails du média via TMDB ID (avec cache)
                    media_details = {}
                    if tmdb_id:
                        cache_key = (tmdb_id, media_type_str)
                        if cache_key not in media_details_cache:
                            media_details_cache[cache_key] = await connector.get_media_details(tmdb_id, media_type_str)
                        media_details = media_details_cache[cache_key]

                    # Titre : depuis les détails TMDB
                    title = media_details.get("title") or media_details.get("name") or "Unknown"

                    # Année : depuis releaseDate (movie) ou firstAirDate (tv)
                    year = 0
                    release_date = media_details.get("releaseDate") or media_details.get("firstAirDate") or ""
                    if release_date:
                        try:
                            year = int(release_date[:4])
                        except (ValueError, TypeError):
                            year = 0

                    # Image : posterPath depuis les détails TMDB
                    poster_path = media_details.get("posterPath", "")
                    image_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else ""

                    # Description
                    description = media_details.get("overview", "")

                    # Extraction sécurisée de la date de création
                    requested_date = "Unknown"
                    if req.get("createdAt"):
                        try:
                            created_dt = datetime.fromisoformat(req.get("createdAt").replace("Z", "+00:00"))
                            requested_date = self._format_time_ago(created_dt)
                        except (ValueError, TypeError, AttributeError):
                            pass

                    req_status = status_map.get(req.get("status"), RequestStatus.PENDING)

                    # Upsert : chercher par jellyseerr_id
                    existing = (
                        self.db.query(JellyseerrRequest)
                        .filter(JellyseerrRequest.jellyseerr_id == jellyseerr_id)
                        .first()
                    )

                    if existing:
                        # Mettre à jour les champs qui peuvent changer
                        existing.title = title
                        existing.year = year
                        existing.image_url = image_url
                        existing.image_alt = f"{title} poster"
                        existing.description = description
                        existing.status = req_status
                        existing.requested_by = requested_by.get("displayName", existing.requested_by)
                        existing.requested_by_avatar = requested_by.get("avatar")
                        existing.requested_by_user_id = requested_by.get("id")
                        existing.quality = "4K" if req.get("is4k") else "1080p"
                        existing.requested_date = requested_date
                        updated_count += 1
                    else:
                        request_item = JellyseerrRequest(
                            jellyseerr_id=jellyseerr_id,
                            title=title,
                            media_type=MediaType.MOVIE if media_type_str == "movie" else MediaType.TV,
                            year=year,
                            image_url=image_url,
                            image_alt=f"{title} poster",
                            status=req_status,
                            priority=RequestPriority.MEDIUM,
                            requested_by=requested_by.get("displayName", "Unknown"),
                            requested_by_avatar=requested_by.get("avatar"),
                            requested_by_user_id=requested_by.get("id"),
                            requested_date=requested_date,
                            quality="4K" if req.get("is4k") else "1080p",
                            description=description,
                        )
                        self.db.add(request_item)
                        added_count += 1
                except Exception as item_error:
                    print(f"⚠️  Erreur traitement requête Jellyseerr: {item_error}")
                    continue

            # Supprimer les requêtes qui n'existent plus dans l'API
            stale_deleted = 0
            if api_jellyseerr_ids:
                stale_deleted = (
                    self.db.query(JellyseerrRequest)
                    .filter(JellyseerrRequest.jellyseerr_id.notin_(api_jellyseerr_ids))
                    .delete(synchronize_session="fetch")
                )
            else:
                # Si l'API ne retourne rien, supprimer tout
                stale_deleted = self.db.query(JellyseerrRequest).delete()

            self.db.commit()

            duration_ms = int((time.time() - start_time) * 1000)
            total_synced = added_count + updated_count
            self.update_sync_metadata(ServiceType.JELLYSEERR, SyncStatus.SUCCESS, total_synced, duration_ms)

            print(f"✅ Jellyseerr: {added_count} ajoutées, {updated_count} mises à jour, {stale_deleted} supprimées")
            return {
                "success": True,
                "requests_added": added_count,
                "requests_updated": updated_count,
                "requests_deleted": stale_deleted,
            }

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            self.update_sync_metadata(ServiceType.JELLYSEERR, SyncStatus.FAILED, 0, duration_ms, str(e))
            print(f"❌ Erreur sync Jellyseerr: {e}")
            return {"success": False, "error": str(e)}
        finally:
            await connector.close()

    async def sync_all(self) -> dict[str, Any]:
        """Synchroniser tous les services"""
        print("\n" + "=" * 50)
        print("🔄 DÉBUT DE LA SYNCHRONISATION GLOBALE")
        print("=" * 50 + "\n")

        results = {}

        results["radarr"] = await self.sync_radarr()
        results["sonarr"] = await self.sync_sonarr()
        results["jellyfin"] = await self.sync_jellyfin()
        results["jellyseerr"] = await self.sync_jellyseerr()
        results["monitored_items"] = await self.sync_monitored_items()

        print("\n" + "=" * 50)
        print("✅ SYNCHRONISATION TERMINÉE")
        print("=" * 50 + "\n")

        return results

    def _format_time_ago(self, dt: datetime) -> str:
        """Formater une date en 'X hours ago', 'X days ago'"""
        # S'assurer que dt est timezone-aware
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)

        now = datetime.now(UTC)
        delta = now - dt

        if delta.days > 0:
            return f"{delta.days} day{'s' if delta.days > 1 else ''} ago"
        elif delta.seconds >= 3600:
            hours = delta.seconds // 3600
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        elif delta.seconds >= 60:
            minutes = delta.seconds // 60
            return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
        else:
            return "just now"
