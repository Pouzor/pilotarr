"""
Service pour enrichir les library_items avec les données qBittorrent.
Supports multi-torrent: enriches individual LibraryItemTorrent rows,
then aggregates results back onto LibraryItem.torrent_info.
"""

import logging
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.models import LibraryItem, LibraryItemTorrent, ServiceConfiguration
from app.services.connector_factory import create_connector

logger = logging.getLogger(__name__)


class TorrentEnrichmentService:
    """Service pour enrichir les items de bibliothèque avec les données torrents"""

    def __init__(self, db: Session):
        self.db = db
        self.qbt_connector = None

    async def _get_qbt_connector(self):
        """Récupère ou crée le connector qBittorrent"""
        if self.qbt_connector is None:
            qbt_service = (
                self.db.query(ServiceConfiguration)
                .filter(ServiceConfiguration.service_name == "qbittorrent", ServiceConfiguration.is_active.is_(True))
                .first()
            )

            if not qbt_service:
                logger.error("❌ Service qBittorrent non configuré")
                return None

            self.qbt_connector = create_connector(qbt_service)

        return self.qbt_connector

    async def enrich_item(self, item: LibraryItem) -> bool:
        """
        Enrichit un item avec les données qBittorrent (legacy single-torrent path).

        Args:
            item: LibraryItem à enrichir

        Returns:
            True si enrichissement réussi, False sinon
        """
        if not item.torrent_hash:
            logger.warning(f"⚠️  Item {item.id} n'a pas de torrent_hash")
            return False

        try:
            connector = await self._get_qbt_connector()
            if not connector:
                return False

            torrent_info = await connector.get_torrent_info(item.torrent_hash)

            if not torrent_info:
                logger.warning(f"⚠️  Torrent {item.torrent_hash} non trouvé pour item {item.id}")
                return False

            item.torrent_info = torrent_info
            item.updated_at = datetime.now(UTC)

            self.db.commit()

            logger.info(
                f"✅ Item {item.id} enrichi avec succès "
                f"(ratio: {torrent_info.get('ratio')}, status: {torrent_info.get('status')})"
            )
            return True

        except Exception as e:
            logger.error(f"❌ Erreur lors de l'enrichissement de l'item {item.id} : {e}")
            self.db.rollback()
            return False

    async def enrich_all_items(self, limit: int | None = None) -> dict:
        """
        Enrichit tous les items via the multi-torrent pipeline:
        Phase A: enrich individual LibraryItemTorrent rows
        Phase B: aggregate per LibraryItem

        Args:
            limit: Nombre maximum d'items à traiter (None = tous)

        Returns:
            Statistiques de l'enrichissement
        """
        try:
            connector = await self._get_qbt_connector()
            if not connector:
                return {"total": 0, "success": 0, "failed": 0, "error": "qBittorrent non configuré"}

            # === Phase A: Enrich individual torrent rows (always refresh, not just NULL) ===
            torrent_rows_query = self.db.query(LibraryItemTorrent)
            if limit:
                torrent_rows_query = torrent_rows_query.limit(limit)

            torrent_rows = torrent_rows_query.all()
            logger.info(f"📊 Phase A: {len(torrent_rows)} torrent rows à enrichir")

            if torrent_rows:
                # Batch fetch all hashes at once
                hashes = list({row.torrent_hash for row in torrent_rows if row.torrent_hash})
                torrents_data = await connector.get_torrents_info(hashes)

                enriched_count = 0
                for row in torrent_rows:
                    info = torrents_data.get(row.torrent_hash.upper() if row.torrent_hash else "")
                    if info:
                        row.torrent_info = info
                        row.updated_at = datetime.now(UTC)
                        enriched_count += 1

                self.db.commit()
                logger.info(f"✅ Phase A: {enriched_count}/{len(torrent_rows)} torrent rows enrichis")

            # === Phase B: Aggregate per LibraryItem ===
            # Get all library items that have at least one torrent row
            affected_item_ids = (
                self.db.query(LibraryItemTorrent.library_item_id)
                .filter(LibraryItemTorrent.torrent_info.isnot(None))
                .distinct()
                .all()
            )
            affected_item_ids = [row[0] for row in affected_item_ids]

            items = self.db.query(LibraryItem).filter(LibraryItem.id.in_(affected_item_ids)).all()
            logger.info(f"📊 Phase B: {len(items)} library items à agréger")

            stats = {"total": len(items), "success": 0, "failed": 0}

            for item in items:
                try:
                    self._aggregate_torrent_info(item)
                    stats["success"] += 1
                except Exception as e:
                    logger.error(f"❌ Erreur agrégation item {item.id}: {e}")
                    stats["failed"] += 1

            self.db.commit()
            logger.info(f"✅ Phase B: {stats}")

            # Also handle items with torrent_hash but no junction table rows (legacy)
            legacy_items = (
                self.db.query(LibraryItem)
                .filter(
                    LibraryItem.torrent_hash.isnot(None),
                    LibraryItem.torrent_hash != "",
                    ~LibraryItem.id.in_(affected_item_ids) if affected_item_ids else True,
                )
                .all()
            )

            if legacy_items:
                logger.info(f"📊 Legacy enrichment: {len(legacy_items)} items sans junction table rows")
                legacy_hashes = list({item.torrent_hash for item in legacy_items if item.torrent_hash})
                legacy_data = await connector.get_torrents_info(legacy_hashes)

                for item in legacy_items:
                    info = legacy_data.get(item.torrent_hash.upper() if item.torrent_hash else "")
                    if info:
                        info["torrent_count"] = 1
                        item.torrent_info = info
                        item.updated_at = datetime.now(UTC)
                        stats["success"] += 1
                        stats["total"] += 1
                    else:
                        stats["failed"] += 1
                        stats["total"] += 1

                self.db.commit()

            logger.info(f"✅ Enrichissement terminé : {stats}")
            return stats

        except Exception as e:
            logger.error(f"❌ Erreur lors de l'enrichissement global : {e}")
            return {"total": 0, "success": 0, "failed": 0, "error": str(e)}
        finally:
            if self.qbt_connector:
                await self.qbt_connector.close()

    def _aggregate_torrent_info(self, item: LibraryItem):
        """
        Compute aggregated torrent_info from all LibraryItemTorrent rows for this item.
        Writes the result to item.torrent_info.
        """
        torrent_rows = (
            self.db.query(LibraryItemTorrent)
            .filter(
                LibraryItemTorrent.library_item_id == item.id,
                LibraryItemTorrent.torrent_info.isnot(None),
            )
            .all()
        )

        if not torrent_rows:
            return

        ratios = []
        sizes = []
        seeding_times = []
        download_dates = []
        progresses = []
        statuses = []
        names = []

        for row in torrent_rows:
            info = row.torrent_info
            if not info:
                continue

            if info.get("ratio") is not None:
                ratios.append(info["ratio"])
            if info.get("size") is not None:
                sizes.append(info["size"])
            if info.get("seeding_time") is not None:
                seeding_times.append(info["seeding_time"])
            if info.get("download_date") is not None:
                download_dates.append(info["download_date"])
            if info.get("progress") is not None:
                progresses.append(info["progress"])
            if info.get("status"):
                statuses.append(info["status"])
            if info.get("name"):
                names.append(info["name"])

        # Compute aggregated status
        if all(s == "seeding" for s in statuses):
            agg_status = "seeding"
        elif any(s == "downloading" for s in statuses):
            agg_status = "downloading"
        elif statuses:
            agg_status = "mixed"
        else:
            agg_status = "unknown"

        # Compute aggregated progress
        if progresses and all(p >= 100 for p in progresses):
            agg_progress = 100.0
        elif progresses:
            agg_progress = round(sum(progresses) / len(progresses), 1)
        else:
            agg_progress = 0.0

        aggregated = {
            "ratio": round(sum(ratios) / len(ratios), 2) if ratios else 0,
            "status": agg_status,
            "size": sum(sizes) if sizes else 0,
            "seeding_time": max(seeding_times) if seeding_times else 0,
            "download_date": min(download_dates) if download_dates else None,
            "progress": agg_progress,
            "torrent_count": len(torrent_rows),
            "name": names[0] if len(names) == 1 else f"{len(torrent_rows)} torrents",
        }

        item.torrent_info = aggregated
        item.updated_at = datetime.now(UTC)

    async def enrich_recent_items(self, days: int = 7) -> dict:
        """
        Enrichit les items récents (ajoutés dans les X derniers jours)

        Args:
            days: Nombre de jours en arrière

        Returns:
            Statistiques de l'enrichissement
        """
        try:
            from datetime import timedelta

            cutoff_date = datetime.now(UTC) - timedelta(days=days)

            connector = await self._get_qbt_connector()
            if not connector:
                return {"total": 0, "success": 0, "failed": 0, "error": "qBittorrent non configuré"}

            # Phase A: enrich recent torrent rows (always refresh, not just NULL)
            torrent_rows = (
                self.db.query(LibraryItemTorrent)
                .filter(
                    LibraryItemTorrent.created_at >= cutoff_date,
                )
                .all()
            )

            logger.info(f"📊 {len(torrent_rows)} torrent rows récents à enrichir")

            if torrent_rows:
                hashes = list({row.torrent_hash for row in torrent_rows if row.torrent_hash})
                torrents_data = await connector.get_torrents_info(hashes)

                for row in torrent_rows:
                    info = torrents_data.get(row.torrent_hash.upper() if row.torrent_hash else "")
                    if info:
                        row.torrent_info = info
                        row.updated_at = datetime.now(UTC)

                self.db.commit()

            # Phase B: aggregate affected items
            affected_item_ids = list({row.library_item_id for row in torrent_rows})
            items = (
                self.db.query(LibraryItem).filter(LibraryItem.id.in_(affected_item_ids)).all()
                if affected_item_ids
                else []
            )

            stats = {"total": len(items), "success": 0, "failed": 0}

            for item in items:
                try:
                    self._aggregate_torrent_info(item)
                    stats["success"] += 1
                except Exception as e:
                    logger.error(f"❌ Erreur agrégation item {item.id}: {e}")
                    stats["failed"] += 1

            self.db.commit()

            # Legacy path for items without junction table rows
            legacy_items = (
                self.db.query(LibraryItem)
                .filter(
                    LibraryItem.torrent_hash.isnot(None),
                    LibraryItem.torrent_hash != "",
                    LibraryItem.created_at >= cutoff_date,
                    ~LibraryItem.id.in_(affected_item_ids) if affected_item_ids else True,
                )
                .all()
            )

            if legacy_items:
                legacy_hashes = list({item.torrent_hash for item in legacy_items if item.torrent_hash})
                legacy_data = await connector.get_torrents_info(legacy_hashes)

                for item in legacy_items:
                    info = legacy_data.get(item.torrent_hash.upper() if item.torrent_hash else "")
                    if info:
                        info["torrent_count"] = 1
                        item.torrent_info = info
                        item.updated_at = datetime.now(UTC)
                        stats["success"] += 1
                        stats["total"] += 1
                    else:
                        stats["failed"] += 1
                        stats["total"] += 1

                self.db.commit()

            logger.info(f"✅ Enrichissement des items récents terminé : {stats}")
            return stats

        except Exception as e:
            logger.error(f"❌ Erreur lors de l'enrichissement des items récents : {e}")
            return {"total": 0, "success": 0, "failed": 0, "error": str(e)}
        finally:
            if self.qbt_connector:
                await self.qbt_connector.close()
