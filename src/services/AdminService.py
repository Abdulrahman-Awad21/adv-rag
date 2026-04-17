# src/services/AdminService.py

import shutil
import os
import logging
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import text as sql_text
from sqlalchemy.ext.asyncio import AsyncEngine

from controllers.DataController import DataController
from config.settings import Settings
from models.db_schemes.adv_rag.schemes import SQLAlchemyBase
from .UserService import UserService
from .EmailService import EmailService

logger = logging.getLogger('uvicorn.error')

class AdminService:
    def __init__(
        self,
        db_engine: AsyncEngine,
        db_client: sessionmaker,
        app_settings: Settings,
        email_service: EmailService
    ):
        self.db_engine = db_engine
        self.db_client = db_client
        self.app_settings = app_settings
        self.email_service = email_service
        self.data_controller = DataController()

    async def nuke_and_rebuild_db(self) -> dict:
        """
        Performs a total system wipe and immediate rebuild.
        It drops all data, recreates the schema, and provisions the initial admin user.
        The system is ready for use immediately after this runs.
        """
        
        # Part 1: Wipe the physical files from the asset directory
        files_path = self.data_controller.files_dir
        if os.path.exists(files_path):
            try:
                shutil.rmtree(files_path)
                os.makedirs(files_path) # Re-create the empty directory
                logger.info(f"Successfully cleared all contents of the asset directory: {files_path}")
            except Exception as e:
                logger.error(f"Failed to clear asset directory: {e}")
                raise

        # Part 2: Nuke the database tables
        dropped_tables = []
        async with self.db_client() as session:
            async with session.begin():
                # Get all user-generated tables and the alembic table
                get_tables_sql = sql_text("""
                    SELECT tablename FROM pg_tables
                    WHERE schemaname = 'public';
                """)
                result = await session.execute(get_tables_sql)
                tables_to_drop = [row[0] for row in result.fetchall()]

                if not tables_to_drop:
                    logger.warning("No tables found in the public schema to drop.")
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
        
        # ==================== START: NEW REBUILD LOGIC ====================
        
        # Part 3: Recreate schema from SQLAlchemy metadata
        logger.info("Recreating database schema from models...")
        try:
            async with self.db_engine.begin() as conn:
                await conn.run_sync(SQLAlchemyBase.metadata.create_all)
                # Also ensure the vector extension is enabled
                await conn.execute(sql_text("CREATE EXTENSION IF NOT EXISTS vector;"))
            logger.info("Database schema recreated successfully.")
        except Exception as e:
            logger.error(f"Failed to recreate database schema: {e}")
            raise

        # Part 4: Re-create the initial admin user
        logger.info("Provisioning initial admin user...")
        user_service = UserService(
            db_client=self.db_client,
            app_settings=self.app_settings,
            email_service=self.email_service
        )
        await user_service.create_initial_admin()
        
        # ===================== END: NEW REBUILD LOGIC =====================

        return {
            "status": "System wipe and rebuild complete.",
            "details": {
                "asset_directory_cleared": True,
                "database_tables_dropped": dropped_tables,
                "database_schema_recreated": True,
                "initial_admin_reprovisioned": True
            },
            "next_step": "System is ready. You can now log in with the initial admin credentials."
        }