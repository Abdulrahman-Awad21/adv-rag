from .BaseDataModel import BaseDataModel
from .db_schemes import Asset # Asset DB Scheme
from sqlalchemy.future import select
from sqlalchemy import update, func as sqlalchemy_func, delete # ✅ ADDED delete
from sqlalchemy.orm import sessionmaker # For type hinting async_db_session_factory
from sqlalchemy.sql import text as sql_text # For executing raw SQL DROP TABLE
from typing import Optional, Dict, Any, List

class AssetModel(BaseDataModel):

    def __init__(self, db_client: sessionmaker): 
        super().__init__(db_client=db_client)

    @classmethod
    async def create_instance(cls, db_client: sessionmaker): 
        instance = cls(db_client)
        return instance

    async def create_asset(self, asset: Asset) -> Asset:
        async with self.db_client() as session: # type: ignore #告诉 MyPy 忽略此行可能出现的类型检查错误
            async with session.begin(): # This ensures the session is active and a transaction is begun
                session.add(asset)
                # After add, and before commit within the same transaction, 
                # SQLAlchemy often makes the PK available if it's a sequence.
                # To be absolutely sure all DB-generated values (like UUIDs, timestamps) are populated,
                # we will flush and then refresh.
                await session.flush() # Send changes to DB, assign PK if sequence-generated
                await session.refresh(asset) # Populate asset object with all DB-generated values
            # The transaction is committed automatically when exiting the "async with session.begin()" block
            # If an error occurs within the block, it's rolled back.
        # asset object should now be populated with asset_id, asset_uuid, created_at
        return asset


    async def get_all_project_assets(self, asset_project_id: int, asset_type: Optional[str] = None) -> List[Asset]:
        async with self.db_client() as session: # type: ignore
            stmt = select(Asset).where(Asset.asset_project_id == asset_project_id)
            if asset_type:
                stmt = stmt.where(Asset.asset_type == asset_type)
            stmt = stmt.order_by(Asset.created_at.desc())
            
            result = await session.execute(stmt)
            records = result.scalars().all()
        return records

    async def get_asset_record(self, asset_project_id: int, asset_name: str) -> Optional[Asset]:
        async with self.db_client() as session: # type: ignore
            stmt = select(Asset).where(
                Asset.asset_project_id == asset_project_id,
                Asset.asset_name == asset_name
            )
            result = await session.execute(stmt)
            record = result.scalar_one_or_none()
        return record

    async def get_asset_by_id(self, asset_db_id: int) -> Optional[Asset]:
        async with self.db_client() as session: # type: ignore
            # Using session.get is a more direct way to fetch by primary key
            record = await session.get(Asset, asset_db_id)
        return record

    async def update_asset_config_pgsql_tables(self, asset_db_id: int, pgsql_tables_info: List[Dict[str, str]]) -> bool:
        async with self.db_client() as session: # type: ignore
            async with session.begin():
                current_asset_result = await session.execute(
                    select(Asset.asset_config).where(Asset.asset_id == asset_db_id)
                )
                current_config = current_asset_result.scalar_one_or_none()

                if current_config is None:
                    current_config = {}
                
                if not isinstance(current_config, dict):
                    print(f"Warning: asset_config for asset_id {asset_db_id} is not a dict, overwriting.")
                    current_config = {}

                current_config['pgsql_tables'] = pgsql_tables_info
                
                stmt = (
                    update(Asset)
                    .where(Asset.asset_id == asset_db_id)
                    .values(asset_config=current_config, updated_at=sqlalchemy_func.now())
                )
                result = await session.execute(stmt)
            # Commit happens automatically on exiting session.begin()
            return result.rowcount > 0

    async def delete_asset_and_associated_data(self, asset_db_id: int, async_db_session_factory: Optional[sessionmaker] = None) -> bool:
        """
        Deletes an asset, its associated PGSQL tables, and its chunks.
        Uses self.db_client for most operations, but can use a passed factory for DDL if needed (though self.db_client should suffice).
        """
        db_factory_to_use = async_db_session_factory if async_db_session_factory else self.db_client

        asset_to_delete: Optional[Asset] = None
        async with db_factory_to_use() as session: # type: ignore
             asset_to_delete = await session.get(Asset, asset_db_id)

        if not asset_to_delete:
            print(f"Asset with ID {asset_db_id} not found for deletion.")
            return False

        # 1. Drop associated PGSQL tables
        if asset_to_delete.asset_config and 'pgsql_tables' in asset_to_delete.asset_config:
            if isinstance(asset_to_delete.asset_config['pgsql_tables'], list):
                async with db_factory_to_use() as pg_ddl_session: # type: ignore
                    async with pg_ddl_session.begin(): # Ensure DDL is in a transaction
                        for table_info in asset_to_delete.asset_config['pgsql_tables']:
                            if isinstance(table_info, dict):
                                table_name = table_info.get('db_table_name')
                                if table_name:
                                    try:
                                        print(f"Dropping PostgreSQL table: \"{table_name}\" for asset {asset_db_id}")
                                        await pg_ddl_session.execute(sql_text(f"DROP TABLE IF EXISTS \"{table_name}\" CASCADE;"))
                                    except Exception as e:
                                        print(f"Error dropping table \"{table_name}\": {e}")
                                        # Optionally re-raise or collect errors
                    # Commit DDL for dropping tables

        # 2. Delete associated chunks
        # Assuming you have a ChunkModel similar to AssetModel
        # from .ChunkModel import ChunkModel # You would import this
        # chunk_model = await ChunkModel.create_instance(db_factory_to_use) # type: ignore
        # await chunk_model.delete_chunks_by_asset_id(asset_id=asset_db_id)
        # For directness here, if ChunkModel is not readily available or to avoid circular deps:
        async with db_factory_to_use() as chunk_session: # type: ignore
            from .db_schemes import DataChunk # Import locally to avoid top-level circular if an issue
            async with chunk_session.begin():
                stmt = delete(DataChunk).where(DataChunk.chunk_asset_id == asset_db_id)
                await chunk_session.execute(stmt)
            # Commit chunk deletion

        # 3. Delete asset record itself
        async with db_factory_to_use() as asset_delete_session: # type: ignore
            async with asset_delete_session.begin():
                asset_in_session = await asset_delete_session.get(Asset, asset_db_id)
                if asset_in_session:
                    await asset_delete_session.delete(asset_in_session)
                else:
                    print(f"Asset with ID {asset_db_id} was not found in session for final deletion step.")
                    return False 
            # Commit asset deletion
            
        print(f"Asset {asset_db_id} and its associated data deleted successfully.")
        return True