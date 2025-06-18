# ... (imports remain the same)
from fastapi import APIRouter, Depends, UploadFile, File, status, Request
from fastapi.responses import JSONResponse
import os
import json
import logging
from typing import List

from config.settings import get_settings, Settings
from controllers.DataController import DataController
from models import ResponseSignal, ProcessingEnum
from schemas.processing import Document
from .schemes.data import ProcessRequest
from models.ProjectModel import ProjectModel
from models.ChunkModel import ChunkModel
from models.AssetModel import AssetModel
from models.db_schemes import DataChunk, Asset
from models.enums.AssetTypeEnum import AssetTypeEnum
from services.IngestionService import IngestionService
from services.ProcessingService import ProcessingService
from services.IndexingService import IndexingService
from sqlalchemy.sql import text as sql_text
import aiofiles

# ... (logger and router setup remain the same)
logger = logging.getLogger('uvicorn.error')

data_router = APIRouter(
    prefix="/api/v1/data",
    tags=["api_v1", "data"],
)


# --- The /upload endpoint is now the only place that needs to know about DataController ---
@data_router.post("/upload/{project_id}")
async def upload_data(request: Request, project_id: int, files: List[UploadFile] = File(...),
                      app_settings: Settings = Depends(get_settings)):
    
    project_model = await ProjectModel.create_instance(db_client=request.app.db_client)
    project = await project_model.get_project_or_create_one(project_id=project_id)

    data_controller = DataController() # We only need this for validation and file path generation
    asset_model = await AssetModel.create_instance(db_client=request.app.db_client)

    uploaded_files_info = []

    for file_to_upload in files:
        is_valid, result_signal = data_controller.validate_uploaded_file(file=file_to_upload)
        if not is_valid:
            logger.warning(f"Skipping invalid file: {file_to_upload.filename} - {result_signal}")
            continue 
        
        # CORRECT: generate_unique_filepath now returns the FULL, correct path
        file_path_on_disk, file_id_for_asset = data_controller.generate_unique_filepath(
            orig_file_name=file_to_upload.filename,
            project_id=str(project.project_id)
        )

        # ... (rest of the upload logic is correct and remains the same)
        try:
            async with aiofiles.open(file_path_on_disk, "wb") as f:
                while chunk := await file_to_upload.read(app_settings.FILE_DEFAULT_CHUNK_SIZE):
                    await f.write(chunk)
            actual_file_size = os.path.getsize(file_path_on_disk)
        except Exception as e:
            logger.error(f"Error writing file {file_to_upload.filename}: {e}")
            continue
        # ... (image captioning logic remains the same)
        if file_to_upload.content_type and file_to_upload.content_type.startswith("image"):
            try:
                async with aiofiles.open(file_path_on_disk, "rb") as f_img:
                    image_bytes = await f_img.read()
                caption = request.app.vision_client.caption_image(image_bytes=image_bytes)
                caption_data = {
                    "caption": caption,
                    "metadata": { "source_file": file_to_upload.filename, "type": "image_caption_upload" }
                }
                caption_path = file_path_on_disk + ".caption.json"
                async with aiofiles.open(caption_path, "w", encoding="utf-8") as f_cap:
                    await f_cap.write(json.dumps(caption_data, ensure_ascii=False))
            except Exception as e:
                logger.error(f"Error captioning image {file_to_upload.filename}: {e}")

        asset_resource = Asset(
            asset_project_id=project.project_id,
            asset_type=AssetTypeEnum.FILE.value,
            asset_name=file_id_for_asset,
            asset_size=actual_file_size,
            asset_config={}
        )
        try:
            asset_record = await asset_model.create_asset(asset=asset_resource)
            uploaded_files_info.append({
                "original_filename": file_to_upload.filename,
                "asset_name_stored": asset_record.asset_name,
                "asset_db_id": asset_record.asset_id
            })
        except Exception as e:
            logger.error(f"Error saving asset metadata for {file_to_upload.filename} to DB: {e}")
            if os.path.exists(file_path_on_disk): os.remove(file_path_on_disk)
            if os.path.exists(file_path_on_disk + ".caption.json"): os.remove(file_path_on_disk + ".caption.json")
    # ... (rest of upload function remains the same)
    if not uploaded_files_info:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"signal": ResponseSignal.FILE_UPLOAD_FAILED.value})

    return JSONResponse(content={"signal": ResponseSignal.FILE_UPLOAD_SUCCESS.value, "uploaded_files_details": uploaded_files_info})


