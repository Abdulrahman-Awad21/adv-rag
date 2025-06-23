# src/stores/llm/providers/GoogleProvider.py

import google.generativeai as genai
import logging
from typing import List, Union

from ..LLMInterface import LLMInterface
from ..LLMEnums import GoogleEnums, DocumentTypeEnum

class GoogleProvider(LLMInterface):
    """
    An LLM provider for Google's Generative AI models (Gemini).
    """

    def __init__(self, api_key: str,
                       default_input_max_characters: int = 8000,
                       default_generation_max_output_tokens: int = 4096,
                       default_generation_temperature: float = 0.7):
        
        if not api_key:
            raise ValueError("Google API key not provided.")
        
        genai.configure(api_key=api_key)
        
        self.default_input_max_characters = default_input_max_characters
        self.default_generation_max_output_tokens = default_generation_max_output_tokens
        self.default_generation_temperature = default_generation_temperature
        
        self.generation_model_id = None
        self.embedding_model_id = None
        self.embedding_size = None
        
        self.enums = GoogleEnums
        self.logger = logging.getLogger(__name__)
        self.logger.info("GoogleProvider initialized.")


    def set_generation_model(self, model_id: str):
        self.generation_model_id = model_id
        self.logger.info(f"Google generation model set to: {model_id}")


    def set_embedding_model(self, model_id: str, embedding_size: int):
        self.embedding_model_id = model_id
        self.embedding_size = embedding_size
        self.logger.info(f"Google embedding model set to: {model_id}")


    def process_text(self, text: str):
        return text[:self.default_input_max_characters].strip()


    def construct_prompt(self, prompt: str, role: str):
        # Convert standard 'assistant' role to Google's 'model' role
        api_role = self.enums.ASSISTANT.value if role == "assistant" else self.enums.USER.value
        return {"role": api_role, "parts": [prompt]}


    def generate_text(self, prompt: Union[str, dict], chat_history: list = [], max_output_tokens: int = None,
                            temperature: float = None):
        
        if not self.generation_model_id:
            self.logger.error("Google generation model was not set.")
            return None
            
        model = genai.GenerativeModel(self.generation_model_id)
        
        max_output_tokens = max_output_tokens if max_output_tokens is not None else self.default_generation_max_output_tokens
        temperature = temperature if temperature is not None else self.default_generation_temperature

        # Build the chat history for the API call
        api_history = []
        for message in chat_history:
            api_history.append(self.construct_prompt(message.get("content", ""), message.get("role", "user")))

        if isinstance(prompt, dict):
            # Google doesn't have a distinct 'system' role in chat history;
            # it's often prepended or handled by system_instruction.
            # For simplicity and compatibility, we treat it as a user message.
            if prompt.get("system"):
                 api_history.append(self.construct_prompt(prompt["system"], "user"))
            if prompt.get("user"):
                 api_history.append(self.construct_prompt(self.process_text(prompt["user"]), "user"))
        else:
            api_history.append(self.construct_prompt(self.process_text(prompt), "user"))
            
        generation_config = genai.types.GenerationConfig(
            max_output_tokens=max_output_tokens,
            temperature=temperature
        )

        try:
            response = model.generate_content(
                api_history,
                generation_config=generation_config
            )
            return response.text
        except Exception as e:
            self.logger.error(f"Exception during Google API call: {e}")
            return None


    def embed_text(self, text: Union[str, List[str]], document_type: str = None):
        if not self.embedding_model_id:
            self.logger.error("Google embedding model was not set")
            return None
        
        if isinstance(text, str):
            text = [text]
        
        # Map our internal document type to Google's task types for better embedding quality
        task_type = GoogleEnums.RETRIEVAL_DOCUMENT.value
        if document_type == DocumentTypeEnum.QUERY.value:
            task_type = GoogleEnums.RETRIEVAL_QUERY.value
            
        try:
            result = genai.embed_content(
                model=self.embedding_model_id,
                content=text,
                task_type=task_type
            )
            return result['embedding']
        except Exception as e:
            self.logger.error(f"Exception during Google embedding API call: {e}")
            return None