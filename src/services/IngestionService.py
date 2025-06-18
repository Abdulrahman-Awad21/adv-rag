import os
import fitz  # PyMuPDF
import json
import logging
from typing import List, Optional
from langchain_community.document_loaders import TextLoader, PyMuPDFLoader
from schemas.processing import Document  # CORRECTED IMPORT PATH
from controllers.ProjectController import ProjectController

logger = logging.getLogger('uvicorn.error')

class IngestionService:
    def __init__(self, project_id: str):
        self.project_id_str = project_id
        self.project_path = ProjectController().get_project_path(project_id=self.project_id_str)

    def get_file_extension(self, file_id: str) -> str:
        return os.path.splitext(file_id)[-1].lower()

    def get_file_content(self, file_id: str) -> List[Document]:
        file_path = os.path.join(self.project_path, file_id)

        if not os.path.exists(file_path):
            return []

        loader = None
        if self.get_file_extension(file_id) == ".txt":
            loader = TextLoader(file_path, encoding="utf-8")
        elif self.get_file_extension(file_id) == ".pdf":
            loader = PyMuPDFLoader(file_path)
        
        if loader:
            try:
                loaded_docs = loader.load()
                return [Document(page_content=doc.page_content, metadata=doc.metadata) for doc in loaded_docs]
            except Exception as e:
                logger.error(f"Error loading {file_id} with Langchain loader: {e}")
                return []
        return []

    def load_caption_sidecar(self, file_id: str) -> Optional[Document]:
        file_path = os.path.join(self.project_path, file_id)
        caption_path = file_path + ".caption.json"
        if os.path.exists(caption_path):
            try:
                with open(caption_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                doc_metadata = data.get("metadata", {})
                if "type" not in doc_metadata:
                    doc_metadata["type"] = "image_caption_sidecar"
                return Document(
                    page_content=data.get("caption", ""),
                    metadata=doc_metadata
                )
            except Exception as e:
                logger.warning(f"Error loading caption sidecar: {caption_path} - {e}")
        return None

    def create_caption_chunks_from_pdf_images(self, pdf_file_id: str, vision_client) -> List[Document]:
        file_path = os.path.join(self.project_path, pdf_file_id)
        if not os.path.exists(file_path): 
            return []
            
        try:
            doc = fitz.open(file_path)
        except Exception as e:
            logger.error(f"Error opening PDF {pdf_file_id} with fitz: {e}")
            return []
            
        caption_chunks = []
        for page_index in range(len(doc)):
            page = doc.load_page(page_index)
            images_info = page.get_images(full=True)
            for img_index, img in enumerate(images_info):
                xref = img[0]
                try:
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    caption = vision_client.caption_image(image_bytes=image_bytes)
                    if caption:
                        caption_chunks.append(Document(
                            page_content=caption,
                            metadata={
                                "type": "image_caption_pdf_extraction",
                                "source_file": pdf_file_id, 
                                "page": page_index + 1,
                                "image_index": img_index + 1
                            }
                        ))
                except Exception as e:
                    logger.warning(f"Failed to extract or caption image xref {xref} from {pdf_file_id}: {e}")
        return caption_chunks