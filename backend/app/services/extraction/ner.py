import re
import json
from typing import Dict, Any, List, Set, Tuple, Optional

# Indian police & legal document terms to filter out from Person extraction
POLICE_RANKS = {
    "si", "insp", "inspector", "sub-inspector", "hc", "head constable",
    "const", "constable", "sho", "io", "dsp", "acp", "sp", "officer",
    "lady constable", "constables", "patrol"
}

HONORIFICS = {
    "shri", "smt", "mr", "mrs", "ms", "sri", "dr", "advocate", "accused",
    "suspect", "kingpin", "mastermind", "operator", "handler", "mule",
    "courier", "driver", "complainant", "victim", "informant", "person",
    "namely", "late", "occupant"
}

NON_PERSON_WORDS = {
    "uttar pradesh", "kanpur nagar", "kanpur", "lucknow", "noida", "delhi", "south-east delhi",
    "subhash marg", "shastri nagar", "tilak nagar", "nehru colony", "aishbagh", "ring road", "kanpur road",
    "police station", "police department", "district hospital", "magistrate", "case diary", "seizure memo",
    "search memo", "first information report", "first information contents", "particulars of property",
    "details of accused", "action taken", "articles seized", "items seized", "recorded by", "occupation",
    "self-employed driver", "inr", "rs", "sec 106", "sec 35", "bns 2023", "bnss 2023", "pmla 2002",
    "two unknown persons", "unknown persons", "unknown", "driver", "shopkeeper", "another person",
    "about", "entry", "statement", "referred", "gist", "date", "hours", "hrs", "court", "report",
    "checkpoint", "toll plaza", "fsl", "lucknow central", "kanpur north", "gautam buddh nagar",
    "economic offences", "nehrú colony", "anti-hawala cell", "anti hawala", "government",
    "handset", "inr recovered", "recovered", "says he knows caller", "ganga co-operative",
    "ganga co-operative bank", "kanpur north p.s.", "lucknow central p.s.", "delhi south-east p.s.",
    "south-east district", "mobile phone", "goods carrier", "cash packets", "foreign person"
}

# Regex to terminate trailing legal descriptors and prepositions from extracted names
NAME_TRIM_REGEX = re.compile(
    r'\b(?:under|sec(?:tion)?|bnss|bns|ipc|crpc|pmla|bsa|age|aged|years?|r\/o|s\/o|w\/o|d\/o|c\/o|'
    r'late|resident|address|near|from|dated|on|at|for|with|who|in|having|occupation|'
    r'alias|also\s+writes|full\s+name|introduced|through|signs\s+as|whose|saved|found|'
    r'was|is|to|a\s+person|another\s+person|shop|twice|after|giving|afterwards|registered|'
    r'recorded|visited|stated|produced|handed|remand|examination|conducted|seized|'
    r'entry|memo|diary|report|reported|procedure|recovered|says|knows|caller|sent|brought|belonging|'
    r'inserted|counted|received)\b.*',
    re.IGNORECASE
)

# Expanded patterns for Indian narrative legal text & criminal dossiers
PERSON_TITLE_PATTERN = re.compile(
    r'\b(?:Shri|Smt\.?|Mr\.?|Mrs\.?|Ms\.?|Sri|Dr\.?|advocate|accused(?:\s+person)?|suspect|kingpin|mastermind|operator|handler|mule|courier|driver|complainant|victim|informant|named|alias|a\.k\.a\.?|known\s+as|namely|s/o|d/o|w/o)\s+([A-Za-z]+(?:\s+[A-Za-z]+){1,3})\b',
    re.IGNORECASE
)

# All-caps names commonly found in police FIRs
ALL_CAPS_NAME_PATTERN = re.compile(
    r'\b([A-Z]{3,15}\s+[A-Z]{3,15}(?:\s+[A-Z]{3,15})?)\b'
)

