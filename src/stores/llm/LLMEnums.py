from enum import Enum

class LLMEnums(Enum):
    OPENAI = "OPENAI"
    COHERE = "COHERE"
    GROQ = "GROQ"
    MISTRAL = "MISTRAL_VISION"
    OPENROUTER = "OPENROUTER" 
    GOOGLE = "GOOGLE"

class OpenAIEnums(Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"

class CoHereEnums(Enum):
    SYSTEM = "SYSTEM"
    USER = "USER"
    ASSISTANT = "CHATBOT"

    DOCUMENT = "search_document"
    QUERY = "search_query"

class GroqEnums(Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"

class OpenRouterEnums(Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"

class GoogleEnums(Enum): # ADD THIS CLASS
    USER = "user"
    ASSISTANT = "model" # Google uses 'model' for the assistant's role
    
    # For embedding task types
    RETRIEVAL_QUERY = "RETRIEVAL_QUERY"
    RETRIEVAL_DOCUMENT = "RETRIEVAL_DOCUMENT"


class MistralEnums:
    USER = "user"
    ASSISTANT = "assistant"


class DocumentTypeEnum(Enum):
    DOCUMENT = "document"
    QUERY = "query"
