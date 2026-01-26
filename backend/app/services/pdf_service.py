import pdfplumber
import io
from typing import List, Dict, Any
from app.models.schemas import DocType

def extract_text_from_pdf(file_bytes: bytes) -> List[Dict[str, Any]]:
    """
    Extracts text from PDF bytes.
    Returns a list of pages with text and metadata.
    """
    pages_content = []

    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            pages_content.append({
                "page_num": i + 1,
                "text": text
            })

    return pages_content

def classify_doc_type_from_text(text: str) -> DocType:
    """
    Desperate check if AI fails. Just grep for headers.
    """
    text_upper = text.upper()

    if "MASTER BILL OF LADING" in text_upper or " MBL " in text_upper:
        return DocType.MBL
    if "HOUSE BILL OF LADING" in text_upper or " HBL " in text_upper:
        return DocType.HBL

    # give up
    return DocType.UNKNOWN
