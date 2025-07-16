# FILE: src/routes/nlp.py

from fastapi import APIRouter, status, Request, Depends
from fastapi.responses import JSONResponse
from tqdm.auto import tqdm
import logging

from routes.schemes.nlp import PushRequest, SearchRequest
from models import ResponseSignal
from models.db_schemes import Project, User # Import User
from models.ChunkModel import ChunkModel
from services.IndexingService import IndexingService
from services.RAGService import RAGService
from services.EmailService import EmailService # Import EmailService
from .dependencies import get_project_from_uuid_and_verify_access, get_current_user # Import get_current_user

logger = logging.getLogger('uvicorn.error')

nlp_router = APIRouter(
    prefix="/api/v1/nlp",
    tags=["api_v1", "nlp"],
)

@nlp_router.post("/index/push/{project_uuid}")
async def index_project(
    request: Request, 
    push_request: PushRequest,
    project: Project = Depends(get_project_from_uuid_and_verify_access)
):
    indexing_service = IndexingService(
        vectordb_client=request.app.vectordb_client,
        embedding_client=request.app.embedding_client
    )
    
    collection_name = indexing_service.get_collection_name(project_uuid=str(project.project_uuid))
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

@nlp_router.get("/index/info/{project_uuid}")
async def get_project_index_info(
    request: Request,
    project: Project = Depends(get_project_from_uuid_and_verify_access)
):
    indexing_service = IndexingService(vectordb_client=request.app.vectordb_client, embedding_client=request.app.embedding_client)
    collection_info = await indexing_service.get_collection_info(project=project)
    
    return JSONResponse(content={"signal": ResponseSignal.VECTORDB_COLLECTION_RETRIEVED.value, "collection_info": collection_info})

@nlp_router.post("/index/search/{project_uuid}")
async def search_index(
    request: Request, 
    search_request: SearchRequest,
    project: Project = Depends(get_project_from_uuid_and_verify_access)
):
    rag_service = RAGService(
        generation_client=request.app.generation_client, embedding_client=request.app.embedding_client,
        vectordb_client=request.app.vectordb_client, template_parser=request.app.template_parser
    )
    results = await rag_service.search_collection(project=project, query=search_request.text, limit=search_request.limit)

    if results is None:
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"signal": ResponseSignal.VECTORDB_SEARCH_ERROR.value})
    
    return JSONResponse(content={"signal": ResponseSignal.VECTORDB_SEARCH_SUCCESS.value, "results": [r.model_dump() for r in results]})

@nlp_router.post("/index/answer/{project_uuid}")
async def answer_rag(
    request: Request,
    search_request: SearchRequest,
    project: Project = Depends(get_project_from_uuid_and_verify_access),
    current_user: User = Depends(get_current_user) # Get the user making the request
):
    rag_service = RAGService(
        generation_client=request.app.generation_client,
        embedding_client=request.app.embedding_client,
        vectordb_client=request.app.vectordb_client,
        template_parser=request.app.template_parser
    )
    
    # Get the email service from the application instance
    email_service: EmailService = request.app.email_service

    response_data = await rag_service.answer_question(
        project=project, 
        query=search_request.text, 
        request=request, 
        user=current_user,
        email_service=email_service,
        limit=search_request.limit
    )

    if not response_data or not response_data.get("answer"):
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"signal": ResponseSignal.RAG_ANSWER_ERROR.value})
    
    return JSONResponse(content={
        "signal": ResponseSignal.RAG_ANSWER_SUCCESS.value,
        "answer": response_data.get("answer"),
        "thinking": response_data.get("thinking"),
        "full_prompt": response_data.get("full_prompt"),
        "chat_history": response_data.get("chat_history")
    })