# Role inference dictionary based on surrounding context
ROLE_KEYWORDS = {
    "kingpin": ["kingpin", "mastermind", "syndicate head", "boss", "gang leader", "main accused"],
    "suspect": ["accused", "suspect", "involved", "perpetrator", "culprit", "conspirator", "hawala", "arrested"],
    "operator": ["operator", "hawala dealer", "angadia", "money changer", "handler", "facilitator"],
    "mule": ["mule", "dummy account", "shell", "beneficiary", "cash courier", "runner", "courier", "driver"],
    "witness": ["witness", "witnesses", "neighbour", "bystander"],
    "victim": ["complainant", "victim", "informant", "aggrieved", "reporting person"],
    "police_officer": ["io", "sho", "sub-inspector", "inspector", "constable", "head constable", "investigating officer", "officer in charge", "patrol"]
}

def unwrap_text(txt: str) -> str:
    """
    Normalizes hard line wraps common in OCR, FIR, and court records.
    Merges broken sentence lines while preserving structural boundaries.
    """
    lines = txt.splitlines()
    unwrapped = []
    for line in lines:
        s = line.strip()
        if not s:
            unwrapped.append("")
            continue
        is_new_block = (
            re.match(r'^(?:\d+\.|\([a-z\d]+\)|Entry\s+dated|Case:|DOCUMENT:|FIRST|CASE|STATEMENT|Particulars|Details|Action|Officer|Investigating|Complainant|SEIZURE|SEARCH|Place|Acts|Name:|Address:|Occupation:|Recorded|Pending:)\b', s, re.IGNORECASE) or
            (unwrapped and unwrapped[-1].endswith(':'))
        )
        if unwrapped and not is_new_block and unwrapped[-1] != "":
            unwrapped[-1] += " " + s
        else:
            unwrapped.append(s)
    return "\n".join(unwrapped)

DISALLOWED_NAME_TOKENS = {
    "says", "knows", "caller", "whose", "recovered", "found", "seized", "handset",
    "carrier", "cartons", "goods", "cash", "inr", "notes", "mobile", "phone", "sim",
    "vehicle", "hatchback", "sedan", "bank", "co-operative", "cooperative", "entry",
    "notice", "memo", "report", "dated", "road", "street", "colony", "nagar", "marg"
}

def clean_person_name(raw: str) -> str:
    """Cleans legal prefixes, prepositions, numbers, and honorifics from a candidate name."""
    if not raw:
        return ""
    cleaned = NAME_TRIM_REGEX.sub('', raw).strip()
    cleaned = re.sub(r'^[(\d\s.)\-]+', '', cleaned)
    cleaned = re.sub(r'[",\':;()]+$', '', cleaned)
    cleaned = re.sub(r'^[",\':;()]+', '', cleaned)
    tokens = [
        t for t in cleaned.split()
        if t.lower().rstrip('.') not in POLICE_RANKS and t.lower().rstrip('.') not in HONORIFICS
    ]
    result = " ".join(tokens).strip()
    lowered = result.lower()
    if lowered in NON_PERSON_WORDS or len(result) < 3:
        return ""
    if any(tok.lower() in DISALLOWED_NAME_TOKENS for tok in tokens):
        return ""
    if any(org in lowered for org in ["p.s.", "police", "bank", "co-operative", "hospital", "court", "station"]):
        return ""
    return result

def infer_entity_role(context_sentence: str, candidate_name: str = "") -> str:
    """Infers operational role without falsely attributing police officers or victims as suspects."""
    s = context_sentence.lower()
    c_lower = candidate_name.lower()

    # Priority 1: Police Officers
    if any(k in s for k in ["investigating officer", "officer in charge", "recorded by", "seizing officer", "io:", "sho:"]) or \
       any(r in c_lower for r in ["si ", "insp", "constable", "inspector"]):
        return "police_officer"

    # Priority 2: Witnesses
    if any(k in s for k in ["witness", "witnesses", "neighbour"]):
        return "witness"

    # Priority 3: Victims
    if any(k in s for k in ["complainant", "victim", "informant", "reporting person"]):
        return "victim"

    # Priority 4: Criminal Roles
    for role in ["kingpin", "operator", "mule", "suspect"]:
        if any(kw in s for kw in ROLE_KEYWORDS[role]):
            return role

    return "person"

