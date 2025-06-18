from dataclasses import dataclass
from typing import Dict

@dataclass
class Document:
    """A dataclass to represent a piece of content being processed,
    standardizing the data passed between services."""
    page_content: str
    metadata: Dict