import os
from typing import Optional, Union
from pydantic_ai import Agent
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.anthropic import AnthropicProvider
from pydantic_ai.providers.ollama import OllamaProvider
from app.config import settings
from app.models.schemas import DocumentExtraction

# Lazy-loaded agent to avoid errors at import time
_extraction_agent: Optional[Agent] = None


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
                "Extract container details, parties, and routing info. "
                "If a field is not found, leave it null."
            )
        )
    return _extraction_agent


async def extract_data_from_text(text: str) -> DocumentExtraction:
    """
    Extract structured data from document text using Pydantic AI.
    Uses the LLM provider configured in .env (ollama or anthropic).
    """
    # safety chop to avoid context window explosion
    truncated_text = text[:15000]

    agent = get_extraction_agent()
    result = await agent.run(
        f"Extract data from this document text:\n\n{truncated_text}"
    )
    return result.output
