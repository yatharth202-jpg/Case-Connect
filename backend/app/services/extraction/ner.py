import re
import json
from typing import Dict, Any, List, Set, Tuple, Optional

# Expanded patterns for Indian narrative legal text & criminal dossiers
PERSON_TITLE_PATTERN = re.compile(
    r'\b(?:Shri|Smt\.?|Mr\.?|Mrs\.?|Ms\.?|Sri|Dr\.?|advocate|accused(?:\s+person)?|suspect|kingpin|mastermind|operator|handler|mule|courier|driver|complainant|victim|informant|named|alias|a\.k\.a\.?|known\s+as|namely|s/o|d/o|w/o)\s+([A-Za-z]+(?:\s+[A-Za-z]+){1,3})\b',
    re.IGNORECASE
)

# All-caps names commonly found in police FIRs (e.g. VIKRAM RATHORE, SURESH AGARWAL)
ALL_CAPS_NAME_PATTERN = re.compile(
    r'\b([A-Z]{3,15}\s+[A-Z]{3,15}(?:\s+[A-Z]{3,15})?)\b'
)

# Honorific words and legal role markers to strip when normalizing person name
HONORIFICS = {
    "shri", "smt", "mr", "mrs", "ms", "sri", "dr", "advocate", "accused",
    "suspect", "kingpin", "mastermind", "operator", "handler", "mule",
    "courier", "driver", "complainant", "victim", "informant", "person", "namely"
}

# Role inference dictionary based on surrounding context
ROLE_KEYWORDS = {
    "kingpin": ["kingpin", "mastermind", "syndicate head", "boss", "gang leader", "main accused"],
    "suspect": ["accused", "suspect", "involved", "perpetrator", "culprit", "conspirator"],
    "operator": ["operator", "hawala dealer", "angadia", "money changer", "handler", "facilitator"],
    "mule": ["mule", "dummy account", "shell", "beneficiary", "cash courier", "runner"],
    "victim": ["complainant", "victim", "informant", "aggrieved", "reporting person"]
}

def infer_entity_role(context_sentence: str) -> str:
    s = context_sentence.lower()
    for role, kw_list in ROLE_KEYWORDS.items():
        if any(kw in s for kw in kw_list):
            return role
    return "person"

_nlp = None

def get_spacy_nlp():
    global _nlp
    if _nlp is None:
        try:
            import spacy
            _nlp = spacy.load("en_core_web_sm")
        except Exception:
            _nlp = False
    return _nlp if _nlp is not False else None

