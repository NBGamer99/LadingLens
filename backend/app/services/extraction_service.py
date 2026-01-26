from typing import Optional
import instructor
from openai import OpenAI
from anthropic import Anthropic
from app.config import settings
from app.models.schemas import DocumentExtraction

def get_extraction_client():
    if settings.LLM_PROVIDER == "anthropic":
        return instructor.from_anthropic(Anthropic(api_key=settings.ANTHROPIC_API_KEY))
    else:
        # Ollama for local dev
        return instructor.from_openai(
            OpenAI(
                base_url=settings.OLLAMA_BASE_URL,
                api_key="ollama",  # dummy key, ollama doesn't care
            ),
            mode=instructor.Mode.JSON,
        )

def extract_data_from_text(text: str) -> DocumentExtraction:
    client = get_extraction_client()

    # safety chop to avoid context window explosion
    # llama 3 has 8k, should be plenty for a single doc
    truncated_text = text[:15000]

    resp = client.chat.completions.create(
        model=settings.OLLAMA_MODEL if settings.LLM_PROVIDER == "ollama" else "claude-3-haiku-20240307",
        response_model=DocumentExtraction,
        messages=[
            {
                "role": "system",
                "content": "You are an expert logistics document analyzer. Extract key information from the Bill of Lading text provided. Determine if it is a Master Bill of Lading (MBL) or House Bill of Lading (HBL). Extract container details, parties, and routing info. If a field is not found, leave it null.",
            },
            {
                "role": "user",
                "content": f"Extract data from this document text:\n\n{truncated_text}",
            },
        ],
    )
    return resp