_nlp = None

def get_spacy_nlp():
    global _nlp
    if _nlp is None:
        try:
            import spacy
            _nlp = spacy.load("en_core_web_sm", disable=["parser", "tagger", "lemmatizer"])
        except Exception:
            _nlp = False
    return _nlp if _nlp is not False else None

def extract_legal_entities(text: str, page_or_para: str, base_char_offset: int = 0) -> List[Dict[str, Any]]:
    """
    Dedicated extraction engine for Indian legal FIRs, Case Diaries,
    Disclosure Statements, and Search/Seizure memos.
    """
    results: List[Dict[str, Any]] = []
    seen_norms: Set[str] = set()
    police_officer_norms: Set[str] = set()

    def add_entity(name: str, role: str, e_type: str = "PERSON", conf: float = 0.92, method: str = "legal_police_regex"):
        c = clean_person_name(name)
        if not c:
            return
        norm = c.lower()
        if norm in police_officer_norms and role != "police_officer":
            return
        if norm in seen_norms:
            return
        seen_norms.add(norm)
        if role == "police_officer":
            police_officer_norms.add(norm)

        # Check if company or syndicate organization
        if e_type == "PERSON" and any(ind in c.lower() for ind in ["llp", "ltd", "limited", "pvt", "exports", "enterprises", "agency", "bank"]):
            e_type = "ORGANIZATION"
            if role == "suspect":
                role = "syndicate_entity"

        idx = text.find(name)
        st = base_char_offset + (idx if idx >= 0 else 0)
        en = st + len(name)
        results.append({
            "entity_type": e_type,
            "raw_value": c,
            "normalized_value": norm,
            "char_span_start": st,
            "char_span_end": en,
            "page_or_paragraph": page_or_para,
            "confidence": conf,
            "method": method,
            "role": role
        })

    # 1. Police Officers from document headers
    for m in re.finditer(r'\b(?:IO|SHO|Investigating\s+Officer|Officer\s+in\s+charge|Complainant|Recorded\s+by|Seizing\s+officer)\s*[:\-]\s*(?:(?:SI|Insp\.?|Inspector|Sub-Inspector|HC|Const\.?)\s+)?([A-Za-z\s.]+?)(?=[,;\n]|\s+IO|\s+SHO|\s*\(|\s+in\s+presence|$)', text, re.IGNORECASE):
        add_entity(m.group(1), role="police_officer")

    for m in re.finditer(r'\b(?:SI|Insp\.?|Inspector|Sub-Inspector|Head\s+Constable|HC|Const\.?|Constable)\s+([A-Za-z]+(?:\s+[A-Za-z]+){1,3})\b', text, re.IGNORECASE):
        add_entity(m.group(1), role="police_officer")

    # 2. Accused headers: Details of accused, STATEMENT OF ACCUSED, Occupant present, Seized from
    for m in re.finditer(r'(?:Details\s+of\s+accused(?:\s*\([^)]*\))?|STATEMENT\s+OF\s+ACCUSED[^\n]*\n[^\n]*Name|Person\s+from\s+whom\s+seized|Occupant\s+present)\s*[:\-]?\s*([^\n]+)', text, re.IGNORECASE):
        line = m.group(1).strip()
        parts = re.split(r'\(\d+\)|\bAnother\s+person\b|,|\n', line)
        for part in parts:
            add_entity(part, role="suspect")

    # 3. Explicit Arrested / Driver mentions
    for m in re.finditer(r'\b(?:Arrested\s+accused|The\s+driver)\s+([A-Za-z\s.]+?)(?=\s+under|\s+alias|\s+was|\s+s\/o|\s+r\/o|,|\n)', text, re.IGNORECASE):
        add_entity(m.group(1), role="suspect")

    # 4. Nicknames in quotes / informal syndicate aliases: "Mukesh bhai", "Sandeep bhai"
    for m in re.finditer(r'["\']([A-Za-z\s]+?\s+(?:bhai|gang|seth|chacha|mama|don|pandit|ustad|babu))["\']|\b(?:caller\s+only\s+as|known\s+as|referred\s+to\s+as|meant\s+for)\s+["\']([^"\']+)["\']', text, re.IGNORECASE):
        nick = m.group(1) or m.group(2)
        add_entity(nick, role="suspect")

    # 5. Aliases: alias P. Chauhan, alias R. Yadav
    for m in re.finditer(r'\balias\s+([A-Za-z.\s]{2,20}?)(?=[,;\n]|\s+age|\s+s\/o|\s+r\/o|\s+was|\(|$|\s+because)', text, re.IGNORECASE):
        add_entity(m.group(1), role="suspect")

    # 6. FIR cross-references: FIR 0519/2026 (Imran Quraishi)
    for m in re.finditer(r'\bFIR\s*[A-Z0-9\/\-]+\s*\(\s*([A-Za-z\s.]+?)\s*\)', text, re.IGNORECASE):
        add_entity(m.group(1), role="suspect")

    # 7. Witnesses
    for m in re.finditer(r'\bwitnesses\s+([A-Za-z\s.]+?)\s+and\s+([A-Za-z\s.]+?)(?=[,.\n]|$)', text, re.IGNORECASE):
        add_entity(m.group(1), role="witness")
        add_entity(m.group(2), role="witness")
    for m in re.finditer(r'\bIndependent\s+witnesses:\s*\(1\)\s*([A-Za-z\s.]+?)[,;]\s*\(2\)\s*([A-Za-z\s.]+?)(?=[,.\n]|$)', text, re.IGNORECASE):
        add_entity(m.group(1), role="witness")
        add_entity(m.group(2), role="witness")
    for m in re.finditer(r'\bneighbour,\s+([A-Za-z\s.]+?),', text, re.IGNORECASE):
        add_entity(m.group(1), role="witness")

    # 8. Complainants (Victims)
    for m in re.finditer(r'\bComplainant:\s*(?:\([a-z]\)\s*Name:\s*)?([A-Za-z\s.]+?)(?=[,.\n]|\s*\([a-z]\)|$)', text, re.IGNORECASE):
        c_name = m.group(1).strip()
        if not any(r["normalized_value"] == c_name.lower() and r["role"] == "police_officer" for r in results):
            add_entity(c_name, role="victim")
    for m in re.finditer(r'\bcomplainant,\s*([A-Za-z\s.]+?),', text, re.IGNORECASE):
        add_entity(m.group(1), role="victim")

    return results