def extract_ner_entities(
    text: str,
    page_or_para: str,
    base_char_offset: int = 0,
    existing_spans: List[Tuple[int, int]] = None
) -> List[Dict[str, Any]]:
    """
    Extracts PERSON candidates using spaCy NER with deterministic keyword/title fallback,
    all-caps legal names, and criminal role detection.
    Resolves overlaps: existing rule spans strictly take precedence.
    """
    results: List[Dict[str, Any]] = []
    occupied_spans = list(existing_spans or [])

    def overlaps_any(start: int, end: int) -> bool:
        for s, e in occupied_spans:
            if not (end <= s or start >= e):
                return True
        return False

    nlp = get_spacy_nlp()
    if nlp:
        try:
            doc = nlp(text)
            for ent in doc.ents:
                if ent.label_ in ["PERSON", "ORG"]:
                    start = base_char_offset + ent.start_char
                    end = base_char_offset + ent.end_char
                    raw = ent.text.strip()
                    if len(raw) >= 3 and not overlaps_any(start, end):
                        tokens = raw.split()
                        clean_tokens = [t for t in tokens if t.lower().rstrip('.') not in HONORIFICS]
                        norm = " ".join(clean_tokens).lower() if clean_tokens else raw.lower()
                        display_name = " ".join(clean_tokens).title() if clean_tokens else raw.title()

                        # Extract context window to detect role
                        window_start = max(0, ent.start_char - 80)
                        window_end = min(len(text), ent.end_char + 80)
                        context_snippet = text[window_start:window_end]
                        detected_role = infer_entity_role(context_snippet)

                        # Determine if this is truly an organization or actually a person
                        org_indicators = ["ltd", "limited", "bank", "pvt", "corp", "corporation", "inc", "trust", "hospital", "police", "agency"]
                        is_org = (ent.label_ == "ORG") and any(ind in raw.lower() for ind in org_indicators)

                        occupied_spans.append((start, end))
                        results.append({
                            "entity_type": "ORGANIZATION" if is_org else "PERSON",
                            "raw_value": display_name,
                            "normalized_value": norm,
                            "char_span_start": start,
                            "char_span_end": end,
                            "page_or_paragraph": page_or_para,
                            "confidence": 0.85,
                            "method": "spacy_ner",
                            "role": detected_role
                        })
        except Exception:
            pass

    # Heuristic fallback 1: Capitalized / Title-prefixed names
    for m in PERSON_TITLE_PATTERN.finditer(text):
        raw_name = m.group(1).strip()
        start = base_char_offset + m.start(1)
        end = base_char_offset + m.end(1)

        if not overlaps_any(start, end):
            tokens = raw_name.split()
            clean_tokens = [t for t in tokens if t.lower().rstrip('.') not in HONORIFICS]
            norm = " ".join(clean_tokens).lower() if clean_tokens else raw_name.lower()
            display_name = " ".join(clean_tokens).title() if clean_tokens else raw_name.title()
            if len(clean_tokens) >= 2 or len(norm) >= 4:
                window_start = max(0, m.start() - 60)
                window_end = min(len(text), m.end() + 60)
                context_snippet = text[window_start:window_end]
                detected_role = infer_entity_role(context_snippet)

                occupied_spans.append((start, end))
                results.append({
                    "entity_type": "PERSON",
                    "raw_value": display_name,
                    "normalized_value": norm,
                    "char_span_start": start,
                    "char_span_end": end,
                    "page_or_paragraph": page_or_para,
                    "confidence": 0.80,
                    "method": "title_heuristic",
                    "role": detected_role
                })

    # Heuristic fallback 2: ALL CAPS names in FIRs (ignoring keywords like FIR, POLICE, STATION)
    EXCLUDED_CAPS = {"POLICE", "STATION", "DELHI", "MUMBAI", "INDIA", "SECTION", "REPORT", "COURT", "OFFICER"}
    for m in ALL_CAPS_NAME_PATTERN.finditer(text):
        raw_name = m.group(1).strip()
        tokens = [t for t in raw_name.split() if t not in EXCLUDED_CAPS]
        if len(tokens) >= 2:
            start = base_char_offset + m.start(1)
            end = base_char_offset + m.end(1)
            if not overlaps_any(start, end):
                norm = " ".join(tokens).title().lower()
                window_start = max(0, m.start() - 60)
                window_end = min(len(text), m.end() + 60)
                context_snippet = text[window_start:window_end]
                detected_role = infer_entity_role(context_snippet)

                occupied_spans.append((start, end))
                results.append({
                    "entity_type": "PERSON",
                    "raw_value": raw_name.title(),
                    "normalized_value": norm,
                    "char_span_start": start,
                    "char_span_end": end,
                    "page_or_paragraph": page_or_para,
                    "confidence": 0.75,
                    "method": "all_caps_heuristic",
                    "role": detected_role
                })

    return results

