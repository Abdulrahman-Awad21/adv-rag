# FILE: src/services/RAGService.py

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

    def get_collection_name(self, project_uuid: str) -> str:
        """Generates a unique and SQL-safe collection name based on project UUID."""
        sanitized_uuid = project_uuid.replace('-', '_')
        return f"collection_{self.embedding_client.embedding_size}_{sanitized_uuid}".strip()

    async def search_collection(self, project: Project, query: str, limit: int) -> List[RetrievedDocument]:
        collection_name = self.get_collection_name(project_uuid=str(project.project_uuid))
        query_vector = self.embedding_client.embed_text(text=query, document_type=DocumentTypeEnum.QUERY.value)
        if not query_vector or not query_vector[0]:
            logger.warning(f"Could not generate a vector for the query: '{query}'")
            return []
        return await self.vectordb_client.search_by_vector(collection_name=collection_name, vector=query_vector[0], limit=limit)

    def _parse_llm_final_answer(self, llm_output: str) -> Tuple[Optional[str], str]:
        """
        Parses LLM output that may contain multiple <think> blocks.
        Aggregates all content within <think> tags.
        Aggregates all content outside <think> tags as the final answer.
        """
        if not llm_output:
            return None, ""

        parts = re.split(r"(<think>.*?</think>)", llm_output, flags=re.DOTALL)
        
        thinking_parts = []
        answer_parts = []

        for part in parts:
            if not part.strip():
                continue
            
            if part.startswith("<think>") and part.endswith("</think>"):
                match = re.search(r"<think>(.*?)</think>", part, re.DOTALL)
                if match:
                    thinking_parts.append(match.group(1).strip())
            else:
                answer_parts.append(part.strip())

        final_thinking = "\n---\n".join(thinking_parts) if thinking_parts else None
        final_answer = " ".join(answer_parts).strip()
        
        if final_thinking:
            final_thinking_markdown = f"```markdown\n{final_thinking}\n```"
        else:
            final_thinking_markdown = None

        return final_thinking_markdown, final_answer

    def _extract_sql_from_llm_response(self, llm_output: str) -> str:
        if not llm_output: return ""
        _, potential_sql = self._parse_llm_final_answer(llm_output)
        potential_sql = potential_sql.replace('`', '').replace(';', '').strip()
        
        if potential_sql.upper().startswith("SELECT"):
            return potential_sql
            
        logger.warning(f"Could not extract a valid SQL query from LLM output: {llm_output}")
        return ""

    async def _execute_sql_from_schema(self, query: str, schema_doc: RetrievedDocument, request: Request) -> Tuple[str, str]:
        sql_gen_prompt = self.template_parser.get("rag", "sql_generation_prompt", vars={"schema": schema_doc.text, "question": query})
        llm_sql_response = self.generation_client.generate_text(prompt=sql_gen_prompt)
        
        generated_sql = self._extract_sql_from_llm_response(llm_sql_response)
        
        if not generated_sql:
            logger.warning(f"LLM failed to generate a valid SELECT query. Full response: '{llm_sql_response}'")
            return "No valid query could be generated to retrieve data.", "N/A"

        if not generated_sql.upper().startswith("SELECT"):
            logger.error(f"SECURITY: Non-SELECT query was generated and blocked: '{generated_sql}'")
            return "An invalid query was generated and blocked.", "Blocked for security reasons."

        try:
            async with request.app.db_client() as session:
                result_proxy = await session.execute(sql_text(generated_sql))
                headers = list(result_proxy.keys())
                rows = result_proxy.all()
                sql_results_text = self._format_sql_results_for_llm(headers, rows)
        except Exception as e:
            logger.error(f"Executing generated SQL failed: {e}")
            sql_results_text = f"There was an error running the query: {str(e)}"
        
        return sql_results_text, generated_sql

    def _format_sql_results_for_llm(self, headers: List[str], rows: List[Any]) -> str:
        if not rows:
            return "The query returned no results."
        header_str = "| " + " | ".join(headers) + " |"
        separator_str = "| " + " | ".join(["---"] * len(headers)) + " |"
        rows_str = "\n".join(["| " + " | ".join(str(item) for item in row) + " |" for row in rows])
        return f"Query Results:\n{header_str}\n{separator_str}\n{rows_str}"

    async def _get_synthesized_answer(self, query: str, retrieved_docs: List[RetrievedDocument], request: Request) -> Tuple[str, dict, list]:
        schema_doc = None
        text_docs = []
        for doc in retrieved_docs:
            if doc.metadata and doc.metadata.get("type") == "pgsql_table_schema":
                if schema_doc is None: schema_doc = doc
            else:
                text_docs.append(doc)
        
        raw_answer_from_llm = ""
        full_prompt_sent_to_llm = {}
        thinking_log = []

        if schema_doc:
            logger.info("Hybrid RAG path triggered (Schema found).")
            sql_results_text, generated_sql = await self._execute_sql_from_schema(query=query, schema_doc=schema_doc, request=request)
            text_docs_context = "\n---\n".join([doc.text for doc in text_docs]) or "No additional text information was found."
            
            full_prompt_sent_to_llm = self.template_parser.get("rag", "hybrid_synthesis_prompt", vars={"question": query, "sql_results": sql_results_text, "text_documents": text_docs_context})
            raw_answer_from_llm = self.generation_client.generate_text(prompt=full_prompt_sent_to_llm)

            thinking_log.extend([
                "Mode: Hybrid (SQL + Text)",
                f"Generated SQL:\n{generated_sql or 'N/A'}",
                f"SQL Query Results: {sql_results_text}",
                f"Synthesizing with {len(text_docs)} additional text document(s)."
            ])
        else:
            logger.info("Standard Text RAG path triggered.")
            text_docs_context = "\n---\n".join([doc.text for doc in text_docs])
            full_prompt_sent_to_llm = self.template_parser.get("rag", "text_synthesis_prompt", vars={"question": query, "text_documents": text_docs_context})
            raw_answer_from_llm = self.generation_client.generate_text(prompt=full_prompt_sent_to_llm)
            thinking_log.append(f"Mode: Standard Text RAG. Synthesizing with {len(text_docs)} text document(s).")
        
        llm_internal_thoughts, clean_draft_answer = self._parse_llm_final_answer(raw_answer_from_llm)
        
        if llm_internal_thoughts:
            thinking_log.append(f"LLM Synthesis Reasoning:\n{llm_internal_thoughts}")
            
        return "\n".join(thinking_log), clean_draft_answer, full_prompt_sent_to_llm

    async def answer_question(self, project: Project, query: str, request: Request, limit: int = 10) -> dict:
        # Phase 1: Intent Classification
        intent_prompt = self.template_parser.get("rag", "intent_classification_prompt", vars={"question": query})
        llm_response = self.generation_client.generate_text(prompt=intent_prompt)
        
        intent_classification = re.sub(r'[^a-zA-Z_]', '', llm_response).strip().lower()

        if intent_classification == 'violation':
            logger.warning(f"Violation detected for query: '{query}'. Classification: {intent_classification}")
            return {"answer": "I can only answer questions related to the provided documents."}

        # Phase 2: Retrieval
        retrieved_docs = await self.search_collection(project=project, query=query, limit=limit)
        if not retrieved_docs:
            return {"answer": "I'm sorry, I couldn't find any information related to your question."}

        # Phase 3: Synthesis
        thinking_log, draft_clean_answer, full_prompt = await self._get_synthesized_answer(query, retrieved_docs, request)

        # Phase 4: Moderation & Finalization
        final_clean_answer = ""
        if draft_clean_answer.strip() == "NO_ANSWER":
            final_clean_answer = "I'm sorry, I couldn't find a relevant answer in the provided documents."
            thinking_log += "\n\n---\nNOTE: Final answer overridden because synthesis resulted in NO_ANSWER."
        else:
            moderation_prompt = self.template_parser.get("rag", "answer_moderation_prompt", vars={"question": query, "draft_answer": draft_clean_answer})
            raw_moderated_output = self.generation_client.generate_text(prompt=moderation_prompt)

            # ** THE FIX IS HERE: Parse the final output to separate any last-minute thinking. **
            moderator_thinking, final_clean_answer = self._parse_llm_final_answer(raw_moderated_output)
            
            # Append any thoughts from the moderation step to the main thinking log
            if moderator_thinking:
                thinking_log += f"\n\n---\nFinal Moderation/Refinement Step:\n{moderator_thinking}"

        return {
            "answer": final_clean_answer,
            "thinking": thinking_log,
            "full_prompt": full_prompt
        }
    