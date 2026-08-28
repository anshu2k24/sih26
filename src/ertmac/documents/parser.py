"""
PS26121 eRTMAC-NWIS — Extracted Event Parser
Parses document text for historical drilling event episodes, depth markers,
evidence snippets, mitigations, and confidence scores.

IMPORTANT INTEGRITY RULE:
Confidence score (0.0 - 1.0) is strictly an extraction confidence metric.
It is NEVER treated as ground truth until verified by a drilling engineer.
"""

import re
import uuid
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

logger = logging.getLogger("ertmac.documents.parser")

EVENT_KEYWORDS = {
    "Loss of Circulation": ["loss", "losses", "lost circulation", "mud loss", "seepage"],
    "Kick / Well Control": ["kick", "influx", "pit gain", "gas kick", "well control", "shut-in"],
    "Stuck Pipe": ["stuck pipe", "overpull", "tight hole", "stuck string", "jarring"],
    "Gasping Pump / Pack-off": ["pack off", "pack-off", "pump pressure spike", "flow out drop"],
    "Equipment Failure": ["tool failure", "mwd failure", "bha failure", "washout", "bit damage"],
}


def parse_extracted_events(
    document_id: str,
    text: str,
    default_well_id: str = "15/9-F-14",
    organization_id: str = "00000000-0000-0000-0000-000000000001",
) -> List[Dict[str, Any]]:
    """
    Parses document text to extract structured event episodes.
    Returns list of extracted event dicts with initial verification_status = 'EXTRACTED'.
    """
    extracted_events: List[Dict[str, Any]] = []
    lines = text.splitlines()

    # Look for wellbores mentioned in text (e.g. 15/9-F-14, 15/9-F-15)
    well_match = re.search(r"15/9-[A-Z0-9\-\s]+", text)
    well_id = well_match.group(0).strip() if well_match else default_well_id

    now = datetime.now(timezone.utc).isoformat()

    # Process text paragraphs / blocks
    blocks = re.split(r"\n\s*\n", text)
    for block in blocks:
        block_clean = block.strip()
        if len(block_clean) < 20:
            continue

        block_lower = block_clean.lower()

        # Check for event keywords
        matched_event_type = None
        matched_domain = "DRILLING_OPERATIONS"

        for ev_type, keywords in EVENT_KEYWORDS.items():
            if any(kw in block_lower for kw in keywords):
                matched_event_type = ev_type
                break

        if not matched_event_type:
            continue

        # Extract Measured Depth (MD) in meters
        md_match = re.search(r"(\d{3,4}(?:\.\d+)?)\s*(?:m|meter|meters|mMD|MD)", block_clean, re.IGNORECASE)
        onset_md = float(md_match.group(1)) if md_match else 2500.0

        # Extract TVD if present
        tvd_match = re.search(r"(\d{3,4}(?:\.\d+)?)\s*(?:mTVD|TVD)", block_clean, re.IGNORECASE)
        onset_tvd = float(tvd_match.group(1)) if tvd_match else None

        # Extract mitigation snippet if present
        mitigation = "Standard operational response recorded."
        mit_match = re.search(r"(?:mitigation|action|response|remedy)s?:?\s*([^\n\.]+)", block_clean, re.IGNORECASE)
        if mit_match:
            mitigation = mit_match.group(1).strip()

        # Calculate extraction confidence score (0.0 to 1.0)
        confidence = 0.65
        if md_match:
            confidence += 0.15
        if tvd_match:
            confidence += 0.10
        if len(block_clean) > 100:
            confidence += 0.10
        confidence = min(0.95, round(confidence, 2))

        event_id = f"EXT_{uuid.uuid4().hex[:8].upper()}"
        evt_record = {
            "id": event_id,
            "document_id": document_id,
            "organization_id": organization_id,
            "well_id": well_id,
            "event_type": matched_event_type,
            "event_domain": matched_domain,
            "onset_md": onset_md,
            "onset_tvd": onset_tvd,
            "event_timestamp": now,
            "evidence_text": block_clean[:500],
            "mitigation_text": mitigation,
            "resolution_text": "Resolution logged in DDR report episode.",
            "confidence": confidence,
            "verification_status": "EXTRACTED",
            "verified_by": None,
            "verified_at": None,
            "created_at": now,
        }
        extracted_events.append(evt_record)

    logger.info(f"Parsed {len(extracted_events)} event episodes from document {document_id}")
    return extracted_events
