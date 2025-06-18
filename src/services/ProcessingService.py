import os
import re
import uuid
import pandas as pd
import sqlalchemy
import logging
from typing import List, Dict, Any
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import text as sql_text

from models.enums.ProcessingEnum import ProcessingEnum
from models.AssetModel import AssetModel
from schemas.processing import Document  # CORRECTED IMPORT PATH

logger = logging.getLogger('uvicorn.error')

class ProcessingService:

    def chunk_text_content(self, documents: List[Document], chunk_size: int, overlap_size: int) -> List[Document]:
        texts = [doc.page_content for doc in documents]
        metadatas = [doc.metadata for doc in documents]
        
        chunks = []
        current_chunk_text = ""
        current_metadata_for_chunk = {} 
        splitter_tag = "\n"

        for i, text_block in enumerate(texts):
            source_metadata = metadatas[i] if i < len(metadatas) else {}
            if not current_chunk_text:
                current_metadata_for_chunk = source_metadata

            lines_in_block = [doc.strip() for doc in text_block.split(splitter_tag) if len(doc.strip()) > 1]
            for line in lines_in_block:
                if len(current_chunk_text) + len(line) + len(splitter_tag) > chunk_size and current_chunk_text:
                    chunks.append(Document(page_content=current_chunk_text.strip(), metadata=dict(current_metadata_for_chunk)))
                    current_chunk_text = ""
                    current_metadata_for_chunk = source_metadata

                current_chunk_text += line + splitter_tag
        
        if current_chunk_text:
            chunks.append(Document(page_content=current_chunk_text.strip(), metadata=dict(current_metadata_for_chunk)))
            
        return chunks

    async def etl_tabular_file_to_postgres(
        self,
        file_path: str,
        file_id_on_disk: str,
        asset_db_id: int,
        asset_project_id: int,
        asset_model: AssetModel,
        async_db_session_factory: sessionmaker,
        sync_engine: sqlalchemy.engine.Engine
    ) -> List[Dict[str, Any]]:
        file_ext = os.path.splitext(file_id_on_disk)[-1].lower()
        created_tables_info = []
        dataframes: Dict[str, pd.DataFrame] = {}

        try:
            if file_ext == ProcessingEnum.CSV.value:
                base_name_key = self._sanitize_sql_identifier(os.path.splitext(file_id_on_disk)[0], prefix="csv_data_")
                df = pd.read_csv(file_path, low_memory=False)
                dataframes[base_name_key] = df
            elif file_ext == ProcessingEnum.XLSX.value:
                xls = pd.ExcelFile(file_path)
                for sheet_name in xls.sheet_names:
                    sanitized_key = self._sanitize_sql_identifier(sheet_name, prefix="sheet_")
                    dataframes[sanitized_key] = xls.parse(sheet_name)
            else:
                return []
        except Exception as e:
            logger.error(f"Error reading tabular file {file_id_on_disk}: {e}")
            return []

        pgsql_table_metadata_for_asset = []

        for sheet_key, df in dataframes.items():
            if df.empty:
                logger.warning(f"DataFrame from '{sheet_key}' in {file_id_on_disk} is empty. Skipping.")
                continue

            db_table_name = f"pgdata_proj{int(asset_project_id)}_asset{asset_db_id}_{sheet_key}"[:63]

            columns_def, columns_schema, sanitized_df_cols = self._prepare_column_definitions(df, sync_engine)
            
            df_to_load = df.copy()
            df_to_load.columns = sanitized_df_cols

            async with async_db_session_factory() as session:
                async with session.begin():
                    try:
                        await session.execute(sql_text(f'DROP TABLE IF EXISTS "{db_table_name}" CASCADE;'))
                        create_sql = f'CREATE TABLE "{db_table_name}" (pg_id SERIAL PRIMARY KEY, {", ".join(columns_def)});'
                        await session.execute(sql_text(create_sql))
                    except Exception as e:
                        logger.error(f"Error creating table '{db_table_name}': {e}")
                        continue
            
            try:
                df_to_load.to_sql(db_table_name, con=sync_engine, if_exists='append', index=False, schema='public')
                logger.info(f"Data from sheet '{sheet_key}' loaded into table: '{db_table_name}'")
                created_tables_info.append({'db_table_name': db_table_name, 'columns': columns_schema})
                pgsql_table_metadata_for_asset.append({"original_sheet_name_key": sheet_key, "db_table_name": db_table_name})
            except Exception as e:
                logger.error(f"Error loading data into '{db_table_name}': {e}")
                async with async_db_session_factory() as session:
                    await session.execute(sql_text(f'DROP TABLE IF EXISTS "{db_table_name}";'))

        if pgsql_table_metadata_for_asset:
            await asset_model.update_asset_config_pgsql_tables(
                asset_db_id=asset_db_id, pgsql_tables_info=pgsql_table_metadata_for_asset
            )
            
        return created_tables_info

    async def extract_schema_as_text(self, table_name: str, columns_info: List[Dict[str, str]], async_db_session_factory: sessionmaker, num_sample_rows: int = 3) -> str:
        parts = [f'Table Name: "{table_name}"', "Columns:"]
        for col in columns_info:
            parts.append(f'- "{col["name"]}" ({col["type"]})')

        if num_sample_rows > 0:
            async with async_db_session_factory() as session:
                try:
                    query = sql_text(f'SELECT * FROM "{table_name}" LIMIT :limit')
                    result = await session.execute(query, {"limit": num_sample_rows})
                    sample_rows = result.mappings().all()
                    
                    if sample_rows:
                        parts.append("\nSample Rows (first few rows):")
                        headers = list(sample_rows[0].keys())
                        parts.append("| " + " | ".join(f'"{h}"' for h in headers) + " |")
                        parts.append("| " + " | ".join(["---"] * len(headers)) + " |")
                        for row in sample_rows:
                            parts.append("| " + " | ".join(str(row.get(h, '')) for h in headers) + " |")
                except Exception as e:
                    logger.warning(f'Could not fetch sample rows for "{table_name}": {e}')
                    parts.append("\nSample Rows: (Could not be retrieved due to an error)")
        return "\n".join(parts)

    def _prepare_column_definitions(self, df: pd.DataFrame, engine: sqlalchemy.engine.Engine):
        defs, schemas, sanitized_cols = [], [], []
        for col_idx, original_name in enumerate(df.columns):
            sanitized_name = self._sanitize_sql_identifier(str(original_name), prefix=f"col{col_idx}_")
            
            temp_name = sanitized_name
            count = 0
            while temp_name in sanitized_cols:
                count += 1
                temp_name = f"{sanitized_name}_{count}"
            sanitized_name = temp_name
            sanitized_cols.append(sanitized_name)

            sa_type = self._get_sqlalchemy_type(df[original_name].dtype)
            defs.append(f'"{sanitized_name}" {sa_type.compile(dialect=engine.dialect)}')
            schemas.append({'name': sanitized_name, 'type': str(sa_type)})
        
        return defs, schemas, sanitized_cols

    def _sanitize_sql_identifier(self, name: str, prefix="col_") -> str:
        name = re.sub(r'\s+', '_', str(name))
        name = re.sub(r'[^0-9a-zA-Z_]', '', name).lower()
        if not name or name[0].isdigit() or name.upper() in {"TABLE", "SELECT", "UPDATE", "DELETE", "INSERT", "FROM", "WHERE", "INDEX", "KEY"}:
             name = prefix + name
        return name[:63] if name else prefix + "unnamed_" + str(uuid.uuid4())[:4]

    def _get_sqlalchemy_type(self, dtype: Any) -> sqlalchemy.types.TypeEngine:
        if pd.api.types.is_integer_dtype(dtype): return sqlalchemy.Integer()
        if pd.api.types.is_float_dtype(dtype): return sqlalchemy.Float()
        if pd.api.types.is_bool_dtype(dtype): return sqlalchemy.Boolean()
        if pd.api.types.is_datetime64_any_dtype(dtype): return sqlalchemy.DateTime()
        return sqlalchemy.Text()