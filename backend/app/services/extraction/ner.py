import json
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from backend.app.config import get_extraction_config, get_fir_patterns
from backend.app.services.ingestion.normalize import (
    normalize_account,
    normalize_amount,
    normalize_phone,
    normalize_vehicle,
    to_ascii_digits,
)


def _fir_cfg() -> Dict[str, Any]:
    return get_fir_patterns() or {}


def _ner_cfg() -> Dict[str, Any]:
    return (get_extraction_config() or {}).get("ner", {}) or {}


def _police_ranks() -> Set[str]:
    return {str(x).lower() for x in _fir_cfg().get("police_ranks", [])}


def _honorifics() -> Set[str]:
    return {str(x).lower() for x in _fir_cfg().get("honorifics", [])}


def _honorific_expansions() -> Dict[str, str]:
    raw = _fir_cfg().get("honorific_expansions", {}) or {}
    return {str(k).lower(): str(v).lower() for k, v in raw.items()}


def _non_person_words() -> Set[str]:
    return {str(x).lower() for x in _fir_cfg().get("non_person_words", [])}


def _disallowed_name_tokens() -> Set[str]:
    return {str(x).lower() for x in _fir_cfg().get("disallowed_name_tokens", [])}


def _excluded_name_tokens() -> Set[str]:
    return {str(x).lower() for x in _fir_cfg().get("excluded_name_tokens", [])}


def _excluded_caps() -> Set[str]:
    return {str(x).upper() for x in _fir_cfg().get("excluded_caps", [])}


def _org_indicators() -> List[str]:
    return [str(x).lower() for x in _fir_cfg().get("org_indicators", [])]


def _role_keywords() -> Dict[str, List[str]]:
    raw = _fir_cfg().get("role_keywords", {}) or {}
    return {str(k): [str(w).lower() for w in (v or [])] for k, v in raw.items()}


# Regex to terminate trailing legal descriptors and prepositions from extracted names
NAME_TRIM_REGEX = re.compile(
    r"\b(?:under|sec(?:tion)?|dhara|bnss|bns|ipc|crpc|pmla|bsa|age|aged|years?|r\/o|s\/o|w\/o|d\/o|c\/o|"
    r"son\s+of|wife\s+of|daughter\s+of|resident\s+of|putra|patni|putri|niwasi|"
    r"late|resident|address|near|from|dated|on|at|for|with|who|in|having|occupation|"
    r"alias|also\s+writes|full\s+name|introduced|through|signs\s+as|whose|saved|found|"
    r"was|is|to|a\s+person|another\s+person|shop|twice|after|giving|afterwards|registered|"
    r"recorded|visited|stated|produced|handed|remand|examination|conducted|seized|"
    r"entry|memo|diary|report|reported|procedure|recovered|says|knows|caller|sent|brought|belonging|"
    r"inserted|counted|received|used|uses|using|operated|operating|driving|ka\s+mobile|ke\s+khate)\b.*",
    re.IGNORECASE,
)

PERSON_TITLE_PATTERN = re.compile(
    r"\b(?i:(?:Shri|Smt\.?|Mr\.?|Mrs\.?|Ms\.?|Sri|Dr\.?|advocate|accused(?:\s+person)?|abhiyukt|aropi|"
    r"operator|handler|mule|courier|driver|complainant|shikayatkarta|victim|informant|witness|gawah|sakshi|"
    r"named|alias|a\.k\.a\.?|known\s+as|namely|s/o|d/o|w/o))\s+([A-Z][A-Za-z.\'-]+(?:\s+[A-Z][A-Za-z.\'-]+){0,3})\b"
)

ALL_CAPS_NAME_PATTERN = re.compile(
    r"\b([A-Z]{3,15}\s+[A-Z]{3,15}(?:\s+[A-Z]{3,15})?)\b"
)


def unwrap_text(txt: str) -> str:
    """
    Normalizes hard line wraps common in OCR, FIR, and court records.
    Merges broken sentence lines while preserving structural boundaries.
    """
    lines = txt.splitlines()
    unwrapped: List[str] = []
    for line in lines:
        s = line.strip()
        if not s:
            unwrapped.append("")
            continue
        is_new_block = (
            re.match(
                r"^(?:\d+\.|\([a-z\d]+\)|Entry\s+dated|Case:|DOCUMENT:|FIRST|CASE|STATEMENT|Particulars|"
                r"Details|Action|Officer|Investigating|Complainant|Shikayatkarta|Witness|Gawah|Sakshi|"
                r"Accused|Abhiyukt|Aropi|SEIZURE|SEARCH|Place|Incident|Date|Offence|Acts|"
                r"Name:|Address:|Occupation:|Recorded|Pending:)\b",
                s,
                re.IGNORECASE,
            )
            or (unwrapped and unwrapped[-1].endswith(":"))
        )
        if unwrapped and not is_new_block and unwrapped[-1] != "":
            unwrapped[-1] += " " + s
        else:
            unwrapped.append(s)
    return "\n".join(unwrapped)


