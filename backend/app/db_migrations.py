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
