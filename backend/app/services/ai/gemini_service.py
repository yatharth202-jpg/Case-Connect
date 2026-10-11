import json
import logging
import hashlib
from typing import Dict, Any, List, Optional
import httpx
from backend.app.config import settings

logger = logging.getLogger(__name__)

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
_GEMINI_CACHE: Dict[str, str] = {}

def is_gemini_configured() -> bool:
    """Returns True if a valid GEMINI_API_KEY is configured in settings or environment."""
    return bool(settings.GEMINI_API_KEY and settings.GEMINI_API_KEY.strip())

ACTIVE_MODELS = ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-flash-lite-latest", "gemini-2.5-flash"]

def _clean_json_text(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    return cleaned.strip()

async def call_gemini_api(
    prompt: str,
    system_prompt: Optional[str] = None,
    json_mode: bool = False,
    timeout_seconds: float = 6.0
) -> Optional[str]:
    """
    Executes a direct, lightweight call to the Google Gemini API.
    Does not require external SDK versions and runs asynchronously via httpx.
    """
    api_key = settings.GEMINI_API_KEY
    if not api_key or not api_key.strip():
        logger.info("Gemini API key is not configured; skipping AI call.")
        return None

    configured_model = getattr(settings, "GEMINI_MODEL", "gemini-2.0-flash") or "gemini-2.0-flash"
    models_to_try = list(dict.fromkeys([configured_model] + ACTIVE_MODELS))

    contents = []
    if system_prompt:
        contents.append({
            "role": "user",
            "parts": [{"text": f"SYSTEM INSTRUCTION:\n{system_prompt}\n\nUSER PROMPT:\n{prompt}"}]
        })
    else:
        contents.append({
            "role": "user",
            "parts": [{"text": prompt}]
        })

    payload: Dict[str, Any] = {
        "contents": contents,
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 2048,
        }
    }

    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            for current_model in models_to_try:
                target_url = f"https://generativelanguage.googleapis.com/v1beta/models/{current_model}:generateContent?key={api_key.strip()}"
                try:
                    resp = await client.post(target_url, json=payload)
                    if resp.status_code == 200:
                        data = resp.json()
                        candidates = data.get("candidates", [])
                        if candidates:
                            parts = candidates[0].get("content", {}).get("parts", [])
                            if parts:
                                return parts[0].get("text", "").strip()
                    elif resp.status_code in [404, 429]:
                        continue
                except (httpx.TimeoutException, httpx.RequestError):
                    continue
            return None
    except Exception as e:
        logger.error(f"Exception during Gemini API request: {e}")
        return None


def call_gemini_sync(
    prompt: str,
    system_prompt: Optional[str] = None,
    json_mode: bool = False,
    timeout_seconds: float = 3.5
) -> Optional[str]:
    """
    Direct synchronous HTTP execution to prevent event loop deadlocks.
    Fast failover between active Gemini models without lingering sleeps.
    Results are cached in memory by hash of prompt + system_prompt.
    """
    api_key = settings.GEMINI_API_KEY
    if not api_key or not api_key.strip():
        return None

    cache_key = hashlib.sha256(f"{prompt}|{system_prompt or ''}".encode("utf-8")).hexdigest()
    if cache_key in _GEMINI_CACHE:
        return _GEMINI_CACHE[cache_key]

    configured_model = getattr(settings, "GEMINI_MODEL", "gemini-2.0-flash") or "gemini-2.0-flash"
    models_to_try = list(dict.fromkeys([configured_model, "gemini-2.0-flash", "gemini-1.5-flash"]))[:2]

    contents = []
    if system_prompt:
        contents.append({
            "role": "user",
            "parts": [{"text": f"SYSTEM INSTRUCTION:\n{system_prompt}\n\nUSER PROMPT:\n{prompt}"}]
        })
    else:
        contents.append({
            "role": "user",
            "parts": [{"text": prompt}]
        })

    payload = {
        "contents": contents,
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 2048,
        }
    }

    try:
        with httpx.Client(timeout=timeout_seconds) as client:
            for current_model in models_to_try:
                target_url = f"https://generativelanguage.googleapis.com/v1beta/models/{current_model}:generateContent?key={api_key.strip()}"
                try:
                    resp = client.post(target_url, json=payload)
                    if resp.status_code == 200:
                        data = resp.json()
                        candidates = data.get("candidates", [])
                        if candidates:
                            parts = candidates[0].get("content", {}).get("parts", [])
                            if parts:
                                out_text = parts[0].get("text", "").strip()
                                _GEMINI_CACHE[cache_key] = out_text
                                return out_text
                    elif resp.status_code in [400, 401, 403]:
                        # Invalid key or bad request: abort immediately, do not retry other models
                        return None
                    elif resp.status_code in [404, 429]:
                        continue
                except (httpx.TimeoutException, httpx.RequestError):
                    # Network offline or timeout: abort immediately to keep pipeline responsive
                    return None
        return None
    except Exception as e:
        logger.error(f"Exception during Gemini sync call: {e}")
        return None


