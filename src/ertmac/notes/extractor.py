"""
PS121 Handwritten Notes OCR — Structured Information Extractor
Extracts domain entities and operational fields from transcribed notes:
- Dates & Times
- Measurements with physical engineering units (bar, °C, m, kNm, RPM, mm/s, L/min, SG)
- Identifiers (Equipment ID, Asset ID, Wellbore ID, Serial Numbers)
- People & Roles
- Tasks & Action items
- Operational Observations
"""

import re
from typing import Dict, Any, List, Optional


class StructuredExtractor:
    """
    Parses unstructured handwritten note text into structured operational entities.
    """

    # Patterns for Dates & Times
    DATE_PATTERNS = [
        r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
        r"\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b",
        r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2}(?:st|nd|rd|th)?,? \d{4}\b",
        r"\b\d{1,2} (?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{4}\b",
    ]
    TIME_PATTERNS = [
        r"\b\d{1,2}:\d{2}(?::\d{2})?\s*(?:HRS|hrs|AM|PM|am|pm)?\b",
        r"\b\d{4}\s*HRS\b",
    ]

    # Engineering measurements with units
    MEASUREMENT_PATTERN = re.compile(
        r"(?i)\b([\w\s\-]+?)\s*[:=]?\s*([0-9]+(?:\.[0-9]+)?)\s*("
        r"bar|psi|kpa|mpa|°c|°f|deg c|deg f|m|meters|ft|feet|mm/s|in/s|kkgf|klbf|kn\.m|knm|ft\.lb|rpm|l/min|gpm|sg|g/cm3|ppg|%|units|hz"
        r")\b"
    )

    # Equipment / Asset / Well IDs
    IDENTIFIER_PATTERN = re.compile(
        r"(?i)\b(asset\s*(?:id)?|equipment\s*(?:id)?|serial\s*(?:no|number)?|wellbore|well|tag|sn|slot|rig)\s*[:#\-]?\s*([A-Z0-9\-_/#]+)\b"
    )

    # People / Roles
    PEOPLE_PATTERN = re.compile(
        r"(?i)\b(supervisor|inspector|engineer|operator|logged by|reviewed by|driller|technician)\s*[:\-]\s*([A-Z][a-zA-Z\.\s]+?)(?=[,\n|\-]|$)"
    )

    # Action / Task keywords
    ACTION_KEYWORDS = [
        "replace", "inspect", "check", "monitor", "repair", "perform",
        "retorque", "maintain", "calibrate", "clean", "follow up", "test", "trip"
    ]

    # Observation keywords
    OBSERVATION_KEYWORDS = [
        "vibration", "leakage", "leak", "rose", "dropped", "temperature", "pressure",
        "gas", "fluctuation", "wear", "noise", "porosity", "lithology", "fracture", "kick"
    ]

    @classmethod
    def extract_structured(cls, text: str, fallback_title: Optional[str] = None) -> Dict[str, Any]:
        """
        Extracts structured entities, tags, and summary from handwritten note text.
        """
        if not text:
            return {
                "title": fallback_title or "Untitled Handwritten Note",
                "date": None,
                "summary": "",
                "observations": [],
                "measurements": [],
                "tasks": [],
                "entities": [],
                "tags": [],
            }

        lines = [line.strip() for line in text.split("\n") if line.strip()]

        # Determine Title (First non-empty line or capitalized header)
        title = lines[0] if lines else (fallback_title or "Handwritten Operational Note")
        if len(title) > 90:
            title = title[:87] + "..."

        # Extract Dates
        dates = []
        for pat in cls.DATE_PATTERNS:
            for match in re.finditer(pat, text, re.IGNORECASE):
                d = match.group(0).strip()
                if d not in dates:
                    dates.append(d)

        # Extract Times
        times = []
        for pat in cls.TIME_PATTERNS:
            for match in re.finditer(pat, text, re.IGNORECASE):
                t = match.group(0).strip()
                if t not in times:
                    times.append(t)

        # Extract Measurements
        measurements: List[Dict[str, str]] = []
        for m in cls.MEASUREMENT_PATTERN.finditer(text):
            label = m.group(1).strip()
            # Clean label prefix noise
            label = re.sub(r"^[-–*•\d\.\s]+", "", label).strip()
            val = m.group(2).strip()
            unit = m.group(3).strip()
            if len(label) < 30 and label.lower() not in ("date", "time"):
                measurements.append({
                    "parameter": label,
                    "value": f"{val} {unit}",
                    "numeric_value": float(val),
                    "unit": unit,
                })

        # Extract Identifiers
        entities: List[Dict[str, str]] = []
        for match in cls.IDENTIFIER_PATTERN.finditer(text):
            kind = match.group(1).strip().upper()
            val = match.group(2).strip()
            if val:
                entities.append({"type": kind, "value": val})

        # Extract People
        people: List[Dict[str, str]] = []
        for match in cls.PEOPLE_PATTERN.finditer(text):
            role = match.group(1).strip().title()
            name = match.group(2).strip()
            if len(name) > 2:
                people.append({"role": role, "name": name})

        # Extract Observations & Tasks from bullet lines / numbered lines
        observations: List[str] = []
        tasks: List[str] = []
        tags: List[str] = []

        for line in lines:
            lower = line.lower()
            # Clean leading bullet or number
            clean_line = re.sub(r"^[-–*•\d\.\)\s]+", "", line).strip()
            if not clean_line or len(clean_line) < 5:
                continue

            # Check for action/task
            if any(lower.startswith(act) or f" {act} " in lower for act in cls.ACTION_KEYWORDS):
                if clean_line not in tasks:
                    tasks.append(clean_line)

            # Check for observation
            if any(obs in lower for obs in cls.OBSERVATION_KEYWORDS):
                if clean_line not in observations:
                    observations.append(clean_line)

        # Tags generation based on detected content
        if "drill" in text.lower() or "rig" in text.lower():
            tags.append("Drilling")
        if "pump" in text.lower() or "valve" in text.lower() or "maintenance" in text.lower():
            tags.append("Maintenance")
        if "vibration" in text.lower():
            tags.append("Vibration")
        if "mud" in text.lower() or "viscosity" in text.lower() or "pit" in text.lower():
            tags.append("Fluid/Mud")
        if "core" in text.lower() or "geolog" in text.lower() or "formation" in text.lower():
            tags.append("Geology")
        if "inspection" in text.lower():
            tags.append("Inspection")

        # Summary generation (First 2-3 lines or observation summary)
        summary = " ".join(lines[1:3]) if len(lines) > 1 else lines[0] if lines else ""
        if len(summary) > 250:
            summary = summary[:247] + "..."

        # Specific form fields extraction (Highly permissive for OCR table scrambling)
        well_id_match = re.search(r"(?i)well\s*(?:id|name)[^\n]*?([A-Za-z0-9\-\/]{5,})", text)
        depth_match = re.search(r"(?i)current\s*depth[^\d\n]*?([0-9]{2,}\.[0-9]+)", text)
        water_depth_match = re.search(r"(?i)water\s*depth[^\d\n]*?([0-9]{1,}\.[0-9]+)", text)
        current_op_match = re.search(r"(?i)(?:current\s*operation|operation\s*/\s*activity)[^\n|A-Za-z]*([A-Za-z0-9\s\.\-]+)", text)
        # Extract reporting period (handle single line, multi-line, and From... To... blocks)
        report_period_match = (
            re.search(r"(?is)(?:reporting\s*period|report\s*period)[\s\:\-\|]*(From[\s\S]*?To[\s\S]*?\d{4})", text)
            or re.search(r"(?is)(From\s*:\s*0?6:00[\s\S]*?To\s*:\s*0?6:00[\s\S]*?\d{4})", text)
            or re.search(r"(?is)(From\s*:\s*\d{1,2}:\d{2}[\s\S]*?To\s*:\s*\d{1,2}:\d{2}[^\n\|]*)", text)
            or re.search(r"(?i)reporting\s*period[^\n\|]*[:\-\|]\s*([^\n\|]+)", text)
            or re.search(r"(?is)4\.\s*REPORTING\s*PERIOD[\s\:\-\|]*([^\n\#\|]+)", text)
        )
        
        extracted_report_period = None
        if report_period_match:
            extracted_report_period = re.sub(r"\s+", " ", report_period_match.group(1)).strip()

        # Look for Summary/Remarks in the bottom section (e.g., 19. DAILY SUMMARY, ABNORMAL REMARKS)
        abnormal_remarks_match = (
            re.search(r"(?is)(?:19\.\s*DAILY\s*SUMMARY|DAILY\s*SUMMARY|abnormal\s*remarks|SUMMARY:)\s*[:\-]?\s*([^\n\#\|]+)", text)
            or re.search(r"(?i)(?:abnormal\s*remarks|remarks|summary)\s*[:\-]?\s*(.*?)(?:\n|$)", text)
        )
        extracted_remarks = None
        if abnormal_remarks_match:
            extracted_remarks = re.sub(r"\s+", " ", abnormal_remarks_match.group(1)).strip()

        return {
            "title": title,
            "date": dates[0] if dates else None,
            "all_dates": dates,
            "times": times,
            "summary": summary,
            "observations": observations[:8],
            "measurements": measurements[:15],
            "tasks": tasks[:8],
            "entities": entities + people,
            "tags": list(set(tags)),
            "well_id": well_id_match.group(1).strip() if well_id_match else None,
            "depth": depth_match.group(1).strip() if depth_match else None,
            "water_depth": water_depth_match.group(1).strip() if water_depth_match else None,
            "report_period": extracted_report_period,
            "abnormal_remarks": extracted_remarks or "None",
        }