# --- The /process endpoint no longer needs to build paths ---
@data_router.post("/process/{project_id}")
async def process_data(request: Request, project_id: int, process_request: ProcessRequest):
    # ... (service and model setup remains the same)
    project_model = await ProjectModel.create_instance(db_client=request.app.db_client)
    project_from_db = await project_model.get_project_or_create_one(project_id=project_id)
    if not project_from_db:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"signal": "project_not_found"})

    asset_model = await AssetModel.create_instance(db_client=request.app.db_client)
    chunk_model = await ChunkModel.create_instance(db_client=request.app.db_client)
    
    ingestion_service = IngestionService(project_id=str(project_from_db.project_id))
    processing_service = ProcessingService()
    indexing_service = IndexingService(
        vectordb_client=request.app.vectordb_client,
        embedding_client=request.app.embedding_client
    )

    # ... (reset logic remains the same)
    if process_request.do_reset == 1:
        collection_name = indexing_service.get_collection_name(project_id=str(project_from_db.project_id))
        await request.app.vectordb_client.delete_collection(collection_name=collection_name)
        await chunk_model.delete_chunks_by_project_id(project_id=project_from_db.project_id)
        all_assets = await asset_model.get_all_project_assets(asset_project_id=project_from_db.project_id)
        async with request.app.db_client() as pg_session:
            async with pg_session.begin():
                for asset in all_assets:
                    if asset.asset_config and 'pgsql_tables' in asset.asset_config:
                        for table_info in asset.asset_config['pgsql_tables']:
                            if table_name := table_info.get('db_table_name'):
                                logger.info(f"Resetting: Dropping PGSQL table: {table_name}")
                                await pg_session.execute(sql_text(f'DROP TABLE IF EXISTS "{table_name}" CASCADE;'))

    target_assets = await asset_model.get_all_project_assets(asset_project_id=project_from_db.project_id, asset_type=AssetTypeEnum.FILE.value)
    if not target_assets:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"signal": ResponseSignal.NO_FILES_ERROR.value})

    total_chunks_inserted = 0
    total_files_processed = 0
    
    # CORRECT: Get project path from the centralized DataController
    data_controller_for_path = DataController()
    project_path = data_controller_for_path.get_project_path(str(project_from_db.project_id))

    for asset in target_assets:
        asset_id_on_disk = asset.asset_name
        file_ext = ingestion_service.get_file_extension(asset_id_on_disk)
        chunks_for_asset: List[Document] = []

        # ... (The rest of the if/elif/else block for processing different file types is correct)
        if file_ext in [ProcessingEnum.CSV.value, ProcessingEnum.XLSX.value]:
             # CORRECT: We need the full path here for the processing service
            full_file_path = os.path.join(project_path, asset_id_on_disk)
            created_tables = await processing_service.etl_tabular_file_to_postgres(
                file_path=full_file_path, # Pass the full, correct path
                file_id_on_disk=asset_id_on_disk, asset_db_id=asset.asset_id, 
                asset_project_id=project_from_db.project_id, asset_model=asset_model, 
                async_db_session_factory=request.app.db_client, sync_engine=request.app.sync_db_engine
            )
            # ... (the rest of the loop is correct)
            for table_info in created_tables:
                schema_text = await processing_service.extract_schema_as_text(
                    table_info['db_table_name'], table_info['columns'], request.app.db_client
                )
                if schema_text:
                    chunks_for_asset.append(Document(page_content=schema_text, metadata={
                        "type": "pgsql_table_schema", "source_asset_id": asset.asset_id, 
                        "pgsql_table_name": table_info['db_table_name']
                    }))
        else: # Handle text, pdf, images
            if file_ext in [ProcessingEnum.TXT.value, ProcessingEnum.PDF.value]:
                if docs := ingestion_service.get_file_content(file_id=asset_id_on_disk):
                    chunks_for_asset.extend(processing_service.chunk_text_content(docs, process_request.chunk_size, process_request.overlap_size))
                if file_ext == ProcessingEnum.PDF.value:
                    chunks_for_asset.extend(ingestion_service.create_caption_chunks_from_pdf_images(asset_id_on_disk, request.app.vision_client))
            elif ingestion_service.get_file_extension(asset_id_on_disk) in ['.png', '.jpg', '.jpeg']:
                if sidecar_doc := ingestion_service.load_caption_sidecar(file_id=asset_id_on_disk):
                    chunks_for_asset.append(sidecar_doc)
        
        # ... (rest of the processing logic remains correct)
        if not chunks_for_asset:
            logger.warning(f"No chunks generated for asset: {asset.asset_name}")
            continue

        db_chunks = [DataChunk(
            chunk_text=chunk.page_content, chunk_metadata=chunk.metadata,
            chunk_order=i + 1, chunk_project_id=project_from_db.project_id,
            chunk_asset_id=asset.asset_id) for i, chunk in enumerate(chunks_for_asset)
        ]

        if db_chunks:
            total_chunks_inserted += await chunk_model.insert_many_chunks(chunks=db_chunks)
        total_files_processed += 1

    return JSONResponse(content={
        "signal": ResponseSignal.PROCESSING_SUCCESS.value,
        "inserted_chunks": total_chunks_inserted,
        "processed_files": total_files_processed
    })