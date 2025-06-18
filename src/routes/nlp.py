from fastapi import APIRouter, status, Request
from fastapi.responses import JSONResponse
from tqdm.auto import tqdm
import logging

from routes.schemes.nlp import PushRequest, SearchRequest
from models.ProjectModel import ProjectModel
from models.ChunkModel import ChunkModel
from models import ResponseSignal
from services.IndexingService import IndexingService
from services.RAGService import RAGService

logger = logging.getLogger('uvicorn.error')

nlp_router = APIRouter(
    prefix="/api/v1/nlp",
    tags=["api_v1", "nlp"],
)

@nlp_router.post("/index/push/{project_id}")
async def index_project(request: Request, project_id: int, push_request: PushRequest):
    project_model = await ProjectModel.create_instance(db_client=request.app.db_client)
    project = await project_model.get_project_or_create_one(project_id=project_id)
    if not project:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"signal": ResponseSignal.PROJECT_NOT_FOUND_ERROR.value})

    indexing_service = IndexingService(
        vectordb_client=request.app.vectordb_client,
        embedding_client=request.app.embedding_client
    )
    
    collection_name = indexing_service.get_collection_name(project_id=str(project.project_id))
    await indexing_service.create_collection(collection_name, do_reset=push_request.do_reset)

    chunk_model = await ChunkModel.create_instance(db_client=request.app.db_client)
    total_chunks = await chunk_model.get_total_chunks_count(project_id=project.project_id)
    pbar = tqdm(total=total_chunks, desc="Vector Indexing") if total_chunks > 0 else None
    
    page_no, inserted_count = 1, 0
    while True:
        page_chunks = await chunk_model.get_poject_chunks(project_id=project.project_id, page_no=page_no)
        if not page_chunks:
            break
        
        if await indexing_service.index_chunks(project=project, chunks=page_chunks):
            inserted_count += len(page_chunks)
            if pbar: pbar.update(len(page_chunks))
        else:
            if pbar: pbar.close()
            return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"signal": ResponseSignal.INSERT_INTO_VECTORDB_ERROR.value})
        
        page_no += 1

    if pbar: pbar.close()
    return JSONResponse(content={"signal": ResponseSignal.INSERT_INTO_VECTORDB_SUCCESS.value, "inserted_items_count": inserted_count})

@nlp_router.get("/index/info/{project_id}")
async def get_project_index_info(request: Request, project_id: int):
    project_model = await ProjectModel.create_instance(db_client=request.app.db_client)
    project = await project_model.get_project_or_create_one(project_id=project_id)
    
    indexing_service = IndexingService(vectordb_client=request.app.vectordb_client, embedding_client=request.app.embedding_client)
    collection_info = await indexing_service.get_collection_info(project=project)
    
    return JSONResponse(content={"signal": ResponseSignal.VECTORDB_COLLECTION_RETRIEVED.value, "collection_info": collection_info})

@nlp_router.post("/index/search/{project_id}")
async def search_index(request: Request, project_id: int, search_request: SearchRequest):
    project_model = await ProjectModel.create_instance(db_client=request.app.db_client)
    project = await project_model.get_project_or_create_one(project_id=project_id)
    
    rag_service = RAGService(
        generation_client=request.app.generation_client, embedding_client=request.app.embedding_client,
        vectordb_client=request.app.vectordb_client, template_parser=request.app.template_parser
    )
    results = await rag_service.search_collection(project=project, query=search_request.text, limit=search_request.limit)

    if results is None:
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"signal": ResponseSignal.VECTORDB_SEARCH_ERROR.value})
    
    return JSONResponse(content={"signal": ResponseSignal.VECTORDB_SEARCH_SUCCESS.value, "results": [r.model_dump() for r in results]})

@nlp_router.post("/index/answer/{project_id}")
async def answer_rag(request: Request, project_id: int, search_request: SearchRequest):
    project_model = await ProjectModel.create_instance(db_client=request.app.db_client)
    project = await project_model.get_project_or_create_one(project_id=project_id)

    rag_service = RAGService(
        generation_client=request.app.generation_client,
        embedding_client=request.app.embedding_client,
        vectordb_client=request.app.vectordb_client,
        template_parser=request.app.template_parser
    )

    answer, full_prompt, chat_history = await rag_service.answer_question(
        project=project, query=search_request.text, request=request, limit=search_request.limit
    )

    if not answer:
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"signal": ResponseSignal.RAG_ANSWER_ERROR.value})
    
    return JSONResponse(content={
        "signal": ResponseSignal.RAG_ANSWER_SUCCESS.value,
        "answer": answer, "full_prompt": full_prompt, "chat_history": chat_history
    })