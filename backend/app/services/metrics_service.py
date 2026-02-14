import logging
from datetime import datetime

import psutil
from sqlalchemy.orm import Session

from app.models.models import PlaybackSession, ServerMetric

logger = logging.getLogger(__name__)


class MetricsService:
    """Service pour gérer les métriques serveur"""

    @staticmethod
    def get_cpu_usage() -> float:
        """Récupère l'utilisation CPU en pourcentage"""
        return psutil.cpu_percent(interval=1)

    @staticmethod
    def get_memory_usage() -> tuple[float, float]:
        """
        Récupère l'utilisation mémoire
        Returns: (usage_gb, total_gb)
        """
        mem = psutil.virtual_memory()
        usage_gb = mem.used / (1024**3)
        total_gb = mem.total / (1024**3)
        return usage_gb, total_gb

    @staticmethod
    def get_disk_usage() -> tuple[float, float]:
        """
        Récupère l'utilisation disque
        Returns: (used_tb, total_tb)
        """
        disk = psutil.disk_usage("/")
        used_tb = disk.used / (1024**4)
        total_tb = disk.total / (1024**4)
        return used_tb, total_tb

    @staticmethod
    def get_network_bandwidth() -> float:
        """
        Récupère la bande passante réseau en Mbps
        Mesure sur 1 seconde
        """
        try:
            net_before = psutil.net_io_counters()
            import time

            time.sleep(1)
            net_after = psutil.net_io_counters()

            # Calculer les bytes envoyés + reçus par seconde
            bytes_sent = net_after.bytes_sent - net_before.bytes_sent
            bytes_recv = net_after.bytes_recv - net_before.bytes_recv
            total_bytes = bytes_sent + bytes_recv

            # Convertir en Mbps
            mbps = (total_bytes * 8) / (1024 * 1024)
            return round(mbps, 2)
        except Exception as e:
            logger.warning(f"⚠️  Impossible de récupérer la bande passante : {e}")
            return 0.0

    @staticmethod
    def determine_status(value: float, warning_threshold: float, error_threshold: float) -> str:
        """
        Détermine le statut basé sur les seuils

        Args:
            value: Valeur actuelle (pourcentage)
            warning_threshold: Seuil d'alerte (ex: 70)
            error_threshold: Seuil d'erreur (ex: 90)

        Returns:
            "success", "warning" ou "error"
        """
        if value >= error_threshold:
            return "error"
        elif value >= warning_threshold:
            return "warning"
        else:
            return "success"

    @staticmethod
    def capture_metrics(db: Session) -> ServerMetric:
        """
        Capture toutes les métriques système et les enregistre en DB
        """
        try:
            # Récupérer les métriques
            cpu_percent = MetricsService.get_cpu_usage()
            memory_usage_gb, memory_total_gb = MetricsService.get_memory_usage()
            storage_used_tb, storage_total_tb = MetricsService.get_disk_usage()
            bandwidth_mbps = MetricsService.get_network_bandwidth()

            # Calculer les pourcentages
            memory_percent = (memory_usage_gb / memory_total_gb) * 100 if memory_total_gb > 0 else 0
            storage_percent = (storage_used_tb / storage_total_tb) * 100 if storage_total_tb > 0 else 0

            # Déterminer les statuts
            cpu_status = MetricsService.determine_status(cpu_percent, 70, 90)
            memory_status = MetricsService.determine_status(memory_percent, 70, 90)
            storage_status = MetricsService.determine_status(storage_percent, 80, 95)

            # Note: Pour bandwidth, on considère que > 100 Mbps = warning, > 500 = error
            # À adapter selon ton infrastructure
            bandwidth_status = "error" if bandwidth_mbps > 500 else ("warning" if bandwidth_mbps > 100 else "success")

            # Compter les sessions actives
            active_sessions_count = db.query(PlaybackSession).filter(PlaybackSession.is_active).count()

            # Compter les transcodages actifs
            active_transcoding_count = (
                db.query(PlaybackSession)
                .filter(PlaybackSession.is_active, PlaybackSession.transcoding_progress > 0)
                .count()
            )

            # Créer l'enregistrement
            metric = ServerMetric(
                cpu_usage_percent=cpu_percent,
                memory_usage_gb=memory_usage_gb,
                memory_total_gb=memory_total_gb,
                storage_used_tb=storage_used_tb,
                storage_total_tb=storage_total_tb,
                bandwidth_mbps=bandwidth_mbps,
                cpu_status=cpu_status,
                memory_status=memory_status,
                bandwidth_status=bandwidth_status,
                storage_status=storage_status,
                active_sessions_count=active_sessions_count,
                active_transcoding_count=active_transcoding_count,
            )

            db.add(metric)
            db.commit()
            db.refresh(metric)

            logger.info(
                f"📊 Métriques capturées : CPU={cpu_percent}%, "
                f"RAM={memory_usage_gb:.1f}GB, Sessions={active_sessions_count}"
            )

            return metric

        except Exception as e:
            db.rollback()
            logger.error(f"❌ Erreur lors de la capture des métriques : {e}")
            raise

    @staticmethod
    def cleanup_old_metrics(db: Session, keep_days: int = 7):
        """
        Nettoie les anciennes métriques (garder seulement les X derniers jours)

        Args:
            db: Session DB
            keep_days: Nombre de jours à conserver
        """
        try:
            from datetime import timedelta

            cutoff_date = datetime.utcnow() - timedelta(days=keep_days)

            deleted = db.query(ServerMetric).filter(ServerMetric.recorded_at < cutoff_date).delete()

            db.commit()

            if deleted > 0:
                logger.info(f"🧹 {deleted} anciennes métriques supprimées")

        except Exception as e:
            db.rollback()
            logger.error(f"❌ Erreur lors du nettoyage des métriques : {e}")
