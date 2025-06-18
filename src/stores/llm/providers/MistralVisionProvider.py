# MistralVisionProvider.py

import httpx
import base64
import logging
from typing import List, Union, Optional # Optional is good practice
from mistralai import Mistral

# Assuming LLMInterface and MistralEnums are in a parent directory '..'
# Adjust the import path based on your actual project structure.
# If openAIProvider.py uses 'from ..LLMInterface', this should too.
from ..LLMInterface import LLMInterface
from ..LLMEnums import MistralEnums # You'll need to create/update this
# from ..LLMEnums import DocumentTypeEnum # Keep if used for embed_text's signature, otherwise remove

class MistralVisionProvider(LLMInterface):

    def __init__(self, api_key: str, api_url: str = None, # Base URL for Mistral
                       default_input_max_characters: int = 4096, # Sensible default
                       default_generation_max_output_tokens: int = 4096,
                       default_generation_temperature: float = 0.7): # Mistral default is often 0.7

        self.api_key = api_key
        self.api_url = api_url

        self.default_input_max_characters = default_input_max_characters
        self.default_generation_max_output_tokens = default_generation_max_output_tokens
        self.default_generation_temperature = default_generation_temperature

        self.generation_model_id = None # To be set by set_generation_model

        self.embedding_model_id = None
        self.embedding_size = None

        self.client = Mistral(api_key=self.api_key)
        
        self.chat_completions_endpoint = "/v1/chat/completions" # Specific endpoint path

        self.enums = MistralEnums
        self.logger = logging.getLogger(__name__)

    def set_generation_model(self, model_id: str):
        
        self.generation_model_id = model_id

    def set_embedding_model(self, model_id: str, embedding_size: int):
        # Mistral's current vision models (like mistral-large-latest with vision)
        # don't offer separate text embedding endpoints in the same way as OpenAI.
        # This method is for interface consistency.
        self.embedding_model_id = model_id
        self.embedding_size = embedding_size
        self.logger.info(
            f"Embedding model set to {model_id} for MistralVisionProvider. "
            "Note: Vision models typically don't provide standalone text embeddings through this class."
        )

    def process_text(self, text: str):
        return text[:self.default_input_max_characters].strip()

    def construct_prompt(self, prompt: str, role: str):
        return {
            "role": role,
            "content": prompt,
        }

    def generate_text(self, prompt: str, chat_history: list = [], 
                            max_output_tokens: int = None,
                            temperature: float = None):

        if not self.client:
            self.logger.error("Mistral client was not set.")
            return None

        if not self.generation_model_id:
            self.logger.error("Generation model for Mistral was not set.")
            return None

        # Use provided or default values
        max_tokens = max_output_tokens if max_output_tokens is not None else self.default_generation_max_output_tokens
        temp = temperature if temperature is not None else self.default_generation_temperature

        processed_prompt = self.process_text(prompt)
        
        
        current_messages = list(chat_history) # Work with a copy if you don't want to modify original list
        current_messages.append(
            self.construct_prompt(prompt=processed_prompt, role=self.enums.USER)
        )

        payload = {
            "model": self.generation_model_id,
            "messages": current_messages,
            "temperature": temp,
            "max_tokens": max_tokens, # Mistral API uses 'max_tokens'
        }

        try:
            response = self.client.chat.complete(self.chat_completions_endpoint, json=payload)
            response.raise_for_status()  # Raises HTTPStatusError for 4xx/5xx responses
            
            data = response.choices[0]
            if not data or "choices" not in data or not data["choices"] or \
               "message" not in data["choices"][0] or "content" not in data["choices"][0]["message"]:
                self.logger.error(f"Error or unexpected response structure from Mistral API: {data}")
                return None
            return data["choices"][0]["message"]["content"]

        except httpx.HTTPStatusError as e:
            self.logger.error(f"HTTP error occurred: {e.response.status_code} - {e.response.text}")
            return None
        except httpx.RequestError as e:
            self.logger.error(f"Request error occurred: {e}")
            return None
        except Exception as e:
            self.logger.error(f"An unexpected error occurred in generate_text: {e}", exc_info=True)
            return None

    def caption_image(self, image_bytes: bytes, prompt: str = "Explain this image",
                            max_output_tokens: int = None, temperature: float = None):
        
        if not self.client:
            self.logger.error("Mistral client was not set.")
            return None

        if not self.generation_model_id:
            self.logger.error("Vision model for Mistral was not set (use set_generation_model).")
            return None

        max_tokens = max_output_tokens if max_output_tokens is not None else self.default_generation_max_output_tokens
        temp = temperature if temperature is not None else self.default_generation_temperature

        processed_text_prompt = self.process_text(prompt)
        image_data_base64 = base64.b64encode(image_bytes).decode("utf-8")

        messages = [
            {
                "role": self.enums.USER,
                "content": [
                    {"type": "text", "text": processed_text_prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_data_base64}"}}
                ]
            }
        ]

        try:
            response = self.client.chat.complete(
                model=self.generation_model_id,
                messages=messages,
                temperature=temp,
                max_tokens=max_tokens
            )

            return response.choices[0].message.content

        except Exception as e:
            self.logger.error(f"An unexpected error occurred in caption_image: {e}", exc_info=True)
            return None


    def embed_text(self, text: Union[str, List[str]], document_type: Optional[str] = None):
        # Following OpenAIProvider's signature for document_type
        if not self.client:
            self.logger.error("Mistral client was not set (though not used for this method).")
            # No return here, let it fall through to NotImplementedError or specific checks if they existed

        # if not self.embedding_model_id: # If Mistral ever offers embeddings via a vision model path
        #     self.logger.error("Embedding model for Mistral was not set.")
        #     return None
        
        self.logger.warning(
            "MistralVisionProvider.embed_text is not implemented. "
            "Vision models typically do not provide standalone text embedding generation through this API pattern. "
            "Use a dedicated Mistral embedding model/provider if needed."
        )
        raise NotImplementedError("Vision models are not typically used for generating text embeddings via this method.")