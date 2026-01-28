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


def _create_llm_model():
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


def _get_or_create_agent() -> Agent:
    """Get or create the extraction agent (lazy loading)."""
    global _extraction_agent
    if _extraction_agent is None:
        _extraction_agent = Agent(
            model=_create_llm_model(),
            output_type=DocumentExtraction,
            retries=3,
            output_retries=3,
            system_prompt=(
                "You are an expert logistics document analyzer. "
                "The document has been converted to Markdown format for better structure. "
                "Extract key information from the Bill of Lading.\n\n"

                "DOCUMENT TYPE:\n"
                "- Look for '**HOUSE BILL OF LADING**' or 'HBL' → doc_type = 'hbl'\n"
                "- Look for '**MASTER BILL OF LADING**' or 'MBL' → doc_type = 'mbl'\n\n"

                "PARTIES (look for bold headers like **SHIPPER**, **CONSIGNEE**):\n"
                "- Shipper: The party sending the goods (company name only)\n"
                "- Consignee: The party receiving the goods (company name only)\n"
                "- Notify Party: If it says 'Same as Consignee', return that exact text\n"
                "- Carrier: The shipping line name (e.g., CMA CGM, Hapag-Lloyd)\n\n"

                "ROUTING (look for **PORT OF LOADING**, **PORT OF DISCHARGE**):\n"
                "- Include the full port name with code, e.g., 'Hong Kong, HK (HKHKG)'\n"
                "- ETD/ETA dates if present\n\n"

                "CONTAINERS (look for Markdown tables with columns):\n"
                "- Container table has columns: CONTAINER NO., SEAL, TYPE, PKGS, GROSS, CBM\n"
                "- Extract 'number' from CONTAINER NO. column\n"
                "- Extract 'weight' from GROSS column (weight in kg, may have space as thousands separator like '15 777.6' = 15777.6)\n"
                "- Extract 'volume' from CBM column (cubic meters, e.g., '51.746')\n"
                "- IMPORTANT: Do NOT confuse TYPE (like '40HC') with volume!\n\n"

                "Return just numeric values for weight/volume (no units).\n"
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


async def extract_with_ai(text: str) -> DocumentExtraction:
    """
    Extract structured data from document text using AI only.
    """
    # safety chop to avoid context window explosion
    truncated_text = text[:15000]
    agent = _get_or_create_agent()

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


async def extract_shipment_data(markdown: str, use_ai_fallback: bool = True) -> DocumentExtraction:
    """
    Extract structured data from document markdown using hybrid regex + AI approach.

    Strategy:
    1. Try fast regex extraction first (< 1 second)
    2. Check if critical fields are missing
    3. If scanned PDF or many nulls, fallback to AI
    4. Otherwise, return regex results (fast + cheap)

    Args:
        markdown: Clean markdown text from PDF
        use_ai_fallback: If True, use AI for missing fields. If False, return regex only.

    Returns:
        DocumentExtraction with all extracted fields
    """
    from app.services.regex_extractor import extract_all, is_scanned_pdf, RegexExtractionResult
    from app.models.schemas import ContainerInfo, DocType

    # Step 1: Check if this is a scanned/image PDF
    if is_scanned_pdf(markdown):
        # No structure - must use AI
        if use_ai_fallback:
            return await extract_with_ai(markdown)
        else:
            # Return empty result
            return DocumentExtraction(doc_type=DocType.UNKNOWN)

    # Step 2: Try regex extraction (fast)
    regex_result = extract_all(markdown)

    # Step 3: Check for critical missing fields
    null_fields = regex_result.null_fields()

    # Critical fields that must be present
    critical_missing = any(f in null_fields for f in ['doc_type', 'bl_number'])

    # If critical fields missing and AI allowed, use AI
    if critical_missing and use_ai_fallback:
        return await extract_data_from_text(markdown)

    # If many fields missing (>3) and AI allowed, use AI
    if len(null_fields) > 3 and use_ai_fallback:
        return await extract_data_from_text(markdown)

    # Step 4: Convert regex result to DocumentExtraction schema
    containers = []
    for c in regex_result.containers:
        containers.append(ContainerInfo(
            number=c.get('number'),
            weight=c.get('weight'),
            volume=c.get('volume'),
        ))

    # Map doc_type string to enum
    doc_type = DocType.UNKNOWN
    if regex_result.doc_type == 'hbl':
        doc_type = DocType.HBL
    elif regex_result.doc_type == 'mbl':
        doc_type = DocType.MBL

    # Calculate confidence score
    # Base: 1.0 for Regex
    confidence = 1.0

    # Penalize for missing critical fields
    critical_fields = [
        regex_result.bl_number,
        regex_result.shipper_name,
        regex_result.consignee_name,
        regex_result.carrier_name,
        containers  # Must have at least one container
    ]
    missing_count = sum(1 for f in critical_fields if not f)
    penalty = (missing_count / len(critical_fields)) * 0.5
    confidence = max(0.5, confidence - penalty)

    return DocumentExtraction(
        doc_type=doc_type,
        bl_number=regex_result.bl_number,
        shipper_name=regex_result.shipper_name,
        consignee_name=regex_result.consignee_name,
        notify_party_name=regex_result.notify_party_name,
        carrier_name=regex_result.carrier_name,
        port_of_loading=regex_result.port_of_loading,
        port_of_discharge=regex_result.port_of_discharge,
        place_of_receipt=regex_result.place_of_receipt,
        place_of_delivery=regex_result.place_of_delivery,
        etd=regex_result.etd,
        eta=regex_result.eta,
        containers=containers,
        raw_text_excerpt=regex_result.raw_text_excerpt,
        extraction_confidence=round(confidence, 2),
    )
