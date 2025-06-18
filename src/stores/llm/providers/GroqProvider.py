# Changes you asked for: This entire file is new for GroqProvider
from ..LLMInterface import LLMInterface
from ..LLMEnums import GroqEnums # Re-using OpenAIEnums structure as Groq API is similar
from groq import Groq
import logging

class GroqProvider(LLMInterface):

    def __init__(self, api_key: str,api_url: str=None,
                       default_input_max_characters: int = 8000, # Groq models often handle larger contexts
                       default_generation_max_output_tokens: int = 1024,
                       default_generation_temperature: float = 0.2):
        
        self.api_key = api_key
        self.api_url = api_url
        
        self.default_input_max_characters = default_input_max_characters
        self.default_generation_max_output_tokens = default_generation_max_output_tokens
        self.default_generation_temperature = default_generation_temperature

        self.generation_model_id = None

        # Groq does not provide embedding models via its primary API
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
        # Groq is not used for embeddings in this setup
        self.embedding_model_id = None
        self.embedding_size = None
        self.logger.warning("GroqProvider does not support embedding models. set_embedding_model call ignored.")

    def process_text(self, text: str):
        # Truncation logic, if needed, can be less aggressive for Groq
        return text[:self.default_input_max_characters].strip()

    def generate_text(self, prompt: str, chat_history: list = [], max_output_tokens: int = None,
                            temperature: float = None):
        
        if not self.client:
            self.logger.error("Groq client was not set.")
            return None

        if not self.generation_model_id:
            self.logger.error("Generation model for Groq was not set.")
            return None
        
        max_output_tokens = max_output_tokens if max_output_tokens else self.default_generation_max_output_tokens
        temperature = temperature if temperature else self.default_generation_temperature

        messages_for_api = []
        for item in chat_history: # Ensure history is in Groq format if it came from another provider
            messages_for_api.append({"role": item.get("role"), "content": item.get("content", item.get("text"))})
        
        messages_for_api.append(
            self.construct_prompt(prompt=prompt, role=self.enums.USER.value)
        )
        
        self.logger.debug(f"Sending to Groq API with model {self.generation_model_id}: {messages_for_api}")

        try:
            response = self.client.chat.completions.create(
                model=self.generation_model_id,
                messages=messages_for_api,
                max_tokens=max_output_tokens,
                temperature=temperature
            )

            if not response or not response.choices or len(response.choices) == 0 or not response.choices[0].message:
                self.logger.error("Error or empty response while generating text with Groq.")
                return None

            return response.choices[0].message.content
        except Exception as e:
            self.logger.error(f"Exception during Groq API call: {e}")
            return None


    def embed_text(self, text: str, document_type: str = None):
        self.logger.warning("GroqProvider does not provide embedding services. embed_text call returning None.")
        # Raise an error or return None based on how you want to handle this.
        # Since the architecture separates embedding and generation clients,
        # this method on the Groq *generation* client might not even be called
        # if the EMBEDDING_BACKEND is set to Cohere/OpenAI.
        raise NotImplementedError("GroqProvider does not support embeddings.")
        # return None 

    def construct_prompt(self, prompt: str, role: str):
        # Groq uses OpenAI's chat completion message format
        return {
            "role": role,
            "content": prompt,
        }