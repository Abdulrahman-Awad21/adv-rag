from ..LLMInterface import LLMInterface
from ..LLMEnums import GroqEnums
from groq import Groq
import logging
from typing import Union

class GroqProvider(LLMInterface):

    def __init__(self, api_key: str,api_url: str=None,
                       default_input_max_characters: int = 8000,
                       default_generation_max_output_tokens: int = 1024,
                       default_generation_temperature: float = 0.2):
        
        self.api_key = api_key
        self.api_url = api_url
        self.default_input_max_characters = default_input_max_characters
        self.default_generation_max_output_tokens = default_generation_max_output_tokens
        self.default_generation_temperature = default_generation_temperature
        self.generation_model_id = None
        self.embedding_model_id = None
        self.embedding_size = None

        if not self.api_key:
            raise ValueError("Groq API key not provided.")
            
        self.client = Groq(api_key=self.api_key)
        self.enums = GroqEnums
        self.logger = logging.getLogger(__name__)
        self.logger.info("GroqProvider initialized.")

    def set_generation_model(self, model_id: str):
        self.generation_model_id = model_id
        self.logger.info(f"Groq generation model set to: {model_id}")

    def set_embedding_model(self, model_id: str, embedding_size: int):
        self.embedding_model_id = None
        self.embedding_size = None
        self.logger.warning("GroqProvider does not support embedding models. set_embedding_model call ignored.")

    def process_text(self, text: str):
        return text[:self.default_input_max_characters].strip()

    def generate_text(self, prompt: Union[str, dict], chat_history: list = [], max_output_tokens: int = None,
                            temperature: float = None):
        
        if not self.client or not self.generation_model_id:
            self.logger.error("Groq client or generation model was not set.")
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
                self.logger.error("Error or empty response while generating text with Groq.")
                return None
            return response.choices[0].message.content
        except Exception as e:
            self.logger.error(f"Exception during Groq API call: {e}")
            return None

    def embed_text(self, text: str, document_type: str = None):
        self.logger.warning("GroqProvider does not provide embedding services. embed_text call returning None.")
        raise NotImplementedError("GroqProvider does not support embeddings.")

    def construct_prompt(self, prompt: str, role: str):
        return {"role": role, "content": prompt}