def normalize_indian_person_candidates(raw_name: str) -> Dict[str, Any]:
    """
    Indian-name normalization helper for honorifics (`Mohd./Md./Mohammad`, `Shri/Smt`, `Sk./Shaikh`)
    and initials (`R. K. Sharma`).
    IMPORTANT GOVERNANCE INVARIANT:
    - Used ONLY to produce candidate claims (`candidate_variants`, `initials`, `surname`).
    - NEVER merges two distinct person strings automatically; `primary_normalized` preserves
      the token form as written (after stripping non-name prefixes like Shri/Smt/Mr/Mrs) so
      for example 'Mohd. Imran' and 'Mohammad Imran' remain distinct Person records until an
      officer reviews and approves an identity match.
    """
    if not raw_name:
        return {
            "raw": "",
            "display_name": "",
            "primary_normalized": "",
            "candidate_variants": [],
            "initials": [],
            "surname": None,
        }

    cleaned = NAME_TRIM_REGEX.sub("", raw_name).strip()
    cleaned = re.sub(r"^[(\d\s.)\-]+", "", cleaned)
    cleaned = re.sub(r'[",\':;()]+$', "", cleaned)
    cleaned = re.sub(r'^[",\':;()]+', "", cleaned)

    police_ranks = _police_ranks()
    strip_honorifics = _honorifics()
    expansions = _honorific_expansions()

    raw_tokens = [t for t in cleaned.split() if t.strip()]
    kept_tokens: List[str] = []
    for tok in raw_tokens:
        low_clean = tok.lower().rstrip(".")
        if low_clean in police_ranks or low_clean in strip_honorifics:
            continue
        kept_tokens.append(tok)

    if not kept_tokens:
        return {
            "raw": raw_name,
            "display_name": "",
            "primary_normalized": "",
            "candidate_variants": [],
            "initials": [],
            "surname": None,
        }

    # Primary normalized form keeps original token spelling (e.g. "mohd imran" vs "mohammad imran")
    primary_tokens = [t.rstrip(".").lower() for t in kept_tokens if t.rstrip(".")]
    primary_normalized = " ".join(primary_tokens).strip()
    display_name = " ".join(kept_tokens).strip()

    # Candidate variants (expanded honorifics like Mohd. -> Mohammad, and stripped-initial surname candidates)
    candidate_variants: List[str] = []
    expanded_tokens: List[str] = []
    has_expansion = False
    for tok in kept_tokens:
        low = tok.lower()
        low_nodot = low.rstrip(".")
        if low in expansions:
            expanded_tokens.append(expansions[low])
            has_expansion = True
        elif low_nodot in expansions:
            expanded_tokens.append(expansions[low_nodot])
            has_expansion = True
        else:
            expanded_tokens.append(low_nodot)

    if has_expansion:
        expanded_form = " ".join(expanded_tokens).strip()
        if expanded_form and expanded_form != primary_normalized:
            candidate_variants.append(expanded_form)

    initials: List[str] = []
    non_initial_tokens: List[str] = []
    for tok in primary_tokens:
        if len(tok) == 1 and tok.isalpha():
            initials.append(tok.upper())
        else:
            non_initial_tokens.append(tok)

    surname = non_initial_tokens[-1] if non_initial_tokens else None
    if initials and non_initial_tokens:
        # Add candidate pattern showing initial + surname structure without merging
        init_form = " ".join([f"{i.lower()}." for i in initials] + non_initial_tokens)
        if init_form not in candidate_variants and init_form != primary_normalized:
            candidate_variants.append(init_form)

    return {
        "raw": raw_name,
        "display_name": display_name,
        "primary_normalized": primary_normalized,
        "candidate_variants": candidate_variants,
        "initials": initials,
        "surname": surname,
    }


def clean_person_name(raw: str) -> str:
    """Cleans legal prefixes, prepositions, numbers, and honorifics from a candidate name."""
    if not raw:
        return ""
    cand = normalize_indian_person_candidates(raw)
    result = cand["display_name"]
    if not result:
        return ""
    # Normalize internal dots on non-initial words while preserving clean spacing
    tokens = [t.rstrip(".") if len(t.rstrip(".")) > 1 else t for t in result.split()]
    result = " ".join(tokens).strip()
    lowered = result.lower()

    non_person_words = _non_person_words()
    disallowed_tokens = _disallowed_name_tokens()

    if lowered in non_person_words or len(result) < 3:
        return ""
    for tok in tokens:
        tl = tok.lower().rstrip(".")
        if tl.endswith("ing") and tl != "singh":
            return ""
        if tl in disallowed_tokens:
            return ""
    if any(
        org in lowered
        for org in [
            "p.s.",
            "police",
            "bank",
            "co-operative",
            "hospital",
            "court",
            "station",
            "crime branch",
            "special cell",
            "cyber cell",
            "headquarters",
            "chowk",
            "fortuner",
            "creta",
            "scorpio",
        ]
    ):
        return ""
    return result


def _has_keyword_boundary(text_lower: str, keywords: List[str]) -> bool:
    for kw in keywords:
        kw_clean = kw.strip().lower()
        if not kw_clean:
            continue
        if re.search(rf"(?<![a-z0-9]){re.escape(kw_clean)}(?![a-z0-9])", text_lower):
            return True
    return False


def infer_entity_role(context_sentence: str, candidate_name: str = "") -> str:
    """Infers operational role from config-driven keywords using word boundaries without prejudicial terminology."""
    s = context_sentence.lower()
    c_lower = candidate_name.lower()
    role_kw = _role_keywords()

    # Priority 1: Police Officers
    if _has_keyword_boundary(
        s,
        role_kw.get(
            "police_officer",
            ["investigating officer", "officer in charge", "recorded by", "seizing officer", "io", "sho"],
        ),
    ) or _has_keyword_boundary(c_lower, ["si", "insp", "constable", "inspector", "sho", "io"]):
        return "police_officer"

    # Priority 2: Witnesses
    if _has_keyword_boundary(s, role_kw.get("witness", ["witness", "witnesses", "neighbour", "gawah", "sakshi"])):
        return "witness"

    # Priority 3: Complainants / Victims
    if _has_keyword_boundary(
        s,
        role_kw.get("complainant", ["complainant", "victim", "informant", "reporting person", "shikayatkarta"]),
    ):
        return "complainant"

    # Priority 4: Accused / Operational roles
    for role in ["operator", "mule", "accused"]:
        if _has_keyword_boundary(s, role_kw.get(role, [])):
            return role

    return "person"


_nlp_cache: Dict[str, Any] = {}


def get_spacy_nlp(model_name: Optional[str] = None):
    """
    Loads the spaCy model configured under `extraction.ner.model` (default `en_core_web_sm`).
    Falls back gracefully to `en_core_web_sm` or None if a configured larger model is not installed.
    """
    cfg_model = str(model_name or _ner_cfg().get("model") or "en_core_web_sm").strip()
    if cfg_model in _nlp_cache:
        val = _nlp_cache[cfg_model]
        return val if val is not False else None

    try:
        import spacy

        try:
            nlp_obj = spacy.load(cfg_model, disable=["parser", "tagger", "lemmatizer"])
            _nlp_cache[cfg_model] = nlp_obj
            return nlp_obj
        except Exception:
            if cfg_model != "en_core_web_sm":
                nlp_obj = spacy.load("en_core_web_sm", disable=["parser", "tagger", "lemmatizer"])
                _nlp_cache[cfg_model] = nlp_obj
                return nlp_obj
            _nlp_cache[cfg_model] = False
            return None
    except Exception:
        _nlp_cache[cfg_model] = False
        return None