def extract_ner_entities(
    text: str,
    page_or_para: str,
    base_char_offset: int = 0,
    existing_spans: List[Tuple[int, int]] = None
) -> List[Dict[str, Any]]:
    """
    Extracts criminal entities, accused, witnesses, police officers, and organizations
    using a hybrid strategy: Legal Domain Patterns + spaCy NER + Title heuristics.
    """
    results: List[Dict[str, Any]] = []
    occupied_spans = list(existing_spans or [])

    def overlaps_any(start: int, end: int) -> bool:
        for s, e in occupied_spans:
            if not (end <= s or start >= e):
                return True
        return False

    clean_unwrapped = unwrap_text(text)

    # 1. Primary: Domain-specific legal police document entity extraction
    legal_entities = extract_legal_entities(clean_unwrapped, page_or_para, base_char_offset)
    for le in legal_entities:
        results.append(le)
        occupied_spans.append((le["char_span_start"], le["char_span_end"]))

    seen_norms = {e["normalized_value"] for e in results}

    # 2. Secondary: Capitalized / Title heuristic names (high precision)
    for m in PERSON_TITLE_PATTERN.finditer(clean_unwrapped):
        raw_name = m.group(1).strip()
        cleaned_name = clean_person_name(raw_name)
        start = base_char_offset + m.start(1)
        end = base_char_offset + m.end(1)

        if cleaned_name and not overlaps_any(start, end):
            norm = cleaned_name.lower()
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
                    "confidence": 0.85,
                    "method": "title_heuristic",
                    "role": detected_role
                })

    # 3. Tertiary: spaCy Named Entity Recognition
    nlp = get_spacy_nlp()
    if nlp:
        try:
            doc = nlp(clean_unwrapped)
            for ent in doc.ents:
                if ent.label_ in ["PERSON", "ORG"]:
                    start = base_char_offset + ent.start_char
                    end = base_char_offset + ent.end_char
                    raw = ent.text.strip()
                    cleaned_name = clean_person_name(raw)

                    if cleaned_name and not overlaps_any(start, end):
                        norm = cleaned_name.lower()
                        if norm not in seen_norms:
                            seen_norms.add(norm)
                            window_start = max(0, ent.start_char - 80)
                            window_end = min(len(clean_unwrapped), ent.end_char + 80)
                            context_snippet = clean_unwrapped[window_start:window_end]
                            detected_role = infer_entity_role(context_snippet, cleaned_name)

                            org_indicators = ["ltd", "limited", "bank", "pvt", "corp", "corporation", "inc", "trust", "hospital", "police", "agency", "llp", "exports"]
                            is_org = (ent.label_ == "ORG") or any(ind in cleaned_name.lower() for ind in org_indicators)

                            occupied_spans.append((start, end))
                            results.append({
                                "entity_type": "ORGANIZATION" if is_org else "PERSON",
                                "raw_value": cleaned_name.title(),
                                "normalized_value": norm,
                                "char_span_start": start,
                                "char_span_end": end,
                                "page_or_paragraph": page_or_para,
                                "confidence": 0.85,
                                "method": "spacy_ner",
                                "role": "syndicate_entity" if (is_org and detected_role == "suspect") else detected_role
                            })
        except Exception:
            pass

    # 4. Quaternary: ALL CAPS names
    EXCLUDED_CAPS = {"POLICE", "STATION", "DELHI", "MUMBAI", "INDIA", "SECTION", "REPORT", "COURT", "OFFICER", "FIRST", "CASE", "DIARY", "MEMO"}
    for m in ALL_CAPS_NAME_PATTERN.finditer(clean_unwrapped):
        raw_name = m.group(1).strip()
        tokens = [t for t in raw_name.split() if t not in EXCLUDED_CAPS]
        if len(tokens) >= 2:
            cleaned_name = clean_person_name(" ".join(tokens))
            start = base_char_offset + m.start(1)
            end = base_char_offset + m.end(1)
            if cleaned_name and not overlaps_any(start, end):
                norm = cleaned_name.lower()
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
    Extracts criminal network relationships between Persons, Phones, Vehicles,
    Bank Accounts, and FIRs based on legal sentence correlation and co-occurrence.
    """
    relationships: List[Dict[str, Any]] = []
    seen_pairs: Set[Tuple[str, str, str]] = set()

    clean_txt = unwrap_text(text)

    persons = [e for e in extracted_entities if e["entity_type"] in ["PERSON", "ORGANIZATION"]]
    targets = [e for e in extracted_entities if e["entity_type"] in ["PHONE", "BANK_ACCOUNT", "VEHICLE", "FIR"]]

    def add_rel(src: str, src_disp: str, tgt: str, tgt_disp: str, tgt_type: str, rel_type: str, sentence: str, conf: float = 0.88):
        key = (src, tgt, rel_type)
        if key in seen_pairs or src == tgt:
            return
        seen_pairs.add(key)
        rel_data = {
            "source": src,
            "source_display": src_disp,
            "target": tgt,
            "target_display": tgt_disp,
            "target_type": tgt_type,
            "relationship_type": rel_type,
            "sentence": sentence[:200]
        }
        relationships.append({
            "entity_type": "RELATIONSHIP",
            "raw_value": f"{src_disp} {rel_type} {tgt_disp}",
            "normalized_value": json.dumps(rel_data),
            "char_span_start": 0,
            "char_span_end": 0,
            "page_or_paragraph": page_or_para,
            "confidence": conf,
            "method": "domain_cooccurrence"
        })

    # 1. Alias relationships (e.g. Rakesh Yadav alias R. Yadav, Pappu Chauhan alias P. Chauhan)
    for p1 in persons:
        for p2 in persons:
            if p1["normalized_value"] != p2["normalized_value"]:
                r1, r2 = re.escape(p1['raw_value']), re.escape(p2['raw_value'])
                if re.search(rf"\b{r1}\b[^\n.]{{0,40}}\balias\b[^\n.]{{0,40}}\b{r2}\b", clean_txt, re.IGNORECASE) or \
                   re.search(rf"\b{r1}\b[^\n.]{{0,50}}\(also\s+writes[^\n.]{{0,40}}\b{r2}\b", clean_txt, re.IGNORECASE):
                    add_rel(p1["normalized_value"], p1["raw_value"], p2["normalized_value"], p2["raw_value"], "PERSON", "ALIAS_OF", "Declared alias", 0.95)

    # 2. Driver / Operator to Vehicle (e.g. Pappu Chauhan drives UP43UK7691, Rakesh Yadav drives DL30HU4086)
    vehicles = [e for e in targets if e["entity_type"] == "VEHICLE"]
    for p in persons:
        if p.get("role") in ["police_officer", "witness", "victim"]:
            continue
        for v in vehicles:
            r_p, r_v = re.escape(p['raw_value']), re.escape(v['raw_value'])
            if re.search(rf"\b{r_p}\b[^\n.]{{0,120}}\b{r_v}\b|\b{r_v}\b[^\n.]{{0,120}}\b{r_p}\b", clean_txt, re.IGNORECASE):
                add_rel(p["normalized_value"], p["raw_value"], v["normalized_value"], v["raw_value"], "VEHICLE", "DRIVES", f"Operated vehicle {v['raw_value']}", 0.90)

    # 3. Person to Phone (e.g. Mukesh bhai uses 6029787534, Pappu Chauhan uses 8475177992)
    phones = [e for e in targets if e["entity_type"] == "PHONE"]
    for p in persons:
        if p.get("role") in ["police_officer", "witness", "victim"]:
            continue
        for ph in phones:
            r_p, r_ph = re.escape(p['raw_value']), re.escape(ph['raw_value'])
            if re.search(rf"\b{r_p}\b[^\n.]{{0,120}}\b{r_ph}\b|\b{r_ph}\b[^\n.]{{0,120}}\b{r_p}\b", clean_txt, re.IGNORECASE):
                add_rel(p["normalized_value"], p["raw_value"], ph["normalized_value"], ph["raw_value"], "PHONE", "USES", f"Associated handset/SIM {ph['raw_value']}", 0.92)

    # 4. Person to Bank Account
    accounts = [e for e in targets if e["entity_type"] == "BANK_ACCOUNT"]
    for p in persons:
        if p.get("role") in ["police_officer", "witness"]:
            continue
        for acc in accounts:
            r_p, r_acc = re.escape(p['raw_value']), re.escape(acc['raw_value'])
            if re.search(rf"\b{r_p}\b[^\n.]{{0,140}}\b{r_acc}\b|\b{r_acc}\b[^\n.]{{0,140}}\b{r_p}\b", clean_txt, re.IGNORECASE):
                rel = "OWNS" if p["entity_type"] == "ORGANIZATION" or "held in the name" in clean_txt.lower() else "OPERATES"
                add_rel(p["normalized_value"], p["raw_value"], acc["normalized_value"], acc["raw_value"], "BANK_ACCOUNT", rel, f"Bank instrument {acc['raw_value']}", 0.88)

    # 5. Cash courier to coordinator / handler (e.g. meant for Sandeep bhai, calls from Mukesh bhai)
    for p1 in persons:
        if p1.get("role") in ["police_officer", "witness", "victim"]:
            continue
        for p2 in persons:
            if p2.get("role") in ["police_officer", "witness", "victim"]:
                continue
            if p1["normalized_value"] != p2["normalized_value"]:
                r1, r2 = re.escape(p1['raw_value']), re.escape(p2['raw_value'])
                if re.search(rf"\b{r1}\b[^\n.]{{0,150}}(?:meant for|cash was meant for|calls me|caller only as|offered me|work of carrying)\b[^\n.]{{0,150}}\b{r2}\b", clean_txt, re.IGNORECASE) or \
                   re.search(rf"\b{r2}\b[^\n.]{{0,150}}(?:offered|told)\b[^\n.]{{0,150}}\b{r1}\b", clean_txt, re.IGNORECASE):
                    add_rel(p1["normalized_value"], p1["raw_value"], p2["normalized_value"], p2["raw_value"], "PERSON", "COURIER_FOR", "Coordinated delivery & fund transfer", 0.90)

    # 6. Person mentioned in FIR
    firs = [e for e in targets if e["entity_type"] == "FIR"]
    for p in persons:
        for f in firs:
            r_p, r_f = re.escape(p['raw_value']), re.escape(f['raw_value'])
            if re.search(rf"\b{r_f}\b[^\n.]{{0,80}}\b{r_p}\b|\b{r_p}\b[^\n.]{{0,80}}\b{r_f}\b", clean_txt, re.IGNORECASE):
                add_rel(p["normalized_value"], p["raw_value"], f["normalized_value"], f["raw_value"], "FIR", "MENTIONED_IN", f"Cited in FIR {f['raw_value']}", 0.95)

    # 7. Sentence-level general co-occurrence (with protected periods and joined lines)
    # Tokenize sentences safely avoiding dot-splits on legal abbreviations
    s_safe = re.sub(r'\b(P\.S\.|SI|Insp\.|Sec\.|Rs\.|No\.|Dr\.|Mr\.|Mrs\.|Ms\.|Shri|Smt\.|[A-Z]\.)', lambda m: m.group(0).replace('.', '@@DOT@@'), clean_txt)
    raw_sentences = re.split(r'[.!?\n]+', s_safe)

    for s_raw in raw_sentences:
        s_text = s_raw.replace('@@DOT@@', '.').strip()
        if len(s_text) < 10:
            continue

        s_persons = [p for p in persons if p["raw_value"].lower() in s_text.lower()]
        s_targets = [t for t in targets if t["raw_value"].lower() in s_text.lower() or t["normalized_value"].lower() in s_text.lower()]

        for p in s_persons:
            is_cop = p.get("role") == "police_officer"
            for t in s_targets:
                if is_cop:
                    rel_type = "INVESTIGATES" if t["entity_type"] in ["PHONE", "VEHICLE", "BANK_ACCOUNT"] else "FILED"
                else:
                    rel_type = "USES" if t["entity_type"] == "PHONE" else (
                        "DRIVES" if t["entity_type"] == "VEHICLE" else (
                            "MENTIONED_IN" if t["entity_type"] == "FIR" else "OWNS"
                        )
                    )
                add_rel(p["normalized_value"], p["raw_value"], t["normalized_value"], t["raw_value"], t["entity_type"], rel_type, s_text, 0.80)

        if len(s_persons) >= 2:
            s_lower = s_text.lower()
            rel_type = "CONNECTED_TO"
            if any(w in s_lower for w in ["transfer", "sent", "paid", "remitted", "rtgs"]):
                rel_type = "TRANSFERRED_TO"
            elif any(w in s_lower for w in ["along with", "associate", "accomplice", "co-accused", "syndicate"]):
                rel_type = "ACCOMPLICE_OF"
            elif any(w in s_lower for w in ["call", "contact", "communicated", "caller"]):
                rel_type = "COMMUNICATED_WITH"

            for i in range(len(s_persons)):
                for j in range(i + 1, len(s_persons)):
                    p1 = s_persons[i]
                    p2 = s_persons[j]
                    add_rel(p1["normalized_value"], p1["raw_value"], p2["normalized_value"], p2["raw_value"], "PERSON", rel_type, s_text, 0.78)

    return relationships
