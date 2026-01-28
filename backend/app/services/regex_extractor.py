import re
from typing import Optional
from datetime import datetime, date
from dataclasses import dataclass


@dataclass
class RegexExtractionResult:
    doc_type: Optional[str] = None
    bl_number: Optional[str] = None
    shipper_name: Optional[str] = None
    consignee_name: Optional[str] = None
    notify_party_name: Optional[str] = None
    carrier_name: Optional[str] = None
    port_of_loading: Optional[str] = None
    port_of_discharge: Optional[str] = None
    place_of_receipt: Optional[str] = None
    place_of_delivery: Optional[str] = None
    etd: Optional[date] = None
    eta: Optional[date] = None
    containers: list = None
    raw_text_excerpt: Optional[str] = None

    def __post_init__(self):
        if self.containers is None:
            self.containers = []

    def null_fields(self) -> list[str]:
        nulls = []
        for field in ['doc_type', 'bl_number', 'shipper_name', 'consignee_name',
                      'carrier_name', 'port_of_loading', 'port_of_discharge']:
            if getattr(self, field) is None:
                nulls.append(field)
        if not self.containers:
            nulls.append('containers')
        return nulls


# =============================================================================
# Document Type Extraction
# =============================================================================

def extract_doc_type(markdown: str) -> Optional[str]:
    text_upper = markdown.upper()

    if 'HOUSE BILL OF LADING' in text_upper:
        return 'hbl'
    if 'MASTER BILL OF LADING' in text_upper:
        return 'mbl'
    if re.search(r'\bHBL-\d+', markdown):
        return 'hbl'
    if re.search(r'\bMBL-\d+', markdown):
        return 'mbl'

    return None


# =============================================================================
# BL Number Extraction
# =============================================================================

def extract_bl_number(markdown: str) -> Optional[str]:
    match = re.search(r'\b([HM]BL-\d+)\b', markdown)
    if match:
        return match.group(1)

    match = re.search(r'B/L\s*(?:NO\.?|NUMBER)[:\s]*\n*([A-Z0-9-]+)', markdown, re.IGNORECASE)
    if match:
        return match.group(1).strip()

    return None


# =============================================================================
# Party Extraction (Shipper, Consignee, Notify Party)
# =============================================================================

def extract_shipper(markdown: str) -> Optional[str]:
    pattern = r'\*\*SHIPPER\*\*\s*\n(?:Shipper:?\s*\n)?([^\n*]+)'
    match = re.search(pattern, markdown)
    if match:
        name = match.group(1).strip()
        # Skip if it's just "Shipper:" or empty
        if name and name.lower() != 'shipper:' and len(name) > 2:
            return name

    return None


def extract_consignee(markdown: str) -> Optional[str]:
    pattern = r'\*\*CONSIGNEE\*\*\s*\n(?:Consignee:?\s*\n)?([^\n*]+)'
    match = re.search(pattern, markdown)
    if match:
        name = match.group(1).strip()
        if name and name.lower() != 'consignee:' and len(name) > 2:
            return name

    return None


def extract_notify_party(markdown: str) -> Optional[str]:
    pattern = r'\*\*NOTIFY PARTY\*\*\s*\n(?:Notify Party:?\s*\n)?([^\n*]+)'
    match = re.search(pattern, markdown)
    if match:
        value = match.group(1).strip()
        if value and value.lower() != 'notify party:' and len(value) > 2:
            return value

    return None


# =============================================================================
# Carrier Extraction
# =============================================================================

def extract_carrier(markdown: str) -> Optional[str]:
    pattern = r'Carrier:\s*\|?\s*([A-Za-z][^\n|]+)'
    match = re.search(pattern, markdown)
    if match:
        carrier = match.group(1).strip()
        # Clean up trailing pipes or whitespace
        carrier = carrier.rstrip('| \t')
        if carrier:
            return carrier

    return None


# =============================================================================
# Port Extraction (POL, POD, Place of Receipt/Delivery)
# =============================================================================

def extract_port_of_loading(markdown: str) -> Optional[str]:
    pattern = r'\*\*PORT OF LOADING\*\*\s*\n([^\n*]+)'
    match = re.search(pattern, markdown)
    if match:
        port = match.group(1).strip()
        # Filter out ETD lines that might be captured
        if port and not port.upper().startswith('ETD'):
            return port

    return None


def extract_port_of_discharge(markdown: str) -> Optional[str]:
    pattern = r'\*\*PORT OF DISCHARGE\*\*\s*\n([^\n*]+)'
    match = re.search(pattern, markdown)
    if match:
        port = match.group(1).strip()
        # Filter out ETA lines
        if port and not port.upper().startswith('ETA'):
            return port

    return None


