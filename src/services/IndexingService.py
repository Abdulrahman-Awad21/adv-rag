import logging
from typing import List

from stores.llm.LLMInterface import LLMInterface
from stores.vectordb.VectorDBInterface import VectorDBInterface
from stores.llm.LLMEnums import DocumentTypeEnum
from models.db_schemes import Project, DataChunk

logger = logging.getLogger('uvicorn.error')

class IndexingService:
    def __init__(self, vectordb_client: VectorDBInterface, embedding_client: LLMInterface):
        self.vectordb_client = vectordb_client
        self.embedding_client = embedding_client

    def get_collection_name(self, project_id: str) -> str:
        """Generates a unique collection name based on project ID and embedding size."""
        return f"collection_{self.embedding_client.embedding_size}_{project_id}".strip()

    async def create_collection(self, collection_name: str, do_reset: bool = False):
        """Creates a new vector DB collection if it doesn't exist."""
        await self.vectordb_client.create_collection(
            collection_name=collection_name,
            embedding_size=self.embedding_client.embedding_size,
            do_reset=do_reset,
        )

    async def index_chunks(self, project: Project, chunks: List[DataChunk]):
        """Embeds and indexes a list of data chunks into the vector database."""
        if not chunks:
            return False

        collection_name = self.get_collection_name(project_id=str(project.project_id))
        
        texts = [c.chunk_text for c in chunks]
        metadata = [c.chunk_metadata for c in chunks]
        chunk_ids = [c.chunk_id for c in chunks]

        try:
            vectors = self.embedding_client.embed_text(
                text=texts, 
                document_type=DocumentTypeEnum.DOCUMENT.value
            )
            
            await self.vectordb_client.insert_many(
                collection_name=collection_name, 
                texts=texts, 
                metadata=metadata, 
                vectors=vectors, 
                record_ids=chunk_ids
            )
            return True
        except Exception as e:
            logger.error(f"Failed to index chunks for project {project.project_id}: {e}")
            return False

    async def get_collection_info(self, project: Project) -> dict:
        """Retrieves information about a project's vector collection."""
        collection_name = self.get_collection_name(project_id=str(project.project_id))
        return await self.vectordb_client.get_collection_info(collection_name=collection_name)