def extract_legal_entities(text: str, page_or_para: str, base_char_offset: int = 0) -> List[Dict[str, Any]]:
    """
    Config-driven extraction engine for Indian legal FIRs, Case Diaries,
    Disclosure Statements, and Search/Seizure memos.
    Reads role-aware and kinship/residence rules from `backend/config/reference/fir_patterns.yaml`.
    """
    results: List[Dict[str, Any]] = []
    seen_norms: Set[str] = set()
    police_officer_norms: Set[str] = set()
    fir_cfg = _fir_cfg()
    ner_cfg = _ner_cfg()
    cutoffs = ner_cfg.get("confidence_cutoffs", {}) or {}
    default_legal_conf = float(cutoffs.get("legal_regex", 0.92))
    min_conf = float(ner_cfg.get("min_conf", 0.65))
    org_inds = _org_indicators()

    def add_entity(
        name: str,
        role: str,
        e_type: str = "PERSON",
        conf: float = default_legal_conf,
        method: str = "legal_police_regex",
        span_override: Optional[Tuple[int, int]] = None,
        extra_meta: Optional[Dict[str, Any]] = None,
    ):
        if conf < min_conf:
            return
        c = clean_person_name(name)
        if not c:
            return
        cand_info = normalize_indian_person_candidates(c)
        norm = cand_info["primary_normalized"] or c.lower()
        if norm in police_officer_norms and role != "police_officer":
            return
        if norm in seen_norms:
            for r in results:
                if r["normalized_value"] == norm:
                    if r.get("role") in ["person", "relative"] and role not in ["person", "relative"]:
                        r["role"] = role
                        r.setdefault("meta", {})["role"] = role
                    if extra_meta:
                        r.setdefault("meta", {}).update(extra_meta)
            return
        seen_norms.add(norm)
        if role == "police_officer":
            police_officer_norms.add(norm)

        if e_type == "PERSON" and any(ind in c.lower() for ind in org_inds):
            e_type = "ORGANIZATION"
            if role == "accused":
                role = "organization_entity"

        if span_override is not None:
            st = base_char_offset + span_override[0]
            en = base_char_offset + span_override[1]
        else:
            idx = text.find(name)
            st = base_char_offset + (idx if idx >= 0 else 0)
            en = st + len(name)

        meta: Dict[str, Any] = {
            "role": role,
            "candidate_variants": cand_info.get("candidate_variants", []),
            "initials": cand_info.get("initials", []),
            "surname": cand_info.get("surname"),
        }
        if extra_meta:
            meta.update(extra_meta)

        results.append({
            "entity_type": e_type,
            "raw_value": c,
            "normalized_value": norm,
            "char_span_start": st,
            "char_span_end": en,
            "page_or_paragraph": page_or_para,
            "confidence": conf,
            "method": method,
            "role": role,
            "meta": meta,
        })

    # 1. Config-driven role rules from fir_patterns.yaml
    for rule in fir_cfg.get("role_rules", []) or []:
        role = str(rule.get("role") or "person")
        pat = rule.get("pattern")
        conf = float(rule.get("confidence", default_legal_conf))
        if not pat:
            continue
        for m in re.finditer(pat, text, re.IGNORECASE):
            add_entity(
                m.group(1),
                role=role,
                conf=conf,
                span_override=(m.start(1), m.end(1)),
            )

    # 2. Kinship & Residence markers ("S/o", "W/o", "D/o", "R/o") from fir_patterns.yaml
    for krule in fir_cfg.get("kinship_and_residence_rules", []) or []:
        marker_type = str(krule.get("marker_type") or "")
        pat = krule.get("pattern")
        conf = float(krule.get("confidence", 0.90))
        if not pat:
            continue
        for m in re.finditer(pat, text, re.IGNORECASE):
            subj_raw = m.group(1).strip()
            obj_raw = m.group(2).strip()
            ctx_window = text[max(0, m.start() - 60) : min(len(text), m.end() + 60)]
            inferred_role = infer_entity_role(ctx_window, subj_raw)
            if marker_type in ("S/O", "W/O", "D/O"):
                rel_clean = clean_person_name(obj_raw)
                add_entity(
                    subj_raw,
                    role=inferred_role,
                    conf=conf,
                    span_override=(m.start(1), m.end(1)),
                    extra_meta={"kinship_marker": marker_type, "relative_name": rel_clean or obj_raw},
                )
                if rel_clean:
                    add_entity(
                        rel_clean,
                        role="relative",
                        conf=round(conf - 0.04, 2),
                        span_override=(m.start(2), m.end(2)),
                    )
            elif marker_type == "R/O":
                add_entity(
                    subj_raw,
                    role=inferred_role,
                    conf=conf,
                    span_override=(m.start(1), m.end(1)),
                    extra_meta={"residence": obj_raw.strip(" ,.")},
                )

    # 3. Police rank prefixes
    for m in re.finditer(
        r"\b(?:SI|Insp\.?|Inspector|Sub-Inspector|Head\s+Constable|HC|Const\.?|Constable)\s+([A-Za-z]+(?:\s+[A-Za-z]+){1,3})\b",
        text,
        re.IGNORECASE,
    ):
        add_entity(m.group(1), role="police_officer", span_override=(m.start(1), m.end(1)))

    # 4. Accused headers & narrative mentions
    for m in re.finditer(
        r"(?:Details\s+of\s+accused(?:\s*\([^)]*\))?|STATEMENT\s+OF\s+ACCUSED[^\n]*\n[^\n]*Name|Person\s+from\s+whom\s+seized|Occupant\s+present)\s*[:\-]?\s*([^\n]+)",
        text,
        re.IGNORECASE,
    ):
        line = m.group(1).strip()
        parts = re.split(r"\(\d+\)|\bAnother\s+person\b|,|\n", line)
        for part in parts:
            add_entity(part, role="accused")

    for m in re.finditer(
        r"\[[A-Z0-9]\]\s+([A-Z\s]{3,35}?)(?:\s+@\s+([^\(\n:]+))?\s*(?:\(([^)]+)\))?\s*:",
        text,
    ):
        target_name = m.group(1).strip()
        alias_name = m.group(2).strip() if m.group(2) else ""
        desc = (m.group(3) or "").lower()
        role = "accused"
        if any(k in desc for k in ["courier", "driver", "transit"]):
            role = "mule"
        elif any(k in desc for k in ["operator", "distributor"]):
            role = "operator"
        add_entity(target_name, role=role, span_override=(m.start(1), m.end(1)))
        if alias_name:
            add_entity(alias_name, role=role, span_override=(m.start(2), m.end(2)))

    for m in re.finditer(
        r"\b(?:representative|accused|perpetrator|person)\s+(?:was\s+)?identified\s+as\s+([A-Za-z.\s]{2,30}?)(?=[,;\n]|\s+operating|\s+driving|\s+having|\s+using|\s+residing|$)",
        text,
        re.IGNORECASE,
    ):
        add_entity(m.group(1), role="accused", span_override=(m.start(1), m.end(1)))

    for m in re.finditer(
        r"\b(?:Arrested\s+accused|The\s+driver)\s+([A-Za-z\s.]+?)(?=\s+under|\s+alias|\s+was|\s+s\/o|\s+r\/o|,|\n)",
        text,
        re.IGNORECASE,
    ):
        add_entity(m.group(1), role="accused", span_override=(m.start(1), m.end(1)))

    # 5. Nicknames & Aliases (kept as separate entities; never auto-merged)
    for m in re.finditer(
        r'["\']([A-Za-z\s]+?\s+(?:bhai|gang|seth|chacha|mama|don|pandit|ustad|babu))["\']|\b(?:caller\s+only\s+as|known\s+as|referred\s+to\s+as|meant\s+for)\s+["\']([^"\']+)["\']',
        text,
        re.IGNORECASE,
    ):
        grp = 1 if m.group(1) else 2
        add_entity(m.group(grp), role="accused", span_override=(m.start(grp), m.end(grp)))

    for m in re.finditer(
        r"\balias\s+([A-Za-z.\s]{2,20}?)(?=[,;\n]|\s+age|\s+s\/o|\s+r\/o|\s+was|\(|$|\s+because)",
        text,
        re.IGNORECASE,
    ):
        add_entity(m.group(1), role="accused", span_override=(m.start(1), m.end(1)))

    # 6. Witnesses
    for m in re.finditer(
        r"\bwitnesses\s+([A-Za-z\s.]+?)\s+and\s+([A-Za-z\s.]+?)(?=[,.\n]|$)",
        text,
        re.IGNORECASE,
    ):
        add_entity(m.group(1), role="witness", span_override=(m.start(1), m.end(1)))
        add_entity(m.group(2), role="witness", span_override=(m.start(2), m.end(2)))
    for m in re.finditer(
        r"\bIndependent\s+witnesses:\s*\(1\)\s*([A-Za-z\s.]+?)[,;]\s*\(2\)\s*([A-Za-z\s.]+?)(?=[,.\n]|$)",
        text,
        re.IGNORECASE,
    ):
        add_entity(m.group(1), role="witness", span_override=(m.start(1), m.end(1)))
        add_entity(m.group(2), role="witness", span_override=(m.start(2), m.end(2)))

    return results