def extract_place_of_receipt(markdown: str) -> Optional[str]:
    pattern = r'\*\*PLACE OF RECEIPT\*\*\s*\n([^\n*]+)'
    match = re.search(pattern, markdown)
    if match:
        return match.group(1).strip()
    return None


def extract_place_of_delivery(markdown: str) -> Optional[str]:
    pattern = r'\*\*PLACE OF DELIVERY\*\*\s*\n([^\n*]+)'
    match = re.search(pattern, markdown)
    if match:
        return match.group(1).strip()
    return None


# =============================================================================
# Date Extraction (ETD, ETA)
# =============================================================================

def parse_date(date_str: str) -> Optional[date]:
    formats = [
        '%d-%b-%Y',    # 02-Jan-2026
        '%Y-%m-%d',    # 2026-01-02
        '%d/%m/%Y',    # 02/01/2026
        '%m/%d/%Y',    # 01/02/2026
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt).date()
        except ValueError:
            continue

    return None


def extract_etd(markdown: str) -> Optional[date]:
    pattern = r'ETD:\s*([^\n]+)'
    match = re.search(pattern, markdown)
    if match:
        return parse_date(match.group(1))
    return None


def extract_eta(markdown: str) -> Optional[date]:
    pattern = r'ETA:\s*([^\n]+)'
    match = re.search(pattern, markdown)
    if match:
        return parse_date(match.group(1))
    return None


# =============================================================================
# Container Extraction (from markdown tables)
# =============================================================================

def parse_weight(value: str) -> Optional[float]:
    if not value:
        return None

    cleaned = value.replace(' ', '').replace(',', '')

    try:
        return float(cleaned)
    except ValueError:
        return None


def extract_containers(markdown: str) -> list[dict]:
    containers = []

    container_pattern = r'\b([A-Z]{4}\d{7})\b'

    container_numbers = re.findall(container_pattern, markdown)

    if not container_numbers:
        return containers

    # Strategy: For each container, find the weight that follows it
    # in the CONTAINER table context. The table cells are split by | and newlines.

    # Find the section containing container table
    # Look for pattern: container_number followed by other cells ending with weight|

    weights = []

    for container_num in container_numbers:
        # Find this container and extract values until we hit a non-table line
        # Pattern: container_num| followed by cells, last numeric cell before empty line is weight

        # Find where this container appears
        pos = markdown.find(container_num)
        if pos == -1:
            weights.append(None)
            continue

        after_container = markdown[pos:pos+200]

        weight_pattern = r'(\d[\d\s,]*\.\d+)\|'
        weight_matches = re.findall(weight_pattern, after_container)

        weight = None
        for val in weight_matches:
            parsed = parse_weight(val)
            if parsed and parsed > 50:  # Min weight threshold
                weight = parsed
                break

        weights.append(weight)

    # Extract volume from MARKS & NUMBERS table
    # This table has total weight and volume for all containers
    # Format: |...|GROSS (KGS)|CBM|
    # Values: |...|15 777.6|51.746|

    total_volume = None

    # Look for the last two numeric pipe-separated values before |CONTAINER
    # We restrict search to the text BEFORE the container table to avoid matching container rows
    container_header_pos = markdown.find('|CONTAINER NO.')
    search_text = markdown[:container_header_pos] if container_header_pos != -1 else markdown

    # Pattern: total_weight|total_volume| followed by optional newlines/spaces
    # We remove the strict lookahead for |CONTAINER logic because there might be loose text in between.
    # Instead, we just find ALL structure matches and take the LAST one.
    marks_end_pattern = r'\|[\s\n]*(\d[\d\s,.]+)\s*\|[\s\n]*(\d+\.?\d*)\s*\|'
    matches = re.findall(marks_end_pattern, search_text, re.IGNORECASE)

    if matches:
        # Take the last match (closest to the container table)
        last_match = matches[-1]
        # Second group is total volume
        total_volume = parse_weight(last_match[1])

    # If single container, also check if there's a CBM value directly
    if len(container_numbers) == 1 and container_numbers[0] in markdown:
        # For single container docs, volume might be right after weight
        pos = markdown.find(container_numbers[0])
        after = markdown[pos:pos+300]

        # Look for two consecutive large and small numbers: weight | volume
        wv_pattern = r'\|[\s\n]*(\d[\d\s,.]+)\s*\|[\s\n]*(\d+\.?\d*)\s*\|'
        wv_match = re.search(wv_pattern, after)
        if wv_match:
            v = parse_weight(wv_match.group(2))
            if v and v < 200:  # Sanity check for volume
                total_volume = v

    # Calculate per-container volume
    # Default: distribute total volume
    volumes = []
    if total_volume and len(container_numbers) > 0:
        per_container_volume = total_volume / len(container_numbers)
        volumes = [per_container_volume] * len(container_numbers)
    else:
        volumes = [None] * len(container_numbers)

    # REFINEMENT: Check for orphaned/floating volumes between MARKS and CONTAINER tables
    # Some PDFs list individual container volumes as loose text between the tables
    marks_header_pos = markdown.find('|MARKS & NUMBERS')
    if marks_header_pos != -1 and container_header_pos != -1:
        gap_text = markdown[marks_header_pos:container_header_pos]
        # Find all floats in this gap
        floats = re.findall(r'\b(\d+\.\d{3})\b', gap_text)
        orphaned_volumes = [float(f) for f in floats]

        # Filter out the total_volume if picked up
        if total_volume:
            orphaned_volumes = [v for v in orphaned_volumes if abs(v - total_volume) > 0.001]

        # Strategy: If found volumes match the count of containers (or count-1), assign them
        # Logic: Match from the END (last found float -> last container)
        if len(orphaned_volumes) > 0:
            count_to_assign = min(len(orphaned_volumes), len(volumes))
            for i in range(1, count_to_assign + 1):
                # Assign to the last i-th container
                # e.g. last orphaned -> last container
                volumes[-i] = orphaned_volumes[-i]

    # Build container list
    for i, number in enumerate(container_numbers):
        container = {
            'number': number,
            'weight': weights[i] if i < len(weights) else None,
            'volume': volumes[i] if i < len(volumes) else None,
        }
        containers.append(container)

    return containers


