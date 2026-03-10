"""
Script de migration pour ajouter les tables analytics
"""

from sqlalchemy import inspect

from app.db import Base, check_db_connection, engine


def get_existing_tables():
    """Récupère la liste des tables existantes dans la DB"""
    inspector = inspect(engine)
    return inspector.get_table_names()


def create_analytics_tables():
    """Crée uniquement les nouvelles tables analytics"""
    print("🔍 Vérification de la connexion à la base de données...")
    if not check_db_connection():
        print("❌ Impossible de se connecter à la base de données!")
        return False

    print("✅ Connexion établie")

    existing_tables = get_existing_tables()
    print(f"\n📊 Tables existantes : {len(existing_tables)}")
    for table in existing_tables:
        print(f"  - {table}")

    new_tables = [
        "playback_sessions",
        "device_statistics",
        "daily_analytics",
        "server_metrics",
        "library_item_torrents",
    ]

    tables_to_create = [t for t in new_tables if t not in existing_tables]

    if not tables_to_create:
        print("\n✅ Toutes les tables existent déjà!")
    else:
        print(f"\n🆕 Nouvelles tables à créer : {len(tables_to_create)}")
        for table in tables_to_create:
            print(f"  - {table}")

        try:
            print("\n🚀 Création des nouvelles tables...")
            Base.metadata.create_all(bind=engine, checkfirst=True)
            print("✅ Tables créées avec succès!")

            new_existing_tables = get_existing_tables()
            created = set(new_existing_tables) - set(existing_tables)
            if created:
                print("\n✨ Tables créées :")
                for table in created:
                    print(f"  - {table}")

        except Exception as e:
            print(f"❌ Erreur lors de la création des tables : {e}")
            return False

    # Migrate existing torrent_hash data into library_item_torrents
    if "library_item_torrents" in get_existing_tables():
        try:
            migrate_torrent_hashes()
        except Exception as e:
            print(f"❌ Erreur lors de la migration des torrents : {e}")
            return False

    # Migrate added_date column from TEXT to DATETIME
    if "library_items" in get_existing_tables():
        try:
            migrate_added_date_column()
        except Exception as e:
            print(f"❌ Erreur lors de la migration de added_date : {e}")
            return False

    # Add jellyfin_id column to library_items
    if "library_items" in get_existing_tables():
        try:
            migrate_add_jellyfin_id_to_library_items()
        except Exception as e:
            print(f"❌ Erreur lors de l'ajout de jellyfin_id sur library_items : {e}")
            return False

    # Add media_path column to library_items
    if "library_items" in get_existing_tables():
        try:
            migrate_add_media_path_to_library_items()
        except Exception as e:
            print(f"❌ Erreur lors de l'ajout de media_path sur library_items : {e}")
            return False

    # Add media_streams column to library_items (movies)
    if "library_items" in get_existing_tables():
        try:
            migrate_add_media_streams_to_library_items()
        except Exception as e:
            print(f"❌ Erreur lors de l'ajout de media_streams sur library_items : {e}")
            return False

    # Add media_streams column to episodes (TV shows)
    if "episodes" in get_existing_tables():
        try:
            migrate_add_media_streams_to_episodes()
        except Exception as e:
            print(f"❌ Erreur lors de l'ajout de media_streams sur episodes : {e}")
            return False

    # Add watched column to library_items (movies)
    if "library_items" in get_existing_tables():
        try:
            migrate_add_watched_to_library_items()
        except Exception as e:
            print(f"❌ Erreur lors de l'ajout de watched sur library_items : {e}")
            return False

    # Add watched column to episodes (TV shows)
    if "episodes" in get_existing_tables():
        try:
            migrate_add_watched_to_episodes()
        except Exception as e:
            print(f"❌ Erreur lors de l'ajout de watched sur episodes : {e}")
            return False

    # Add 'prowlarr' to sync_metadata.service_name ENUM
    if "sync_metadata" in get_existing_tables():
        try:
            migrate_add_prowlarr_to_sync_metadata_enum()
        except Exception as e:
            print(f"❌ Erreur lors de l'ajout de prowlarr dans sync_metadata enum : {e}")
            return False

    # Add 'prowlarr' to service_configurations.service_name ENUM
    if "service_configurations" in get_existing_tables():
        try:
            migrate_add_prowlarr_to_service_configurations_enum()
        except Exception as e:
            print(f"❌ Erreur lors de l'ajout de prowlarr dans service_configurations enum : {e}")
            return False

    # Add 'radarr' to service_configurations.service_name ENUM (may be missing on some installs)
    if "service_configurations" in get_existing_tables():
        try:
            migrate_add_radarr_to_service_configurations_enum()
        except Exception as e:
            print(f"❌ Erreur lors de l'ajout de radarr dans service_configurations enum : {e}")
            return False

    # Add 'radarr' to sync_metadata.service_name ENUM (may be missing on some installs)
    if "sync_metadata" in get_existing_tables():
        try:
            migrate_add_radarr_to_sync_metadata_enum()
        except Exception as e:
            print(f"❌ Erreur lors de l'ajout de radarr dans sync_metadata enum : {e}")
            return False

    # Convert sync_metadata.service_name from ENUM to VARCHAR to avoid SQLAlchemy _object_lookup issues
    if "sync_metadata" in get_existing_tables():
        try:
            migrate_sync_metadata_service_name_to_varchar()
        except Exception as e:
            print(f"❌ Erreur lors de la conversion de sync_metadata.service_name en VARCHAR : {e}")
            return False

    # Add 'AVAILABLE' to jellyseerr_requests.status ENUM
    if "jellyseerr_requests" in get_existing_tables():
        try:
            migrate_add_available_to_jellyseerr_requests_status()
        except Exception as e:
            print(f"❌ Erreur lors de l'ajout de AVAILABLE dans jellyseerr_requests.status : {e}")
            return False

    # Add genres column to library_items
    if "library_items" in get_existing_tables():
        try:
            migrate_add_genres_to_library_items()
        except Exception as e:
            print(f"❌ Erreur lors de l'ajout de genres sur library_items : {e}")
            return False

    return True


