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


def extract_document_metadata(text: str, default_well_id: str = "15/9-F-14") -> Dict[str, Any]:
    """
    Extracts core domain metadata deterministically from document text:
    - well_id
    - depth
    - water_depth
    - report_period
    - abnormal_remarks
    - current_operation
    """
    if not text:
        return {
            "well_id": default_well_id,
            "depth": "N/A",
            "water_depth": "N/A",
            "report_period": "N/A",
            "abnormal_remarks": "None",
            "current_operation": "N/A",
        }

    # 1. Well ID
    well_id_match = (
        re.search(r"(?i)well\s*(?:id|name)[^\n]*?([A-Za-z0-9\-\/]{5,})", text)
        or re.search(r"\b(15/9-[A-Z0-9\-\s]+)\b", text)
    )
    well_id = well_id_match.group(1).strip() if well_id_match else default_well_id

    # 2. Depth
    depth_match = (
        re.search(r"(?i)current\s*depth[^\d\n]*?([0-9]{2,}\.[0-9]+)", text)
        or re.search(r"(?i)(?:depth|measured depth|md)\s*[:=]?\s*(\d+(?:\.\d+)?\s*(?:m|ft|meters|feet))", text)
        or re.search(r"(\d{3,4}(?:\.\d+)?)\s*(?:m|meters|mMD|MD)", text)
    )
    depth = depth_match.group(1).strip() if depth_match else "N/A"

    # 3. Water Depth
    water_depth_match = re.search(r"(?i)water\s*depth[^\d\n]*?([0-9]{1,}\.[0-9]+)", text)
    water_depth = water_depth_match.group(1).strip() if water_depth_match else "N/A"

    # 4. Report Period
    report_period_match = (
        re.search(r"(?is)(?:reporting\s*period|report\s*period)[\s\:\-\|]*(From[\s\S]*?To[\s\S]*?\d{4})", text)
        or re.search(r"(?is)(From\s*:\s*0?6:00[\s\S]*?To\s*:\s*0?6:00[\s\S]*?\d{4})", text)
        or re.search(r"(?is)(From\s*:\s*\d{1,2}:\d{2}[\s\S]*?To\s*:\s*\d{1,2}:\d{2}[^\n\|]*)", text)
        or re.search(r"(?i)reporting\s*period[^\n\|]*[:\-\|]\s*([^\n\|]+)", text)
        or re.search(r"(?is)4\.\s*REPORTING\s*PERIOD[\s\:\-\|]*([^\n\#\|]+)", text)
    )
    report_period = re.sub(r"\s+", " ", report_period_match.group(1)).strip() if report_period_match else "N/A"

    # 5. Abnormal Remarks / Summary
    abnormal_remarks_match = (
        re.search(r"(?is)(?:19\.\s*DAILY\s*SUMMARY|DAILY\s*SUMMARY|abnormal\s*remarks|SUMMARY:)\s*[:\-]?\s*([^\n\#\|]+)", text)
        or re.search(r"(?i)(?:abnormal\s*remarks|remarks)\s*[:\-]?\s*(.*?)(?:\n|$)", text)
    )
    abnormal_remarks = re.sub(r"\s+", " ", abnormal_remarks_match.group(1)).strip() if abnormal_remarks_match else "None"

    # 6. Current Operation
    op_match = re.search(r"(?i)(?:current\s*operation|operation\s*/\s*activity|ops)\s*[:=]?\s*([^\n\r\|]{1,100})", text)
    current_operation = op_match.group(1).strip() if op_match else "N/A"

    return {
        "well_id": well_id,
        "depth": depth,
        "water_depth": water_depth,
        "report_period": report_period,
        "abnormal_remarks": abnormal_remarks,
        "current_operation": current_operation,
    }