# =============================================================================
# Full Extraction Orchestrator
# =============================================================================

def extract_all(markdown: str) -> RegexExtractionResult:
    return RegexExtractionResult(
        doc_type=extract_doc_type(markdown),
        bl_number=extract_bl_number(markdown),
        shipper_name=extract_shipper(markdown),
        consignee_name=extract_consignee(markdown),
        notify_party_name=extract_notify_party(markdown),
        carrier_name=extract_carrier(markdown),
        port_of_loading=extract_port_of_loading(markdown),
        port_of_discharge=extract_port_of_discharge(markdown),
        place_of_receipt=extract_place_of_receipt(markdown),
        place_of_delivery=extract_place_of_delivery(markdown),
        etd=extract_etd(markdown),
        eta=extract_eta(markdown),
        containers=extract_containers(markdown),
        raw_text_excerpt=extract_raw_text_excerpt(markdown),
    )


def is_scanned_pdf(markdown: str) -> bool:
    # Check for minimum content
    if len(markdown.strip()) < 100:
        return True

    # Check for markdown structure
    has_headers = '**' in markdown
    has_tables = '|' in markdown and '---' in markdown

    if not has_headers and not has_tables:
        return True

    return False


def extract_raw_text_excerpt(markdown: str) -> Optional[str]:
    # Priority 1: Specific Terms & Conditions header
    # Matches: **TERMS & CONDITIONS**, **TERMS AND CONDITIONS**, **TERMS & CONDITIONS (EXCERPT)**
    # Capture content until next bold header or end of string
    terms_pattern = r'\*\*TERMS\s*(?:&|AND)\s*CONDITIONS[^\n*]*\*\*\n(.*?)(?:\n\*\*|$)'
    match = re.search(terms_pattern, markdown, re.IGNORECASE | re.DOTALL)

    if match:
        excerpt = match.group(1).strip()
        excerpt = re.sub(r'\n+', ' ', excerpt)
        if len(excerpt) > 200:
            excerpt = excerpt[:197] + "..."
        if len(excerpt) > 10:
            return excerpt

    # Priority 2: Other legal headers if Terms not found (e.g. RECEIVED BY, LIABILITY)
    # But explicitly avoid "SIGNED FOR", "ISSUED BY", "SHIPPER", "CONSIGNEE", "NOTIFY"
    other_headers_pattern = r'\*\*(?:RECEIVED BY|LIABILITY|CARRIER RESPONSIBILITY)[^\n*]*\*\*\n(.*?)(?:\n\*\*|$)'
    match = re.search(other_headers_pattern, markdown, re.IGNORECASE | re.DOTALL)

    if match:
        excerpt = match.group(1).strip()
        excerpt = re.sub(r'\n+', ' ', excerpt)
        if len(excerpt) > 200:
            excerpt = excerpt[:197] + "..."
        if len(excerpt) > 10:
            return excerpt

    # Fallback: Just get the first non-header paragraph
    # (Existing fallback logic)
    paragraphs = markdown.split('\n\n')
    for p in paragraphs:
        if len(p) > 50 and not p.startswith('|') and not p.startswith('#') and not p.strip().startswith('**'):
            excerpt = re.sub(r'\n+', ' ', p.strip())
            if len(excerpt) > 200:
                excerpt = excerpt[:197] + "..."
            return excerpt

    return None
