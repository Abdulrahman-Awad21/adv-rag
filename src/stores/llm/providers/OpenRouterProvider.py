# src/stores/llm/providers/OpenRouterProvider.py

from ..LLMInterface import LLMInterface
from ..LLMEnums import OpenAIEnums # OpenRouter is OpenAI-compatible, so we reuse the enums
from openai import OpenAI
import logging
from typing import List, Union

class OpenRouterProvider(LLMInterface):
    """
    An LLM provider for OpenRouter, which offers access to a variety of models
    through an OpenAI-compatible API.
    """

    def __init__(self, api_key: str, app_name: str, app_version: str,
                       default_input_max_characters: int=8000,
                       default_generation_max_output_tokens: int=4096,
                       default_generation_temperature: float=0.7):
        
        self.api_key = api_key
        self.app_name = app_name
        self.app_version = app_version
        
        self.default_input_max_characters = default_input_max_characters
        self.default_generation_max_output_tokens = default_generation_max_output_tokens
        self.default_generation_temperature = default_generation_temperature
        
        self.generation_model_id = None
        self.embedding_model_id = None
        self.embedding_size = None

        if not self.api_key:
            raise ValueError("OpenRouter API key not provided.")

        # OpenRouter uses an OpenAI-compatible API but requires a specific base URL and headers.
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=self.api_key,
            default_headers={
                "HTTP-Referer": f"{self.app_name}-v{self.app_version}",
                "X-Title": self.app_name,
            }
        )

        self.enums = OpenAIEnums # Reusing roles like 'user', 'system', 'assistant'
        self.logger = logging.getLogger(__name__)
        self.logger.info("OpenRouterProvider initialized.")


    def set_generation_model(self, model_id: str):
        # Model ID for OpenRouter includes the provider, e.g., "openai/gpt-4o"
        self.generation_model_id = model_id
        self.logger.info(f"OpenRouter generation model set to: {model_id}")


    def set_embedding_model(self, model_id: str, embedding_size: int):
        self.embedding_model_id = model_id
        self.embedding_size = embedding_size
        self.logger.info(f"OpenRouter embedding model set to: {model_id}")


    def process_text(self, text: str):
        return text[:self.default_input_max_characters].strip()


    def generate_text(self, prompt: Union[str, dict], chat_history: list=[], max_output_tokens: int=None,
                            temperature: float = None):
        
        if not self.client or not self.generation_model_id:
            self.logger.error("OpenRouter client or generation model was not set.")
            return None
        
        max_output_tokens = max_output_tokens if max_output_tokens is not None else self.default_generation_max_output_tokens
        temperature = temperature if temperature is not None else self.default_generation_temperature

        messages_for_api = list(chat_history)

        if isinstance(prompt, dict):
            if prompt.get("system"):
                messages_for_api.append(self.construct_prompt(prompt=prompt["system"], role=self.enums.SYSTEM.value))
            if prompt.get("user"):
                messages_for_api.append(self.construct_prompt(prompt=self.process_text(prompt["user"]), role=self.enums.USER.value))
        else:
            messages_for_api.append(self.construct_prompt(prompt=self.process_text(prompt), role=self.enums.USER.value))

        try:
            response = self.client.chat.completions.create(
                model=self.generation_model_id,
                messages=messages_for_api,
                max_tokens=max_output_tokens,
                temperature=temperature
            )
            if not response or not response.choices or not response.choices[0].message:
                self.logger.error("Error while generating text with OpenRouter")
                return None
            return response.choices[0].message.content
        except Exception as e:
            self.logger.error(f"Exception during OpenRouter API call: {e}")
            return None


    def embed_text(self, text: Union[str, List[str]], document_type: str = None):
        
        if not self.client or not self.embedding_model_id:
            self.logger.error("OpenRouter client or embedding model was not set")
            return None
        
        if isinstance(text, str):
            text = [text]
        
        # OpenRouter also supports OpenAI-compatible embeddings
        response = self.client.embeddings.create(
            model = self.embedding_model_id,
            input = text,
        )

        if not response or not response.data or not response.data[0].embedding:
            self.logger.error("Error while embedding text with OpenRouter")
            return None

        return [ rec.embedding for rec in response.data ]


    def construct_prompt(self, prompt: str, role: str):
        return {"role": role, "content": prompt}