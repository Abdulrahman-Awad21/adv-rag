# src/services/AdminService.py

import shutil
import os
import logging
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import text as sql_text

from controllers.DataController import DataController
from config.settings import Settings

logger = logging.getLogger('uvicorn.error')

class AdminService:
    def __init__(self, db_client: sessionmaker, app_settings: Settings):
        self.db_client = db_client
        self.app_settings = app_settings
        self.data_controller = DataController()

    async def nuke_and_rebuild_db(self) -> dict:
        """
        Performs a total system wipe. Drops all known dynamic and static tables
        and clears the asset file system. The Alembic entrypoint will handle
        recreating the core static tables on the next app startup.
        """
        
        # Part 1: Wipe the physical files from the asset directory
        files_path = self.data_controller.files_dir
        if os.path.exists(files_path):
            try:
                # Delete everything inside the 'files' directory
                for item in os.listdir(files_path):
                    item_path = os.path.join(files_path, item)
                    if os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                    else:
                        os.remove(item_path)
                logger.info(f"Successfully cleared all contents of the asset directory: {files_path}")
            except Exception as e:
                logger.error(f"Failed to clear asset directory: {e}")
                raise  # Stop the process if we can't clear files

        # Part 2: Nuke the database tables
        dropped_tables = []
        async with self.db_client() as session:
            async with session.begin():
                # Get all user-generated tables: core tables, pgvector collections, and pgdata tables
                get_tables_sql = sql_text("""
                    SELECT tablename FROM pg_tables
                    WHERE schemaname = 'public' AND (
                        tablename LIKE 'pgdata_%' OR
                        tablename LIKE 'collection_%' OR
                        tablename IN ('projects', 'assets', 'chunks', 'chat_histories', 'alembic_version')
                    );
                """)
                result = await session.execute(get_tables_sql)
                tables_to_drop = [row[0] for row in result.fetchall()]

                if not tables_to_drop:
                    logger.warning("No user-generated tables found to drop.")
                else:
                    logger.warning(f"Preparing to drop the following tables: {tables_to_drop}")
                    for table in tables_to_drop:
                        try:
                            drop_sql = sql_text(f'DROP TABLE IF EXISTS "{table}" CASCADE;')
                            await session.execute(drop_sql)
                            dropped_tables.append(table)
                            logger.info(f"Dropped table: {table}")
                        except Exception as e:
                            logger.error(f"Failed to drop table '{table}': {e}")
        
        return {
            "status": "System data wipe complete.",
            "details": {
                "asset_directory_cleared": True,
                "database_tables_dropped": dropped_tables
            },
            "next_step": "Please RESTART the application container(s). The entrypoint script will automatically recreate the core database tables."
        }