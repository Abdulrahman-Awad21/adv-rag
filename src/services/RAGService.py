import logging
import re
from typing import List, Any, Tuple, Optional
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
        return await self.vectordb_client.search_by_vector(collection_name=collection_name, vector=query_vector[0], limit=limit)

    async def answer_question(self, project: Project, query: str, request: Request, limit: int = 10):
        retrieved_docs = await self.search_collection(project=project, query=query, limit=limit)
        if not retrieved_docs:
            return "I'm sorry, I couldn't find any information related to your question.", None, None

        schema_doc = None
        text_docs = []
        for doc in retrieved_docs:
            if doc.metadata and doc.metadata.get("type") == "pgsql_table_schema":
                if schema_doc is None:
                    schema_doc = doc
            else:
                text_docs.append(doc)

        if schema_doc:
            logger.info("Hybrid RAG path triggered (Schema found).")
            return await self._get_hybrid_answer(query=query, schema_doc=schema_doc, text_docs=text_docs, request=request)
        else:
            logger.info("Standard Text RAG path triggered.")
            answer, full_prompt = self._get_answer_from_text(query=query, text_docs=text_docs)
            return answer, full_prompt, None

    def _parse_llm_final_answer(self, llm_output: str) -> Tuple[Optional[str], str]:
        if not llm_output:
            return None, ""
        match = re.search(r"<think>(.*?)</think>(.*)", llm_output, re.DOTALL)
        if match:
            llm_thoughts = match.group(1).strip()
            clean_answer = match.group(2).strip()
            return llm_thoughts, clean_answer
        return None, llm_output.strip()

    async def _execute_sql_from_schema(self, query: str, schema_doc: RetrievedDocument, request: Request):
        sql_gen_prompt = self.template_parser.get("rag", "sql_generation_prompt", vars={"schema": schema_doc.text, "question": query})
        llm_sql_response = self.generation_client.generate_text(prompt=sql_gen_prompt)
        if not llm_sql_response:
            logger.error("LLM failed to generate SQL.")
            return "Error: The AI failed to generate a database query.", ""

        generated_sql = self._extract_sql_from_llm_response(llm_sql_response)
        clean_sql = generated_sql.strip().replace('`', '')

        if not clean_sql or not clean_sql.upper().startswith("SELECT"):
            logger.warning(f"LLM generated a non-SELECT or empty statement: '{clean_sql}' from full response: '{llm_sql_response}'")
            return "No valid query could be generated to retrieve data.", generated_sql

        try:
            async with request.app.db_client() as session:
                result_proxy = await session.execute(sql_text(clean_sql))
                headers = list(result_proxy.keys())
                rows = result_proxy.all()
                sql_results_text = self._format_sql_results_for_llm(headers, rows)
        except Exception as e:
            logger.error(f"Executing generated SQL failed: {e}")
            sql_results_text = f"There was an error running the query: {str(e)}"
        return sql_results_text, clean_sql

    def _get_answer_from_text(self, query: str, text_docs: List[RetrievedDocument]):
        text_docs_context = "\n---\n".join([self.generation_client.process_text(doc.text) for doc in text_docs])
        synthesis_prompt = self.template_parser.get("rag", "text_synthesis_prompt", vars={"question": query, "text_documents": text_docs_context})
        
        raw_answer = self.generation_client.generate_text(prompt=synthesis_prompt)
        llm_thoughts, clean_answer = self._parse_llm_final_answer(raw_answer)

        if llm_thoughts:
            final_response = f"<think>{llm_thoughts}</think>{clean_answer}"
        else:
            final_response = clean_answer
        return final_response, synthesis_prompt

    async def _get_hybrid_answer(self, query: str, schema_doc: RetrievedDocument, text_docs: List[RetrievedDocument], request: Request):
        sql_results_text, generated_sql = await self._execute_sql_from_schema(query=query, schema_doc=schema_doc, request=request)
        text_docs_context = "\n---\n".join([self.generation_client.process_text(doc.text) for doc in text_docs])
        if not text_docs_context:
            text_docs_context = "No additional text information was found."

        synthesis_prompt = self.template_parser.get("rag", "hybrid_synthesis_prompt", vars={"question": query, "sql_results": sql_results_text, "text_documents": text_docs_context})
        raw_final_answer = self.generation_client.generate_text(prompt=synthesis_prompt)
        
        llm_thoughts, clean_final_answer = self._parse_llm_final_answer(raw_final_answer)

        thinking_parts = [
            "Hybrid mode triggered. Most relevant schema found.",
            f"Generated SQL:\n```sql\n{generated_sql or 'N/A'}\n```",
            f"SQL Query Results:\n{sql_results_text}",
            f"Synthesizing with {len(text_docs)} additional text document(s)."
        ]
        if llm_thoughts:
            thinking_parts.append(f"\nLLM's Final Synthesis Reasoning:\n{llm_thoughts}")
        
        # ✅ FIX: Build the content outside the f-string to avoid the SyntaxError
        thinking_content = "\n".join(thinking_parts)
        comprehensive_thinking_block = f"<think>\n{thinking_content}\n</think>"
        
        final_answer_with_context = f"{comprehensive_thinking_block}{clean_final_answer}"
        return final_answer_with_context, synthesis_prompt, None

    def _format_sql_results_for_llm(self, headers: List[str], rows: List[Any]) -> str:
        if not rows:
            return "The query returned no results."
        header_str = "| " + " | ".join(headers) + " |"
        separator_str = "| " + " | ".join(["---"] * len(headers)) + " |"
        rows_str = "\n".join(["| " + " | ".join(str(item) for item in row) + " |" for row in rows])
        return f"Query Results:\n{header_str}\n{separator_str}\n{rows_str}"
        
    def _extract_sql_from_llm_response(self, llm_output: str) -> str:
        if not llm_output: return ""
        if "</think>" in llm_output:
            parts = llm_output.split("</think>")
            potential_sql = parts[-1].strip()
            if potential_sql.upper().startswith("SELECT"):
                return potential_sql
        logger.warning("LLM did not use <think> tags. Falling back to regex extraction.")
        match = re.search(r"SELECT\s+.*?(?:;|$)", llm_output, re.IGNORECASE | re.DOTALL)
        if match: return match.group(0).strip()
        logger.error(f"Could not extract a valid SQL query from LLM output: {llm_output}")
        return ""