def migrate_torrent_hashes():
    """Migrate existing LibraryItem.torrent_hash rows into library_item_torrents"""
    from sqlalchemy import text

    from app.db import SessionLocal

    db = SessionLocal()
    try:
        # Find library_items with a torrent_hash that don't already have a matching row
        rows = db.execute(
            text(
                """
                SELECT li.id, li.torrent_hash
                FROM library_items li
                WHERE li.torrent_hash IS NOT NULL
                  AND li.torrent_hash != ''
                  AND NOT EXISTS (
                    SELECT 1 FROM library_item_torrents lit
                    WHERE lit.library_item_id = li.id AND lit.torrent_hash = li.torrent_hash
                  )
                """
            )
        ).fetchall()

        if not rows:
            print("✅ Aucune donnée torrent à migrer")
            return

        print(f"🔄 Migration de {len(rows)} torrents existants...")
        import uuid

        for row in rows:
            db.execute(
                text(
                    """
                    INSERT INTO library_item_torrents (id, library_item_id, torrent_hash, is_season_pack, created_at, updated_at)
                    VALUES (:id, :item_id, :hash, 0, NOW(), NOW())
                    """
                ),
                {"id": str(uuid.uuid4()), "item_id": row[0], "hash": row[1]},
            )

        db.commit()
        print(f"✅ {len(rows)} torrents migrés avec succès")
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def migrate_added_date_column():
    """Migrate library_items.added_date from TEXT to DATETIME NULL.

    Existing human-readable strings ("5 days ago", "just now", etc.) cannot be
    converted to DATETIME, so we null them out first. The next sync will populate
    real datetime values.
    """
    from sqlalchemy import text

    from app.db import SessionLocal

    inspector = inspect(engine)
    columns = {col["name"]: col for col in inspector.get_columns("library_items")}
    if "added_date" not in columns:
        print("⚠️  added_date column not found in library_items, skipping migration")
        return

    col_type = str(columns["added_date"]["type"]).upper()
    if "TEXT" not in col_type and "VARCHAR" not in col_type and "LONGTEXT" not in col_type:
        print("✅ added_date is already a non-text type, skipping migration")
        return

    print("🔄 Migrating library_items.added_date from TEXT → DATETIME ...")
    db = SessionLocal()
    try:
        # Step 1: drop the NOT NULL constraint while keeping TEXT type, so we can null values
        db.execute(text("ALTER TABLE library_items MODIFY COLUMN added_date TEXT NULL"))
        db.commit()
        # Step 2: null out the stale human-readable strings
        db.execute(text("UPDATE library_items SET added_date = NULL"))
        db.commit()
        # Step 3: change to DATETIME now that all values are NULL
        db.execute(text("ALTER TABLE library_items MODIFY COLUMN added_date DATETIME NULL"))
        db.commit()
        print("✅ added_date column migrated to DATETIME NULL (existing rows nulled — re-sync to repopulate)")
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def migrate_add_jellyfin_id_to_library_items():
    """Add jellyfin_id VARCHAR(255) column to library_items if it doesn't exist."""
    from sqlalchemy import text

    from app.db import SessionLocal

    inspector = inspect(engine)
    columns = {col["name"] for col in inspector.get_columns("library_items")}
    if "jellyfin_id" in columns:
        print("✅ jellyfin_id already exists on library_items, skipping")
        return

    print("🔄 Adding jellyfin_id column to library_items...")
    db = SessionLocal()
    try:
        db.execute(text("ALTER TABLE library_items ADD COLUMN jellyfin_id VARCHAR(255) NULL"))
        db.execute(text("CREATE INDEX idx_library_items_jellyfin_id ON library_items (jellyfin_id)"))
        db.commit()
        print("✅ jellyfin_id column added to library_items")
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def migrate_add_media_path_to_library_items():
    """Add media_path TEXT column to library_items if it doesn't exist."""
    from sqlalchemy import text

    from app.db import SessionLocal

    inspector = inspect(engine)
    columns = {col["name"] for col in inspector.get_columns("library_items")}
    if "media_path" in columns:
        print("✅ media_path already exists on library_items, skipping")
        return

    print("🔄 Adding media_path column to library_items...")
    db = SessionLocal()
    try:
        db.execute(text("ALTER TABLE library_items ADD COLUMN media_path TEXT NULL"))
        db.commit()
        print("✅ media_path column added to library_items")
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def migrate_add_media_streams_to_library_items():
    """Add media_streams JSON column to library_items if it doesn't exist."""
    from sqlalchemy import text

    from app.db import SessionLocal

    inspector = inspect(engine)
    columns = {col["name"] for col in inspector.get_columns("library_items")}
    if "media_streams" in columns:
        print("✅ media_streams already exists on library_items, skipping")
        return

    print("🔄 Adding media_streams column to library_items...")
    db = SessionLocal()
    try:
        db.execute(text("ALTER TABLE library_items ADD COLUMN media_streams JSON NULL"))
        db.commit()
        print("✅ media_streams column added to library_items")
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def migrate_add_media_streams_to_episodes():
    """Add media_streams JSON column to episodes if it doesn't exist."""
    from sqlalchemy import text

    from app.db import SessionLocal

    inspector = inspect(engine)
    columns = {col["name"] for col in inspector.get_columns("episodes")}
    if "media_streams" in columns:
        print("✅ media_streams already exists on episodes, skipping")
        return

    print("🔄 Adding media_streams column to episodes...")
    db = SessionLocal()
    try:
        db.execute(text("ALTER TABLE episodes ADD COLUMN media_streams JSON NULL"))
        db.commit()
        print("✅ media_streams column added to episodes")
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def migrate_add_watched_to_library_items():
    """Add watched TINYINT(1) column to library_items if it doesn't exist."""
    from sqlalchemy import text

    from app.db import SessionLocal

    inspector = inspect(engine)
    columns = {col["name"] for col in inspector.get_columns("library_items")}
    if "watched" in columns:
        print("✅ watched already exists on library_items, skipping")
        return

    print("🔄 Adding watched column to library_items...")
    db = SessionLocal()
    try:
        db.execute(text("ALTER TABLE library_items ADD COLUMN watched TINYINT(1) NOT NULL DEFAULT 0"))
        db.execute(text("CREATE INDEX idx_library_items_watched ON library_items (watched)"))
        db.commit()
        print("✅ watched column added to library_items")
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def migrate_add_watched_to_episodes():
    """Add watched TINYINT(1) column to episodes if it doesn't exist."""
    from sqlalchemy import text

    from app.db import SessionLocal

    inspector = inspect(engine)
    columns = {col["name"] for col in inspector.get_columns("episodes")}
    if "watched" in columns:
        print("✅ watched already exists on episodes, skipping")
        return

    print("🔄 Adding watched column to episodes...")
    db = SessionLocal()
    try:
        db.execute(text("ALTER TABLE episodes ADD COLUMN watched TINYINT(1) NOT NULL DEFAULT 0"))
        db.execute(text("CREATE INDEX idx_episodes_watched ON episodes (watched)"))
        db.commit()
        print("✅ watched column added to episodes")
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def migrate_add_prowlarr_to_service_configurations_enum():
    """Add 'prowlarr' to the service_configurations.service_name ENUM if not already present."""
    from sqlalchemy import text

    from app.db import SessionLocal

    inspector = inspect(engine)
    columns = {col["name"]: col for col in inspector.get_columns("service_configurations")}
    if "service_name" not in columns:
        print("⚠️  service_name column not found in service_configurations, skipping")
        return

    col_type = str(columns["service_name"]["type"])
    if "prowlarr" in col_type.lower():
        print("✅ 'prowlarr' already in service_configurations.service_name ENUM, skipping")
        return

    # Column may be VARCHAR — only ALTER if it's an ENUM
    if "enum" not in col_type.lower():
        print("✅ service_configurations.service_name is not an ENUM, skipping")
        return

    print("🔄 Adding 'prowlarr' to service_configurations.service_name ENUM...")
    db = SessionLocal()
    try:
        db.execute(
            text(
                "ALTER TABLE service_configurations MODIFY COLUMN service_name "
                "ENUM('jellyfin','jellyseerr','sonarr','radarr','qbittorrent','prowlarr') NOT NULL"
            )
        )
        db.commit()
        print("✅ 'prowlarr' added to service_configurations.service_name ENUM")
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def migrate_add_prowlarr_to_sync_metadata_enum():
    """Add 'prowlarr' to the sync_metadata.service_name ENUM if not already present."""
    from sqlalchemy import text

    from app.db import SessionLocal

    inspector = inspect(engine)
    columns = {col["name"]: col for col in inspector.get_columns("sync_metadata")}
    if "service_name" not in columns:
        print("⚠️  service_name column not found in sync_metadata, skipping")
        return

    col_type = str(columns["service_name"]["type"])
    if "prowlarr" in col_type.lower():
        print("✅ 'prowlarr' already in sync_metadata.service_name ENUM, skipping")
        return

    print("🔄 Adding 'prowlarr' to sync_metadata.service_name ENUM...")
    db = SessionLocal()
    try:
        db.execute(
            text(
                "ALTER TABLE sync_metadata MODIFY COLUMN service_name "
                "ENUM('jellyfin','jellyseerr','sonarr','radarr','qbittorrent','prowlarr') NOT NULL"
            )
        )
        db.commit()
        print("✅ 'prowlarr' added to sync_metadata.service_name ENUM")
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def migrate_add_radarr_to_service_configurations_enum():
    """Add 'radarr' to the service_configurations.service_name ENUM if not already present."""
    from sqlalchemy import text

    from app.db import SessionLocal

    inspector = inspect(engine)
    columns = {col["name"]: col for col in inspector.get_columns("service_configurations")}
    if "service_name" not in columns:
        print("⚠️  service_name column not found in service_configurations, skipping")
        return

    col_type = str(columns["service_name"]["type"])
    if "radarr" in col_type.lower():
        print("✅ 'radarr' already in service_configurations.service_name ENUM, skipping")
        return

    if "enum" not in col_type.lower():
        print("✅ service_configurations.service_name is not an ENUM, skipping")
        return

    print("🔄 Adding 'radarr' to service_configurations.service_name ENUM...")
    db = SessionLocal()
    try:
        db.execute(
            text(
                "ALTER TABLE service_configurations MODIFY COLUMN service_name "
                "ENUM('jellyfin','jellyseerr','sonarr','radarr','qbittorrent','prowlarr') NOT NULL"
            )
        )
        db.commit()
        print("✅ 'radarr' added to service_configurations.service_name ENUM")
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def migrate_add_radarr_to_sync_metadata_enum():
    """Add 'radarr' to the sync_metadata.service_name ENUM if not already present."""
    from sqlalchemy import text

    from app.db import SessionLocal

    inspector = inspect(engine)
    columns = {col["name"]: col for col in inspector.get_columns("sync_metadata")}
    if "service_name" not in columns:
        print("⚠️  service_name column not found in sync_metadata, skipping")
        return

    col_type = str(columns["service_name"]["type"])
    if "radarr" in col_type.lower():
        print("✅ 'radarr' already in sync_metadata.service_name ENUM, skipping")
        return

    if "enum" not in col_type.lower():
        print("✅ sync_metadata.service_name is not an ENUM, skipping")
        return

    print("🔄 Adding 'radarr' to sync_metadata.service_name ENUM...")
    db = SessionLocal()
    try:
        db.execute(
            text(
                "ALTER TABLE sync_metadata MODIFY COLUMN service_name "
                "ENUM('jellyfin','jellyseerr','sonarr','radarr','qbittorrent','prowlarr') NOT NULL"
            )
        )
        db.commit()
        print("✅ 'radarr' added to sync_metadata.service_name ENUM")
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def migrate_sync_metadata_service_name_to_varchar():
    """Convert sync_metadata.service_name from ENUM to VARCHAR(50).

    SQLAlchemy's native MySQL ENUM type builds _object_lookup at class-definition time.
    On some installs the lookup misses 'radarr', causing a LookupError when reading rows.
    Converting to VARCHAR bypasses this entirely, matching how service_configurations
    already stores service_name.
    """
    from sqlalchemy import text

    from app.db import SessionLocal

    inspector = inspect(engine)
    columns = {col["name"]: col for col in inspector.get_columns("sync_metadata")}
    if "service_name" not in columns:
        print("⚠️  service_name column not found in sync_metadata, skipping")
        return

    col_type = str(columns["service_name"]["type"])
    if "enum" not in col_type.lower():
        print("✅ sync_metadata.service_name is already VARCHAR/non-ENUM, skipping")
        return

    print("🔄 Converting sync_metadata.service_name from ENUM → VARCHAR(50)...")
    db = SessionLocal()
    try:
        db.execute(text("ALTER TABLE sync_metadata MODIFY COLUMN service_name VARCHAR(50) NOT NULL"))
        db.commit()
        print("✅ sync_metadata.service_name converted to VARCHAR(50)")
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def migrate_add_available_to_jellyseerr_requests_status():
    """Add 'AVAILABLE' to jellyseerr_requests.status ENUM if not already present."""
    from sqlalchemy import text

    from app.db import SessionLocal

    inspector = inspect(engine)
    columns = {col["name"]: col for col in inspector.get_columns("jellyseerr_requests")}
    if "status" not in columns:
        print("⚠️  status column not found in jellyseerr_requests, skipping")
        return

    col_type = str(columns["status"]["type"])
    if "available" in col_type.lower():
        print("✅ 'AVAILABLE' already in jellyseerr_requests.status ENUM, skipping")
        return

    if "enum" not in col_type.lower():
        print("✅ jellyseerr_requests.status is not an ENUM, skipping")
        return

    print("🔄 Adding 'AVAILABLE' to jellyseerr_requests.status ENUM...")
    db = SessionLocal()
    try:
        db.execute(
            text(
                "ALTER TABLE jellyseerr_requests MODIFY COLUMN status "
                "ENUM('PENDING','APPROVED','DECLINED','AVAILABLE') NOT NULL DEFAULT 'PENDING'"
            )
        )
        db.commit()
        print("✅ 'AVAILABLE' added to jellyseerr_requests.status ENUM")
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def show_table_info():
    """Affiche les informations détaillées sur toutes les tables"""
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    print("\n" + "=" * 60)
    print("📋 INFORMATIONS DÉTAILLÉES DES TABLES")
    print("=" * 60)

    for table_name in sorted(tables):
        columns = inspector.get_columns(table_name)
        indexes = inspector.get_indexes(table_name)

        print(f"\n📌 Table: {table_name}")
        print(f"   Colonnes: {len(columns)}")
        for col in columns:
            col_type = str(col["type"])
            nullable = "NULL" if col["nullable"] else "NOT NULL"
            print(f"      - {col['name']}: {col_type} {nullable}")

        if indexes:
            print(f"   Index: {len(indexes)}")
            for idx in indexes:
                unique = "UNIQUE" if idx["unique"] else ""
                print(f"      - {idx['name']} {unique}")


if __name__ == "__main__":
    print("=" * 60)
    print("🔧 MIGRATION BASE DE DONNÉES - ANALYTICS")
    print("=" * 60)

    # Créer les tables
    success = create_analytics_tables()

    if success:
        # Afficher les infos
        show_table_info()
        print("\n" + "=" * 60)
        print("✅ Migration terminée avec succès!")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("❌ Migration échouée")
        print("=" * 60)


def migrate_add_genres_to_library_items():
    """Add genres JSON column to library_items if it doesn't exist."""
    from sqlalchemy import text

    from app.db import SessionLocal

    inspector = inspect(engine)
    columns = {col["name"] for col in inspector.get_columns("library_items")}
    if "genres" in columns:
        print("✅ genres already exists on library_items, skipping")
        return

    print("🔄 Adding genres column to library_items...")
    db = SessionLocal()
    try:
        db.execute(text("ALTER TABLE library_items ADD COLUMN genres JSON NULL"))
        db.commit()
        print("✅ genres column added to library_items")
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()
