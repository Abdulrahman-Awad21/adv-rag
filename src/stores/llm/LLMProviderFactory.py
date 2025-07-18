
from .LLMEnums import LLMEnums
from .providers import OpenAIProvider, CoHereProvider ,GroqProvider,MistralVisionProvider, OpenRouterProvider, GoogleProvider

class LLMProviderFactory:
    def __init__(self, config: dict):
        self.config = config

    def create(self, provider: str):
        if provider == LLMEnums.OPENAI.value:
            return OpenAIProvider(
                api_key = self.config.OPENAI_API_KEY,
                api_url = self.config.OPENAI_API_URL,
                default_input_max_characters=self.config.INPUT_DAFAULT_MAX_CHARACTERS,
                default_generation_max_output_tokens=self.config.GENERATION_DAFAULT_MAX_TOKENS,
                default_generation_temperature=self.config.GENERATION_DAFAULT_TEMPERATURE
            )
        if provider == LLMEnums.OPENROUTER.value: # ADD THIS BLOCK
            return OpenRouterProvider(
                api_key=self.config.OPENROUTER_API_KEY,
                app_name=self.config.APP_NAME,
                app_version=self.config.APP_VERSION,
                default_input_max_characters=self.config.INPUT_DAFAULT_MAX_CHARACTERS,
                default_generation_max_output_tokens=self.config.GENERATION_DAFAULT_MAX_TOKENS,
                default_generation_temperature=self.config.GENERATION_DAFAULT_TEMPERATURE,
        )

        if provider == LLMEnums.COHERE.value:
            return CoHereProvider(
                api_key = self.config.COHERE_API_KEY,
                default_input_max_characters=self.config.INPUT_DAFAULT_MAX_CHARACTERS,
                default_generation_max_output_tokens=self.config.GENERATION_DAFAULT_MAX_TOKENS,
                default_generation_temperature=self.config.GENERATION_DAFAULT_TEMPERATURE
            )
        
        if provider == LLMEnums.GOOGLE.value: # ADD THIS BLOCK
            return GoogleProvider(
                api_key=self.config.GOOGLE_API_KEY,
                default_input_max_characters=self.config.INPUT_DAFAULT_MAX_CHARACTERS,
                default_generation_max_output_tokens=self.config.GENERATION_DAFAULT_MAX_TOKENS,
                default_generation_temperature=self.config.GENERATION_DAFAULT_TEMPERATURE,
            )

        if provider == LLMEnums.GROQ.value:
            return GroqProvider(
                api_key = self.config.GROQ_API_KEY,
                default_input_max_characters=self.config.INPUT_DAFAULT_MAX_CHARACTERS,
                default_generation_max_output_tokens=self.config.GENERATION_DAFAULT_MAX_TOKENS,
                default_generation_temperature=self.config.GENERATION_DAFAULT_TEMPERATURE
            )
        
        if provider == LLMEnums.MISTRAL.value:  # ADDED: Support for Mistral Vision
            return MistralVisionProvider(
            api_key = self.config.MISTRAL_API_KEY,
            default_input_max_characters=self.config.INPUT_DAFAULT_MAX_CHARACTERS,
            default_generation_max_output_tokens=self.config.GENERATION_DAFAULT_MAX_TOKENS,
            default_generation_temperature=self.config.GENERATION_DAFAULT_TEMPERATURE
            )
        

        return None
