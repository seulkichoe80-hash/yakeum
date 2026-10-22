"""Safe TASK A extraction contract adapter.

This package does not call Gemini at import time.  The public functions exposed
here transform a provider JSON response into the shared ExtractionResult draft.
"""

from .adapter import (
    ExtractionContext,
    adapt_extracted_document,
    adapt_gemini_response,
    adapt_provider_call,
)
from .config import GeminiConfigurationError, GeminiSettings
from .parser import ExtractionPayloadError, parse_gemini_response

__all__ = [
    "ExtractionContext",
    "ExtractionPayloadError",
    "GeminiConfigurationError",
    "GeminiSettings",
    "adapt_extracted_document",
    "adapt_gemini_response",
    "adapt_provider_call",
    "parse_gemini_response",
]