def extract_entities_with_gemini(document_text: str, page_ref: str = "P1") -> List[Dict[str, Any]]:
    """
    Uses Gemini to extract entities and coded roles from unstructured police documents,
    FIRs, wiretap transcripts, or WhatsApp logs.
    """
    if not is_gemini_configured() or not document_text.strip():
        return []

    system_instruction = (
        "You are an expert criminal intelligence and digital forensics officer operating under "
        "Section 63 of Bharatiya Sakshya Adhiniyam (BSA 2023). Extract all entities and identifiers "
        "from the provided police investigation document. Return ONLY valid JSON adhering strictly "
        "to the requested format.\n"
        "RULES:\n"
        "1. Police officers (IO, SHO, SI, Inspector, Constable, Sub-Inspector) MUST have role_description 'police_officer', NEVER 'suspect'.\n"
        "2. Victims/Complainants must have role_description 'victim'. Witnesses must have role_description 'witness'.\n"
        "3. Only genuine suspects, accused persons, and cash/hawala carriers should have role_description 'suspect', 'mule', or 'kingpin'.\n"
        "4. Non-person entities (Phone, Vehicle, Bank Account, FIR) should have role_description ''."
    )

    prompt = f"""Analyze the following police investigation text and extract all entities:
Document Text:
\"\"\"{document_text[:5000]}\"\"\"

Return a JSON array of objects with the exact schema:
[
  {{
    "entity_type": "PERSON | PHONE | BANK_ACCOUNT | VEHICLE | FIR | ORGANIZATION",
    "raw_value": "exact mention in text",
    "normalized_value": "standardized canonical format",
    "role_description": "police_officer / suspect / mule / kingpin / courier / witness / driver / victim",
    "confidence": 0.95
  }}
]
"""

    raw_json = call_gemini_sync(prompt, system_prompt=system_instruction, json_mode=True, timeout_seconds=5.0)
    if not raw_json:
        return []

    try:
        cleaned = _clean_json_text(raw_json)
        parsed = json.loads(cleaned)
        if isinstance(parsed, list):
            results = []
            for item in parsed:
                t = str(item.get("entity_type", "PERSON")).upper()
                raw_v = str(item.get("raw_value", "")).strip()
                norm_v = str(item.get("normalized_value", raw_v)).strip()
                if raw_v and norm_v:
                    results.append({
                        "entity_type": t if t in ["PERSON", "PHONE", "BANK_ACCOUNT", "VEHICLE", "FIR", "ORGANIZATION"] else "PERSON",
                        "raw_value": raw_v,
                        "normalized_value": norm_v,
                        "page_or_paragraph": page_ref,
                        "char_span_start": 0,
                        "char_span_end": len(raw_v),
                        "confidence": float(item.get("confidence", 0.9)),
                        "method": "gemini_llm_ner",
                        "role": item.get("role_description", "")
                    })
            return results
    except Exception as e:
        logger.warning(f"Failed to parse Gemini entity extraction JSON: {e}")

    return []


def generate_case_modus_operandi_sync(case_context: Dict[str, Any]) -> str:
    """
    Synchronously generates an executive forensic narrative and Modus Operandi breakdown.
    """
    if not is_gemini_configured():
        return ""

    system_instruction = (
        "You are a Senior Digital Forensics & Financial Intelligence Analyst. "
        "Review the evidence facts for this case and generate a concise, court-ready, "
        "Section 63 BSA 2023 compliant Modus Operandi & Crime Nexus Brief. "
        "Be factual, concise, cite specific entity IDs, amounts, and dates where available."
    )

    prompt = f"""Case Facts and Forensic Correlation Overview:
Case Title: {case_context.get('title')}
Total Money Volume: {case_context.get('total_money_volume', 'N/A')}
Total Transactions: {case_context.get('total_txns', 0)}
Total Calls Ingested: {case_context.get('total_calls', 0)}
Tracked Vehicles: {case_context.get('vehicles', [])}
Top Scored Target Leads: {case_context.get('leads', [])}
Algorithmic Pattern Alerts: {case_context.get('alerts', [])}

Write a professional forensic synthesis."""

    res = call_gemini_sync(prompt, system_prompt=system_instruction, timeout_seconds=6.0)
    return res or ""


async def generate_case_modus_operandi(case_context: Dict[str, Any]) -> str:
    """
    Async wrapper for callers.
    """
    return generate_case_modus_operandi_sync(case_context)


async def answer_investigation_copilot_query(query: str, case_context: Dict[str, Any]) -> str:
    """
    Answers natural language queries from investigating officers regarding
    specific accounts, phone calls, vehicles, or suspects in the case.
    """
    if not is_gemini_configured():
        return "Gemini AI API key is not configured. Provide GEMINI_API_KEY in .env to activate the Investigation Copilot."

    system_instruction = (
        "You are the Case Connect AI Investigation Copilot. You assist police officers and investigators "
        "by answering queries strictly based on the ingested case evidence, financial transactions, "
        "phone records, ANPR sightings, and graph nodes provided in the context. "
        "If information is not present in the case data, clearly state that it is not in the uploaded records."
    )

    prompt = f"""Investigation Case Context:
{json.dumps(case_context, indent=2, default=str)}

Officer's Query:
\"{query}\"

Provide a direct, factual forensic response with citations to specific accounts, phones, or timestamps where relevant."""

    res = await call_gemini_api(prompt, system_prompt=system_instruction)
    return res or "No response could be generated for this query."
