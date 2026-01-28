import os
import asyncio
from typing import Optional
from pydantic_ai import Agent
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.anthropic import AnthropicProvider
from pydantic_ai.providers.ollama import OllamaProvider
from app.config import settings
from app.models.schemas import DocumentExtraction

# Lazy-loaded agent to avoid errors at import time
_extraction_agent: Optional[Agent] = None

# Retry configuration for transient API errors
MAX_RETRIES = 3
RETRY_DELAY_BASE = 2  # seconds


def get_model():
    """
    Get the model for pydantic-ai.
    Supports both Ollama (local) and Anthropic (cloud) providers.
    Set LLM_PROVIDER in .env to switch between them.
    """
    if settings.LLM_PROVIDER == "anthropic":
        # Use AnthropicModel with AnthropicProvider for explicit API key
        provider = AnthropicProvider(api_key=settings.ANTHROPIC_API_KEY)
        return AnthropicModel("claude-sonnet-4-5", provider=provider)
    else:
        # Ollama - use OllamaProvider with /v1 endpoint as per pydantic-ai docs
        base_url = settings.OLLAMA_BASE_URL
        if not base_url.endswith("/v1"):
            base_url = base_url.rstrip("/") + "/v1"
        provider = OllamaProvider(base_url=base_url)
        return OpenAIChatModel(model_name=settings.OLLAMA_MODEL, provider=provider)


def get_extraction_agent() -> Agent:
    """Get or create the extraction agent (lazy loading)."""
    global _extraction_agent
    if _extraction_agent is None:
        _extraction_agent = Agent(
            model=get_model(),
            output_type=DocumentExtraction,
            retries=3,
            output_retries=3,
            system_prompt=(
                "You are an expert logistics document analyzer. "
                "Extract key information from the Bill of Lading text provided. "
                "Determine if it is a Master Bill of Lading (MBL) or House Bill of Lading (HBL). "
                "Focus on accurately ensuring the Shipper and Consignee names and addresses are extracted. "
                "- Shipper: The party sending the goods. Often at the top left.\n"
                "- Consignee: The party receiving the goods.\n"
                "- Notify Party: Often 'Same as Consignee' or a specific address.\n"
                "- Carrier: The name of the shipping line (e.g., MSC, MAERSK, CMA CGM). Ignore codes unless part of the name.\n"
                "Extract container details, parties, and routing info. "
                "For container volume and weight, provide just the numeric values if possible (e.g., '51.746' instead of '51.746 CBM'). "
                "If a field is not found, leave it null."
            )
        )
    return _extraction_agent

def _is_transient_error(error: Exception) -> bool:
    """Check if an error is transient and worth retrying."""
    error_str = str(error).lower()
    # Check for common transient error patterns
    transient_patterns = [
        "status_code: 500",
        "status_code: 502",
        "status_code: 503",
        "status_code: 504",
        "internal server error",
        "service unavailable",
        "bad gateway",
        "gateway timeout",
        "overloaded",
        "rate limit",
    ]
    return any(pattern in error_str for pattern in transient_patterns)


async def extract_data_from_text(text: str) -> DocumentExtraction:
    """
    Extract structured data from document text using AI.
    """
    # safety chop to avoid context window explosion
    truncated_text = text[:15000]
    agent = get_extraction_agent()

    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            result = await agent.run(
                f"Extract data from this document text:\n\nDOCUMENT TEXT:\n{truncated_text}"
            )
            ai_data = result.output
            return ai_data

        except Exception as e:
            last_error = e
            if _is_transient_error(e) and attempt < MAX_RETRIES - 1:
                delay = RETRY_DELAY_BASE * (2 ** attempt)  # Exponential backoff: 2, 4, 8 seconds
                print(f"        ⚠️  Transient API error (attempt {attempt + 1}/{MAX_RETRIES}), retrying in {delay}s...")
                await asyncio.sleep(delay)
            else:
                raise
    raise last_error
