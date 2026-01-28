import pymupdf4llm
import io
import re
import tempfile
import os
from typing import List, Dict, Any
from app.models.schemas import DocType


class PDFExtractionError(Exception):
    """Custom exception for PDF extraction errors."""
    pass


def clean_markdown(text: str) -> str:
    """
    Clean markdown output from pymupdf4llm.

    Removes:
    - Excessive blank lines (collapses 3+ newlines to 2)
    - HTML <br> tags (often appear in tables)
    - Leading/trailing whitespace per line
    """
    # Remove HTML br tags
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)

    # Collapse multiple consecutive newlines (3+) to 2
    text = re.sub(r'\n{3,}', '\n\n', text)

    # Clean up each line
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        # Strip trailing whitespace but preserve leading for markdown
        cleaned_lines.append(line.rstrip())

    text = '\n'.join(cleaned_lines)

    # Remove leading/trailing whitespace from the whole document
    return text.strip()


def extract_text_from_pdf(file_bytes: bytes) -> List[Dict[str, Any]]:
    """
    Extracts text from PDF bytes using pymupdf4llm for markdown output.
    Returns a list of pages with cleaned markdown text and metadata.

    pymupdf4llm provides better structure for LLM parsing:
    - Markdown headers for sections
    - Markdown tables for tabular data
    - Better text flow
    """
    pages_content = []

    # Basic PDF magic byte check
    if not file_bytes.startswith(b"%PDF-"):
        raise PDFExtractionError("Invalid PDF: Missing %PDF- header")

    # pymupdf4llm requires a file path, so use a temp file
    try:
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        try:
            # Get total page count first
            import pymupdf
            doc = pymupdf.open(tmp_path)
            num_pages = len(doc)
            doc.close()

            # Extract each page individually for per-page analysis
            for page_num in range(num_pages):
                markdown = pymupdf4llm.to_markdown(tmp_path, pages=[page_num])
                cleaned_text = clean_markdown(markdown)

                pages_content.append({
                    "page_num": page_num + 1,
                    "text": cleaned_text
                })

            return pages_content

        finally:
            # Clean up temp file
            os.unlink(tmp_path)

    except Exception as e:
        raise PDFExtractionError(f"Failed to process PDF: {str(e)}")


def extract_text_from_pdf_pages(file_bytes: bytes, page_range: List[int]) -> str:
    """
    Extract markdown text from specific pages of a PDF.

    Args:
        file_bytes: PDF file as bytes
        page_range: List of 1-indexed page numbers to extract

    Returns:
        Cleaned markdown text from the specified pages
    """
    # Basic PDF magic byte check
    if not file_bytes.startswith(b"%PDF-"):
        raise PDFExtractionError("Invalid PDF: Missing %PDF- header")

    try:
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        try:
            # Convert to 0-indexed for pymupdf4llm
            pages = [p - 1 for p in page_range]
            markdown = pymupdf4llm.to_markdown(tmp_path, pages=pages)
            return clean_markdown(markdown)

        finally:
            os.unlink(tmp_path)

    except Exception as e:
        raise PDFExtractionError(f"Failed to process PDF pages {page_range}: {str(e)}")


def classify_doc_type_from_text(text: str) -> DocType:
    """
    Desperate check if AI fails. Just grep for headers.
    Works with both raw text and markdown.
    """
    text_upper = text.upper()

    if "MASTER BILL OF LADING" in text_upper or " MBL " in text_upper:
        return DocType.MBL
    if "HOUSE BILL OF LADING" in text_upper or " HBL " in text_upper:
        return DocType.HBL

    # give up
    return DocType.UNKNOWN
