import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List

def generate_case_export_json(
    output_path: str,
    case_data: Dict[str, Any],
    officer_info: Dict[str, str],
    evidence_list: List[Dict[str, Any]],
    entities_list: List[Dict[str, Any]],
    entity_links: List[Dict[str, Any]],
    cdr_summary: Dict[str, Any],
    financial_summary: Dict[str, Any],
    extracted_summary: Dict[str, Any],
    audit_summary: Dict[str, Any]
) -> str:
    """
    Builds a complete, machine-readable forensic case archive in JSON format.
    Calculates and returns the SHA-256 digest of the saved file.
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    now_utc_str = datetime.now(timezone.utc).isoformat()

    payload = {
        "$schema": "https://caseconnect.internal/schemas/case-dossier-v1.json",
        "export_metadata": {
            "system": "Case Connect AI (v1.0)",
            "statutory_standard": "Section 63 Bharatiya Sakshya Adhiniyam, 2023",
            "exported_at": now_utc_str,
            "export_format": "JSON_ARCHIVE"
        },
        "certifying_officer": {
            "name": officer_info.get("name", "Investigating Officer"),
            "rank": officer_info.get("rank", "Inspector"),
            "station": officer_info.get("station", case_data.get("police_station", "Special Cyber Crime Unit")),
            "unit": officer_info.get("unit", "Law Enforcement Agency"),
            "remarks": officer_info.get("remarks", "")
        },
        "case": {
            "id": case_data.get("id"),
            "title": case_data.get("title"),
            "description": case_data.get("description"),
            "status": case_data.get("status"),
            "priority": case_data.get("priority"),
            "fir_number": case_data.get("fir_number"),
            "police_station": case_data.get("police_station"),
            "crime_category": case_data.get("crime_category"),
            "created_at": str(case_data.get("created_at"))
        },
        "evidence_inventory": evidence_list,
        "entities": entities_list,
        "entity_links": entity_links,
        "telecommunications": cdr_summary,
        "financial_flows": financial_summary,
        "document_extractions": extracted_summary,
        "cryptographic_audit": audit_summary
    }

    raw_json = json.dumps(payload, indent=2, default=str)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(raw_json)

    sha256_hash = hashlib.sha256(raw_json.encode("utf-8")).hexdigest()
    return sha256_hash