def extract_cooccurrence_relationships(
    text: str,
    extracted_entities: List[Dict[str, Any]],
    page_or_para: str,
    base_char_offset: int = 0
) -> List[Dict[str, Any]]:
    """
    Extracts candidate entity relationships based on sentence co-occurrence.
    Co-occurrence of PERSON with PHONE -> USES
    Co-occurrence of PERSON with BANK_ACCOUNT -> OWNS
    Co-occurrence of PERSON with VEHICLE -> DRIVES
    Confidence = min(person_conf, target_conf) * 0.8.
    """
    relationships: List[Dict[str, Any]] = []

    # Separate persons and targets
    persons = [e for e in extracted_entities if e["entity_type"] == "PERSON"]
    targets = [e for e in extracted_entities if e["entity_type"] in ["PHONE", "BANK_ACCOUNT", "VEHICLE"]]

    if not persons or not targets:
        return []

    # Split text into sentences with char bounds
    sentence_spans = []
    for m in re.finditer(r'([^.!?\n]+[.!?\n]*)', text):
        s_text = m.group(1).strip()
        if s_text:
            s_start = base_char_offset + m.start()
            s_end = base_char_offset + m.end()
            sentence_spans.append((s_start, s_end, s_text))

    # Match co-occurrences within the same sentence
    seen_pairs = set()

    for s_start, s_end, s_text in sentence_spans:
        s_persons = [p for p in persons if s_start <= p["char_span_start"] < s_end]
        s_targets = [t for t in targets if s_start <= t["char_span_start"] < s_end]

        # 1. Person to Identifier (Phone, Account, Vehicle)
        for p in s_persons:
            for tgt in s_targets:
                pair_key = (p["normalized_value"], tgt["normalized_value"])
                if pair_key in seen_pairs:
                    continue
                seen_pairs.add(pair_key)

                rel_type = "USES" if tgt["entity_type"] == "PHONE" else ("DRIVES" if tgt["entity_type"] == "VEHICLE" else "OWNS")
                conf = round(min(p.get("confidence", 0.6), tgt.get("confidence", 0.9)) * 0.8, 2)

                rel_data = {
                    "source": p["normalized_value"],
                    "source_display": p["raw_value"],
                    "target": tgt["normalized_value"],
                    "target_display": tgt["raw_value"],
                    "target_type": tgt["entity_type"],
                    "relationship_type": rel_type,
                    "sentence": s_text[:200]
                }

                relationships.append({
                    "entity_type": "RELATIONSHIP",
                    "raw_value": f"{p['raw_value']} {rel_type} {tgt['raw_value']}",
                    "normalized_value": json.dumps(rel_data),
                    "char_span_start": min(p["char_span_start"], tgt["char_span_start"]),
                    "char_span_end": max(p["char_span_end"], tgt["char_span_end"]),
                    "page_or_paragraph": page_or_para,
                    "confidence": conf,
                    "method": "cooccurrence"
                })

        # 2. Person to Person relationships
        if len(s_persons) >= 2:
            s_lower = s_text.lower()
            rel_type = "CONNECTED_TO"
            if any(w in s_lower for w in ["transfer", "sent", "paid", "gave", "remitted", "hawala"]):
                rel_type = "TRANSFERRED_TO"
            elif any(w in s_lower for w in ["along with", "associate", "accomplice", "partner", "gang", "co-accused"]):
                rel_type = "ACCOMPLICE_OF"
            elif any(w in s_lower for w in ["call", "contact", "communicated", "spoke"]):
                rel_type = "COMMUNICATED_WITH"

            for i in range(len(s_persons)):
                for j in range(i + 1, len(s_persons)):
                    p1 = s_persons[i]
                    p2 = s_persons[j]
                    pair_key = (p1["normalized_value"], p2["normalized_value"])
                    if pair_key in seen_pairs:
                        continue
                    seen_pairs.add(pair_key)

                    rel_data = {
                        "source": p1["normalized_value"],
                        "source_display": p1["raw_value"],
                        "target": p2["normalized_value"],
                        "target_display": p2["raw_value"],
                        "target_type": "PERSON",
                        "relationship_type": rel_type,
                        "sentence": s_text[:200]
                    }
                    relationships.append({
                        "entity_type": "RELATIONSHIP",
                        "raw_value": f"{p1['raw_value']} {rel_type} {p2['raw_value']}",
                        "normalized_value": json.dumps(rel_data),
                        "char_span_start": min(p1["char_span_start"], p2["char_span_start"]),
                        "char_span_end": max(p1["char_span_end"], p2["char_span_end"]),
                        "page_or_paragraph": page_or_para,
                        "confidence": 0.75,
                        "method": "cooccurrence"
                    })

    return relationships