def extract_ner_entities(
    text: str,
    page_or_para: str,
    base_char_offset: int = 0,
    existing_spans: Optional[List[Tuple[int, int]]] = None,
) -> List[Dict[str, Any]]:
    """
    Extracts persons, witnesses, complainants, accused, police officers, and organizations
    using config-driven Legal Domain Patterns + Title Heuristics + spaCy NER (`extraction.ner`).
    Never auto-merges people; Indian honorific/initial variants are emitted as candidate metadata only.
    """
    results: List[Dict[str, Any]] = []
    occupied_spans = list(existing_spans or [])
    ner_cfg = _ner_cfg()
    min_conf = float(ner_cfg.get("min_conf", 0.65))
    cutoffs = ner_cfg.get("confidence_cutoffs", {}) or {}
    label_mapping = ner_cfg.get("label_mapping", {"PERSON": "PERSON", "ORG": "ORGANIZATION"}) or {}
    org_indicators = _org_indicators()
    excluded_name_tokens = _excluded_name_tokens()
    excluded_caps = _excluded_caps()

    def overlaps_any(start: int, end: int) -> bool:
        for s, e in occupied_spans:
            if not (end <= s or start >= e):
                return True
        return False

    clean_unwrapped = unwrap_text(text)

    # 1. Primary: Config-driven legal police document entity extraction
    legal_entities = extract_legal_entities(clean_unwrapped, page_or_para, base_char_offset)
    for le in legal_entities:
        results.append(le)
        occupied_spans.append((le["char_span_start"], le["char_span_end"]))

    seen_norms = {e["normalized_value"] for e in results}

    # 2. Secondary: Capitalized / Title heuristic names
    title_conf = float(cutoffs.get("title_heuristic", 0.85))
    if title_conf >= min_conf:
        for m in PERSON_TITLE_PATTERN.finditer(clean_unwrapped):
            raw_name = m.group(1).strip()
            cleaned_name = clean_person_name(raw_name)
            start = base_char_offset + m.start(1)
            end = base_char_offset + m.end(1)

            if cleaned_name and not overlaps_any(start, end):
                cand_info = normalize_indian_person_candidates(cleaned_name)
                norm = cand_info["primary_normalized"] or cleaned_name.lower()
                if norm not in seen_norms:
                    seen_norms.add(norm)
                    window_start = max(0, m.start() - 70)
                    window_end = min(len(clean_unwrapped), m.end() + 70)
                    context_snippet = clean_unwrapped[window_start:window_end]
                    detected_role = infer_entity_role(context_snippet, cleaned_name)

                    occupied_spans.append((start, end))
                    results.append({
                        "entity_type": "PERSON",
                        "raw_value": cleaned_name,
                        "normalized_value": norm,
                        "char_span_start": start,
                        "char_span_end": end,
                        "page_or_paragraph": page_or_para,
                        "confidence": title_conf,
                        "method": "title_heuristic",
                        "role": detected_role,
                        "meta": {
                            "role": detected_role,
                            "candidate_variants": cand_info.get("candidate_variants", []),
                            "initials": cand_info.get("initials", []),
                            "surname": cand_info.get("surname"),
                        },
                    })

    # 2.5 High-Recall Proper Names (including Indian honorifics like Mohd., Md., Initials)
    proper_conf = float(cutoffs.get("proper_name", 0.88))
    proper_name_pattern = re.compile(
        r"\b((?:(?:Mohd|Md|Sk|Ch)\.?\s+|[A-Z]\.\s+){0,2}[A-Z][a-z]{2,15}\s+[A-Z][a-z]{2,15}(?:\s+[A-Z][a-z]{2,15})?)\b"
    )
    if proper_conf >= min_conf:
        for m in proper_name_pattern.finditer(clean_unwrapped):
            raw_name = m.group(1).strip()
            cleaned_name = clean_person_name(raw_name)
            start = base_char_offset + m.start(1)
            end = base_char_offset + m.end(1)

            if cleaned_name and not overlaps_any(start, end):
                tokens = [t.lower().rstrip(".") for t in cleaned_name.split()]
                if len(tokens) >= 2 and not any(t in excluded_name_tokens for t in tokens):
                    cand_info = normalize_indian_person_candidates(raw_name)
                    norm = cand_info["primary_normalized"] or cleaned_name.lower()
                    if norm not in seen_norms:
                        seen_norms.add(norm)
                        window_start = max(0, m.start() - 70)
                        window_end = min(len(clean_unwrapped), m.end() + 70)
                        context_snippet = clean_unwrapped[window_start:window_end]
                        detected_role = infer_entity_role(context_snippet, cleaned_name)
                        is_org = any(ind in cleaned_name.lower() for ind in org_indicators)

                        occupied_spans.append((start, end))
                        results.append({
                            "entity_type": "ORGANIZATION" if is_org else "PERSON",
                            "raw_value": raw_name if "." in raw_name else cleaned_name.title(),
                            "normalized_value": norm,
                            "char_span_start": start,
                            "char_span_end": end,
                            "page_or_paragraph": page_or_para,
                            "confidence": proper_conf,
                            "method": "proper_name_heuristic",
                            "role": "organization_entity" if is_org else detected_role,
                            "meta": {
                                "role": "organization_entity" if is_org else detected_role,
                                "candidate_variants": cand_info.get("candidate_variants", []),
                                "initials": cand_info.get("initials", []),
                                "surname": cand_info.get("surname"),
                            },
                        })

    # 3. Tertiary: spaCy Named Entity Recognition (model & labels from config)
    spacy_conf = float(cutoffs.get("spacy_ner", 0.85))
    nlp = get_spacy_nlp()
    if nlp and spacy_conf >= min_conf:
        try:
            doc = nlp(clean_unwrapped)
            for ent in doc.ents:
                mapped_label = label_mapping.get(ent.label_)
                if mapped_label in ("PERSON", "ORGANIZATION"):
                    start = base_char_offset + ent.start_char
                    end = base_char_offset + ent.end_char
                    raw = ent.text.strip()
                    cleaned_name = clean_person_name(raw)

                    if cleaned_name and not overlaps_any(start, end):
                        cand_info = normalize_indian_person_candidates(raw)
                        norm = cand_info["primary_normalized"] or cleaned_name.lower()
                        # Do not emit single-word fragments if already part of a multi-word extracted name,
                        # EXCEPT we never merge two full distinct names (e.g. Mohd. Imran vs Mohammad Imran).
                        is_single_token_fragment = (
                            len(norm.split()) == 1
                            and any(norm in full_norm.split() for full_norm in seen_norms if len(full_norm.split()) >= 2)
                        )
                        if norm not in seen_norms and not is_single_token_fragment:
                            seen_norms.add(norm)
                            window_start = max(0, ent.start_char - 80)
                            window_end = min(len(clean_unwrapped), ent.end_char + 80)
                            context_snippet = clean_unwrapped[window_start:window_end]
                            detected_role = infer_entity_role(context_snippet, cleaned_name)
                            is_org = (mapped_label == "ORGANIZATION") or any(
                                ind in cleaned_name.lower() for ind in org_indicators
                            )

                            occupied_spans.append((start, end))
                            results.append({
                                "entity_type": "ORGANIZATION" if is_org else "PERSON",
                                "raw_value": cleaned_name.title(),
                                "normalized_value": norm,
                                "char_span_start": start,
                                "char_span_end": end,
                                "page_or_paragraph": page_or_para,
                                "confidence": spacy_conf,
                                "method": "ner",
                                "role": "organization_entity" if is_org else detected_role,
                                "meta": {
                                    "role": "organization_entity" if is_org else detected_role,
                                    "candidate_variants": cand_info.get("candidate_variants", []),
                                    "initials": cand_info.get("initials", []),
                                    "surname": cand_info.get("surname"),
                                },
                            })
        except Exception:
            pass

    # 4. Quaternary: ALL CAPS names
    caps_conf = float(cutoffs.get("all_caps", 0.75))
    if caps_conf >= min_conf:
        for m in ALL_CAPS_NAME_PATTERN.finditer(clean_unwrapped):
            raw_name = m.group(1).strip()
            tokens = [t for t in raw_name.split() if t not in excluded_caps]
            if len(tokens) >= 2:
                cleaned_name = clean_person_name(" ".join(tokens))
                start = base_char_offset + m.start(1)
                end = base_char_offset + m.end(1)
                if cleaned_name and not overlaps_any(start, end):
                    cand_info = normalize_indian_person_candidates(cleaned_name)
                    norm = cand_info["primary_normalized"] or cleaned_name.lower()
                    if norm not in seen_norms:
                        seen_norms.add(norm)
                        window_start = max(0, m.start() - 60)
                        window_end = min(len(clean_unwrapped), m.end() + 60)
                        context_snippet = clean_unwrapped[window_start:window_end]
                        detected_role = infer_entity_role(context_snippet, cleaned_name)

                        occupied_spans.append((start, end))
                        results.append({
                            "entity_type": "PERSON",
                            "raw_value": cleaned_name.title(),
                            "normalized_value": norm,
                            "char_span_start": start,
                            "char_span_end": end,
                            "page_or_paragraph": page_or_para,
                            "confidence": caps_conf,
                            "method": "all_caps_heuristic",
                            "role": detected_role,
                            "meta": {
                                "role": detected_role,
                                "candidate_variants": cand_info.get("candidate_variants", []),
                            },
                        })

    return results


