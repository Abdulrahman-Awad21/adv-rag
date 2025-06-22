import logging
from typing import List, Any
from sqlalchemy.sql import text as sql_text 
from fastapi import Request

from stores.llm.LLMInterface import LLMInterface
from stores.vectordb.VectorDBInterface import VectorDBInterface
from stores.llm.templates.template_parser import TemplateParser
from stores.llm.LLMEnums import DocumentTypeEnum
from models.db_schemes import Project, RetrievedDocument

logger = logging.getLogger('uvicorn.error')

class RAGService:
    def __init__(
        self,
        generation_client: LLMInterface,
        embedding_client: LLMInterface,
        vectordb_client: VectorDBInterface,
        template_parser: TemplateParser,
    ):
        self.generation_client = generation_client
        self.embedding_client = embedding_client
        self.vectordb_client = vectordb_client
        self.template_parser = template_parser

    def get_collection_name(self, project_id: str) -> str:
        return f"collection_{self.embedding_client.embedding_size}_{project_id}".strip()

    async def search_collection(self, project: Project, query: str, limit: int) -> List[RetrievedDocument]:
        collection_name = self.get_collection_name(project_id=str(project.project_id))
        query_vector = self.embedding_client.embed_text(text=query, document_type=DocumentTypeEnum.QUERY.value)
        
        if not query_vector or not query_vector[0]:
            logger.warning(f"Could not generate a vector for the query: '{query}'")
            return []
            
        return await self.vectordb_client.search_by_vector(
            collection_name=collection_name, vector=query_vector[0], limit=limit
        )

    async def answer_question(self, project: Project, query: str, request: Request, limit: int = 10):
        retrieved_docs = await self.search_collection(project=project, query=query, limit=limit)
        if not retrieved_docs:
            return None, None, None

        # ✅ UPDATED: Iterate through all retrieved docs to find the first schema document.
        for doc in retrieved_docs:
            if doc.metadata and doc.metadata.get("type") == "pgsql_table_schema":
                logger.info("SQL RAG path triggered by a schema document.")
                return await self._get_answer_from_sql(query=query, schema_doc=doc, request=request)

        # ✅ UPDATED: If no schema is found after checking all docs, fall back to text RAG.
        logger.info("Standard Text RAG path triggered as no schema was found in retrieved docs.")
        return self._get_answer_from_text(query=query, text_docs=retrieved_docs)

    async def _get_answer_from_sql(self, query: str, schema_doc: RetrievedDocument, request: Request):
        sql_gen_prompt = self.template_parser.get(
            "rag", "sql_generation_prompt", 
            vars={"schema": schema_doc.text, "question": query}
        )
        
        llm_sql_response = self.generation_client.generate_text(prompt=sql_gen_prompt)
        if not llm_sql_response:
            logger.error("LLM failed to generate SQL.")
            return "Sorry, I had trouble formulating a database query for your question.", sql_gen_prompt, None

        generated_sql = self._extract_sql_from_llm_response(llm_sql_response)
        clean_sql = generated_sql.strip().replace('`', '').replace(';', '')

        if not clean_sql.upper().startswith("SELECT"):
            logger.error(f"LLM generated a non-SELECT statement: {clean_sql}")
            return "Sorry, I can only perform read-only queries.", sql_gen_prompt, None

        try:
            async with request.app.db_client() as session:
                result_proxy = await session.execute(sql_text(clean_sql))
                headers = list(result_proxy.keys())
                rows = result_proxy.all()
                sql_results_text = self._format_sql_results_for_llm(headers, rows)
        except Exception as e:
            logger.error(f"Executing generated SQL failed: {e}")
            sql_results_text = f"There was an error running the query: {str(e)}"

        final_answer_prompt = self.template_parser.get(
            "rag", "final_answer_prompt", 
            vars={"question": query, "sql_results": sql_results_text}
        )
        final_answer = self.generation_client.generate_text(prompt=final_answer_prompt)
        
        thinking_process = f"<think>\nGenerated SQL:\n```sql\n{clean_sql}\n```\n\nQuery Results:\n{sql_results_text}\n</think>"
        final_answer_with_context = f"{thinking_process}{final_answer}"

        return final_answer_with_context, final_answer_prompt, None

    def _get_answer_from_text(self, query: str, text_docs: List[RetrievedDocument]):
        system_prompt = self.template_parser.get("rag", "system_prompt")
        documents_prompts = "\n".join([
            self.template_parser.get("rag", "document_prompt", {"doc_num": idx + 1, "chunk_text": self.generation_client.process_text(doc.text)})
            for idx, doc in enumerate(text_docs)
        ])
        footer_prompt = self.template_parser.get("rag", "footer_prompt", {"query": query})
        
        chat_history = [
            self.generation_client.construct_prompt(prompt=system_prompt, role=self.generation_client.enums.SYSTEM.value)
        ]
        full_prompt = "\n\n".join([documents_prompts, footer_prompt])
        answer = self.generation_client.generate_text(prompt=full_prompt, chat_history=chat_history)
        
        return answer, full_prompt, chat_history

    def _format_sql_results_for_llm(self, headers: List[str], rows: List[Any]) -> str:
        if not rows:
            return "The SQL query returned no results."
        header_str = "| " + " | ".join(headers) + " |"
        separator_str = "| " + " | ".join(["---"] * len(headers)) + " |"
        rows_str = "\n".join(["| " + " | ".join(str(item) for item in row) + " |" for row in rows])
        return f"Query Results:\n{header_str}\n{separator_str}\n{rows_str}"
        
    def _extract_sql_from_llm_response(self, llm_output: str) -> str:
        if not llm_output:
            return ""
        if "</think>" in llm_output:
            return llm_output.split("</think>")[-1].strip()
        if select_pos := llm_output.upper().find("SELECT") != -1:
            return llm_output[select_pos:]
        return llm_output