def extract_cooccurrence_relationships(
    text: str,
    extracted_entities: List[Dict[str, Any]],
    page_or_para: str,
    base_char_offset: int = 0,
) -> List[Dict[str, Any]]:
    """
    Rule-based, config-driven relation extraction linking:
    - person-phone ("mobile no. X of Y", "Y used mobile X", etc.)
    - person-account ("account X of Y", "Y operates account X")
    - person-vehicle ("vehicle X driven by Y")
    - person-person roles & kinship ("S/o", "W/o", "D/o", alias, accomplice, courier)
    - money amounts with from/to when stated in sentence
    Outputs proposed `entity_links` (`entity_type='RELATIONSHIP'`) with `method='regex'` or `'ner'`,
    `confidence`, exact `char_span_start` / `char_span_end`, and `status='pending_review'`.
    Never invents links that are not present in the text.
    """
    relationships: List[Dict[str, Any]] = []
    seen_pairs: Set[Tuple[str, str, str]] = set()

    if not text or not text.strip():
        return relationships

    ascii_txt = to_ascii_digits(text)
    clean_txt = unwrap_text(ascii_txt)
    fir_cfg = _fir_cfg()
    rel_cfg = fir_cfg.get("sentence_relation_patterns", {}) or {}

    persons = [e for e in extracted_entities if e["entity_type"] in ["PERSON", "ORGANIZATION"]]
    targets = [e for e in extracted_entities if e["entity_type"] in ["PHONE", "BANK_ACCOUNT", "VEHICLE", "FIR", "AMOUNT"]]

    def _find_span_in_text(snippet: str) -> Tuple[int, int]:
        if not snippet:
            return (base_char_offset, base_char_offset)
        idx = ascii_txt.find(snippet)
        if idx >= 0:
            return (base_char_offset + idx, base_char_offset + idx + len(snippet))
        idx_clean = clean_txt.find(snippet)
        if idx_clean >= 0:
            return (base_char_offset + idx_clean, base_char_offset + idx_clean + len(snippet))
        return (base_char_offset, base_char_offset + min(len(text), len(snippet)))

    def add_rel(
        src: str,
        src_disp: str,
        tgt: str,
        tgt_disp: str,
        tgt_type: str,
        rel_type: str,
        sentence: str,
        conf: float = 0.88,
        method: str = "regex",
        span: Optional[Tuple[int, int]] = None,
        extra: Optional[Dict[str, Any]] = None,
    ):
        if not src or not tgt or src == tgt:
            return
        key = (src, tgt, rel_type)
        if key in seen_pairs:
            return
        seen_pairs.add(key)

        s_start, s_end = span if span is not None else _find_span_in_text(sentence)
        rel_data: Dict[str, Any] = {
            "source": src,
            "source_display": src_disp,
            "target": tgt,
            "target_display": tgt_disp,
            "target_type": tgt_type,
            "relationship_type": rel_type,
            "sentence": sentence[:240],
            "method": method,
            "char_span_start": s_start,
            "char_span_end": s_end,
        }
        if extra:
            rel_data.update(extra)

        relationships.append({
            "entity_type": "RELATIONSHIP",
            "raw_value": f"{src_disp} {rel_type} {tgt_disp}",
            "normalized_value": json.dumps(rel_data),
            "char_span_start": s_start,
            "char_span_end": s_end,
            "page_or_paragraph": page_or_para,
            "confidence": conf,
            "method": method,
            "status": "pending_review",
        })

    # 1. Config-driven sentence patterns: person_phone, person_account, person_vehicle
    for pat_def in rel_cfg.get("person_phone", []) or []:
        pat = pat_def.get("pattern")
        if not pat:
            continue
        p_grp = int(pat_def.get("person_group", 2))
        ph_grp = int(pat_def.get("phone_group", 1))
        rel_type = str(pat_def.get("relationship_type", "USES"))
        conf = float(pat_def.get("confidence", 0.93))
        for m in re.finditer(pat, clean_txt, re.IGNORECASE):
            raw_person = clean_person_name(m.group(p_grp))
            raw_phone = m.group(ph_grp).strip()
            ph_norm = normalize_phone(raw_phone)
            if raw_person and ph_norm and ph_norm.get("valid_mobile"):
                cand = normalize_indian_person_candidates(raw_person)
                p_norm = cand["primary_normalized"] or raw_person.lower()
                add_rel(
                    p_norm,
                    raw_person,
                    ph_norm["number"],
                    raw_phone,
                    "PHONE",
                    rel_type,
                    m.group(0),
                    conf=conf,
                    method="regex",
                    span=(base_char_offset + m.start(), base_char_offset + m.end()),
                )

    for pat_def in rel_cfg.get("person_account", []) or []:
        pat = pat_def.get("pattern")
        if not pat:
            continue
        p_grp = int(pat_def.get("person_group", 2))
        acc_grp = int(pat_def.get("account_group", 1))
        rel_type = str(pat_def.get("relationship_type", "OWNS"))
        conf = float(pat_def.get("confidence", 0.92))
        for m in re.finditer(pat, clean_txt, re.IGNORECASE):
            raw_person = clean_person_name(m.group(p_grp))
            raw_acc = m.group(acc_grp).strip()
            acc_norm = normalize_account(raw_acc)
            if raw_person and acc_norm and len(re.sub(r"\D", "", acc_norm)) >= 9:
                cand = normalize_indian_person_candidates(raw_person)
                p_norm = cand["primary_normalized"] or raw_person.lower()
                add_rel(
                    p_norm,
                    raw_person,
                    acc_norm,
                    raw_acc,
                    "BANK_ACCOUNT",
                    rel_type,
                    m.group(0),
                    conf=conf,
                    method="regex",
                    span=(base_char_offset + m.start(), base_char_offset + m.end()),
                )

    for pat_def in rel_cfg.get("person_vehicle", []) or []:
        pat = pat_def.get("pattern")
        if not pat:
            continue
        p_grp = int(pat_def.get("person_group", 2))
        veh_grp = int(pat_def.get("vehicle_group", 1))
        rel_type = str(pat_def.get("relationship_type", "DRIVES"))
        conf = float(pat_def.get("confidence", 0.92))
        for m in re.finditer(pat, clean_txt, re.IGNORECASE):
            raw_person = clean_person_name(m.group(p_grp))
            raw_veh = m.group(veh_grp).strip()
            veh_norm = normalize_vehicle(raw_veh)
            if raw_person and veh_norm:
                cand = normalize_indian_person_candidates(raw_person)
                p_norm = cand["primary_normalized"] or raw_person.lower()
                add_rel(
                    p_norm,
                    raw_person,
                    veh_norm,
                    raw_veh,
                    "VEHICLE",
                    rel_type,
                    m.group(0),
                    conf=conf,
                    method="regex",
                    span=(base_char_offset + m.start(), base_char_offset + m.end()),
                )

    # 2. Kinship & Residence relationships ("S/o", "W/o", "D/o", "R/o") from fir_patterns.yaml
    for krule in fir_cfg.get("kinship_and_residence_rules", []) or []:
        marker_type = str(krule.get("marker_type") or "")
        rel_type = str(krule.get("relationship_type") or "RELATED_TO")
        pat = krule.get("pattern")
        conf = float(krule.get("confidence", 0.91))
        if not pat:
            continue
        for m in re.finditer(pat, clean_txt, re.IGNORECASE):
            subj = clean_person_name(m.group(1))
            if not subj:
                continue
            subj_norm = normalize_indian_person_candidates(subj)["primary_normalized"] or subj.lower()
            if marker_type in ("S/O", "W/O", "D/O"):
                rel_p = clean_person_name(m.group(2))
                if rel_p:
                    rel_norm = normalize_indian_person_candidates(rel_p)["primary_normalized"] or rel_p.lower()
                    add_rel(
                        subj_norm,
                        subj,
                        rel_norm,
                        rel_p,
                        "PERSON",
                        rel_type,
                        m.group(0),
                        conf=conf,
                        method="regex",
                        span=(base_char_offset + m.start(), base_char_offset + m.end()),
                    )
            elif marker_type == "R/O":
                addr = m.group(2).strip(" ,.")
                if len(addr) >= 4:
                    add_rel(
                        subj_norm,
                        subj,
                        addr.lower(),
                        addr,
                        "LOCATION",
                        rel_type,
                        m.group(0),
                        conf=conf,
                        method="regex",
                        span=(base_char_offset + m.start(), base_char_offset + m.end()),
                    )

    # 3. Alias candidate relationships (never merges people; proposes ALIAS_OF link for officer review)
    for p1 in persons:
        for p2 in persons:
            if p1["normalized_value"] != p2["normalized_value"]:
                r1, r2 = re.escape(p1["raw_value"]), re.escape(p2["raw_value"])
                m_alias = re.search(
                    rf"\b{r1}\b[^\n.]{{0,40}}\balias\b[^\n.]{{0,40}}\b{r2}\b|\b{r1}\b[^\n.]{{0,50}}\(also\s+writes[^\n.]{{0,40}}\b{r2}\b",
                    clean_txt,
                    re.IGNORECASE,
                )
                if m_alias:
                    add_rel(
                        p1["normalized_value"],
                        p1["raw_value"],
                        p2["normalized_value"],
                        p2["raw_value"],
                        "PERSON",
                        "ALIAS_OF",
                        m_alias.group(0),
                        conf=0.95,
                        method="regex",
                        span=(base_char_offset + m_alias.start(), base_char_offset + m_alias.end()),
                    )

    # 4. Entity proximity rules within sentence boundaries (Person <-> Vehicle / Phone / Account / FIR)
    vehicles = [e for e in targets if e["entity_type"] == "VEHICLE"]
    for p in persons:
        if p.get("role") in ["police_officer", "witness", "complainant", "victim"]:
            continue
        for v in vehicles:
            r_p, r_v = re.escape(p["raw_value"]), re.escape(v["raw_value"])
            m_v = re.search(rf"\b{r_p}\b[^\n.]{{0,120}}\b{r_v}\b|\b{r_v}\b[^\n.]{{0,120}}\b{r_p}\b", clean_txt, re.IGNORECASE)
            if m_v:
                add_rel(
                    p["normalized_value"],
                    p["raw_value"],
                    v["normalized_value"],
                    v["raw_value"],
                    "VEHICLE",
                    "DRIVES",
                    m_v.group(0),
                    conf=0.90,
                    method="regex",
                    span=(base_char_offset + m_v.start(), base_char_offset + m_v.end()),
                )

    phones = [e for e in targets if e["entity_type"] == "PHONE"]
    for p in persons:
        if p.get("role") in ["police_officer", "witness"]:
            continue
        for ph in phones:
            r_p, r_ph = re.escape(p["raw_value"]), re.escape(ph["raw_value"])
            m_ph = re.search(rf"\b{r_p}\b[^\n.]{{0,120}}\b{r_ph}\b|\b{r_ph}\b[^\n.]{{0,120}}\b{r_p}\b", clean_txt, re.IGNORECASE)
            if m_ph:
                add_rel(
                    p["normalized_value"],
                    p["raw_value"],
                    ph["normalized_value"],
                    ph["raw_value"],
                    "PHONE",
                    "USES",
                    m_ph.group(0),
                    conf=0.92,
                    method="regex",
                    span=(base_char_offset + m_ph.start(), base_char_offset + m_ph.end()),
                )

    accounts = [e for e in targets if e["entity_type"] == "BANK_ACCOUNT"]
    for p in persons:
        if p.get("role") in ["police_officer", "witness"]:
            continue
        for acc in accounts:
            r_p, r_acc = re.escape(p["raw_value"]), re.escape(acc["raw_value"])
            m_ac = re.search(rf"\b{r_p}\b[^\n.]{{0,140}}\b{r_acc}\b|\b{r_acc}\b[^\n.]{{0,140}}\b{r_p}\b", clean_txt, re.IGNORECASE)
            if m_ac:
                rel = "OWNS" if p["entity_type"] == "ORGANIZATION" or "held in the name" in m_ac.group(0).lower() else "OPERATES"
                add_rel(
                    p["normalized_value"],
                    p["raw_value"],
                    acc["normalized_value"],
                    acc["raw_value"],
                    "BANK_ACCOUNT",
                    rel,
                    m_ac.group(0),
                    conf=0.88,
                    method="regex",
                    span=(base_char_offset + m_ac.start(), base_char_offset + m_ac.end()),
                )

    # 5. Sentence-level co-occurrence & money transfer extraction with from/to
    s_safe = re.sub(
        r"\b(P\.S\.|SI|Insp\.|Sec\.|Rs\.|No\.|Dr\.|Mr\.|Mrs\.|Ms\.|Shri|Smt\.|Mohd\.|Md\.|Sk\.|Ch\.|[A-Z]\.)",
        lambda m: m.group(0).replace(".", "@@DOT@@"),
        clean_txt,
        flags=re.IGNORECASE,
    )
    cursor = 0
    for s_match in re.finditer(r"[^.!?\n]+", s_safe):
        s_raw = s_match.group(0)
        s_text = s_raw.replace("@@DOT@@", ".").strip()
        s_start = base_char_offset + s_match.start()
        s_end = base_char_offset + s_match.end()
        cursor = s_end
        if len(s_text) < 10:
            continue

        s_persons = [p for p in persons if p["raw_value"].lower() in s_text.lower() or p["normalized_value"].lower() in s_text.lower()]
        s_targets = [
            t
            for t in targets
            if t["entity_type"] != "AMOUNT"
            and (t["raw_value"].lower() in s_text.lower() or t["normalized_value"].lower() in s_text.lower())
        ]
        s_amounts = [
            t
            for t in targets
            if t["entity_type"] == "AMOUNT" and t["raw_value"].lower() in s_text.lower()
        ]

        for p in s_persons:
            is_cop = p.get("role") == "police_officer"
            for t in s_targets:
                if is_cop:
                    rel_type = "INVESTIGATES" if t["entity_type"] in ["PHONE", "VEHICLE", "BANK_ACCOUNT"] else "FILED"
                else:
                    rel_type = (
                        "USES"
                        if t["entity_type"] == "PHONE"
                        else (
                            "DRIVES"
                            if t["entity_type"] == "VEHICLE"
                            else ("MENTIONED_IN" if t["entity_type"] == "FIR" else "OWNS")
                        )
                    )
                add_rel(
                    p["normalized_value"],
                    p["raw_value"],
                    t["normalized_value"],
                    t["raw_value"],
                    t["entity_type"],
                    rel_type,
                    s_text,
                    conf=0.82,
                    method="ner",
                    span=(s_start, s_end),
                )

        # Money amount transfer links with explicit from/to in sentence
        if s_amounts:
            amt_ent = s_amounts[0]
            paise_val = int(amt_ent["normalized_value"]) if str(amt_ent["normalized_value"]).lstrip("-").isdigit() else normalize_amount(amt_ent["raw_value"])
            # Case A: Person transferred amount to Account / Person
            if len(s_persons) >= 1 and any(t["entity_type"] == "BANK_ACCOUNT" for t in s_targets):
                acc_t = next(t for t in s_targets if t["entity_type"] == "BANK_ACCOUNT")
                p_src = s_persons[0]
                add_rel(
                    p_src["normalized_value"],
                    p_src["raw_value"],
                    acc_t["normalized_value"],
                    acc_t["raw_value"],
                    "BANK_ACCOUNT",
                    "TRANSFERRED_TO",
                    s_text,
                    conf=0.89,
                    method="regex",
                    span=(s_start, s_end),
                    extra={
                        "amount_paise": paise_val,
                        "amount_raw": amt_ent["raw_value"],
                        "from_party": p_src["normalized_value"],
                        "to_party": acc_t["normalized_value"],
                    },
                )
            elif len(s_persons) >= 2 and any(
                w in s_text.lower() for w in ["transfer", "sent", "paid", "remitted", "rtgs", "neft", "upi", "handed", "gave"]
            ):
                p1, p2 = s_persons[0], s_persons[1]
                add_rel(
                    p1["normalized_value"],
                    p1["raw_value"],
                    p2["normalized_value"],
                    p2["raw_value"],
                    "PERSON",
                    "TRANSFERRED_TO",
                    s_text,
                    conf=0.88,
                    method="regex",
                    span=(s_start, s_end),
                    extra={
                        "amount_paise": paise_val,
                        "amount_raw": amt_ent["raw_value"],
                        "from_party": p1["normalized_value"],
                        "to_party": p2["normalized_value"],
                    },
                )

        if len(s_persons) >= 2:
            s_lower = s_text.lower()
            rel_type = "CONNECTED_TO"
            if any(w in s_lower for w in ["transfer", "sent", "paid", "remitted", "rtgs"]):
                rel_type = "TRANSFERRED_TO"
            elif any(w in s_lower for w in ["along with", "associate", "accomplice", "co-accused"]):
                rel_type = "ACCOMPLICE_OF"
            elif any(w in s_lower for w in ["call", "contact", "communicated", "caller"]):
                rel_type = "COMMUNICATED_WITH"

            for i in range(len(s_persons)):
                for j in range(i + 1, len(s_persons)):
                    p1 = s_persons[i]
                    p2 = s_persons[j]
                    add_rel(
                        p1["normalized_value"],
                        p1["raw_value"],
                        p2["normalized_value"],
                        p2["raw_value"],
                        "PERSON",
                        rel_type,
                        s_text,
                        conf=0.78,
                        method="ner",
                        span=(s_start, s_end),
                    )

    return relationships
