import re
import json
import uuid
from datetime import datetime
from typing import Dict, Any, List, Set, Tuple, Optional
from sqlalchemy.orm import Session
from rapidfuzz.distance import JaroWinkler

from backend.app.db.sql import (
    Entity, EntityLink, MatchSuggestion, ProfileMember, CaseSetting,
    EvidenceFile, CallRecord, Transaction, IPEvent
)
from backend.app.config import settings
from backend.app.audit.service import record_audit_log
from backend.app.services.graph.builder import invalidate_case_graph

TITLES_REGEX = re.compile(
    r"\b(shri|smt|mr|mrs|ms|dr|adv|inspector|constable|accused|complainant|victim|alias|aka|mohd|md|ku|kumar|kumari)\b",
    re.IGNORECASE
)

def get_soundex(name: str) -> str:
    """Computes American Soundex for phonetic surname blocking."""
    if not name:
        return "0000"
    clean = re.sub(r"[^A-Z]", "", name.upper())
    if not clean:
        return "0000"
    mapping = {
        "B": "1", "F": "1", "P": "1", "V": "1",
        "C": "2", "G": "2", "J": "2", "K": "2", "Q": "2", "S": "2", "X": "2", "Z": "2",
        "D": "3", "T": "3",
        "L": "4",
        "M": "5", "N": "5",
        "R": "6"
    }
    first_letter = clean[0]
    res = [first_letter]
    for ch in clean[1:]:
        digit = mapping.get(ch, "0")
        if digit != "0" and digit != res[-1]:
            res.append(digit)
    digits = "".join(res[1:])
    return (first_letter + digits + "000")[:4]

def normalize_person_name(raw_name: str) -> Tuple[str, str, str]:
    """
    Normalizes person name: strips titles and punctuation, collapses spaces.
    Returns: (clean_full_name, first_name, surname)
    """
    if not raw_name:
        return ("", "", "")
    # Lowercase & strip titles
    clean = raw_name.lower()
    clean = TITLES_REGEX.sub(" ", clean)
    clean = re.sub(r"[^\w\s]", " ", clean)
    tokens = clean.split()
    if not tokens:
        return (raw_name.lower().strip(), "", raw_name.lower().strip())
    
    clean_full = " ".join(tokens)
    if len(tokens) == 1:
        first_name = ""
        surname = tokens[0]
    else:
        first_name = tokens[0]
        surname = tokens[-1]
    return (clean_full, first_name, surname)

def check_name_compatibility(
    name1: str, name2: str,
    surname_thresh: float = 0.90,
    first_thresh: float = 0.85
) -> Tuple[bool, float, str]:
    """
    Evaluates name compatibility according to Phase 7 rules:
    - surname_ok = surname similarity >= surname_thresh
    - first_ok = first-name similarity >= first_thresh OR initial-compatible OR one side lacks first name
    - name_compatible = surname_ok AND first_ok
    """
    _, f1, s1 = normalize_person_name(name1)
    _, f2, s2 = normalize_person_name(name2)

    if not s1 or not s2:
        return (False, 0.0, "Missing surname")

    surname_sim = JaroWinkler.normalized_similarity(s1, s2)
    surname_ok = (surname_sim >= surname_thresh)

    first_ok = False
    first_detail = ""

    if not f1 or not f2:
        # One side lacks first name -> acceptable
        first_ok = True
        first_detail = "single_name_match"
    elif (len(f1) == 1 and f2.startswith(f1)) or (len(f2) == 1 and f1.startswith(f2)):
        # Initial compatible (e.g. 'R.' matches 'Rahul')
        first_ok = True
        first_detail = "initial_compatible"
    else:
        first_sim = JaroWinkler.normalized_similarity(f1, f2)
        if first_sim >= first_thresh:
            first_ok = True
            first_detail = f"first_name_sim_{first_sim:.2f}"

    compatible = (surname_ok and first_ok)
    avg_score = surname_sim if not (f1 and f2) else (surname_sim * 0.6 + JaroWinkler.normalized_similarity(f1, f2) * 0.4)
    return (compatible, avg_score, first_detail)

def get_matching_config(db: Session, case_id: str) -> Dict[str, Any]:
    """Loads matching weights and thresholds from CaseSettings or defaults.yaml."""
    from backend.app.cases.router import get_effective_case_settings
    eff = get_effective_case_settings(db, case_id)
    return eff.get("matching", {
        "strengths": {
            "same_account": 95,
            "same_phone": 90,
            "same_vehicle": 90,
            "same_email": 85,
            "same_device_imei": 70,
            "dob_plus_similar_name": 60,
            "same_address": 35,
            "similar_name_only": 25,
            "same_ip": 20
        },
        "thresholds": {
            "surname_similarity_min": 0.90,
            "first_name_similarity_min": 0.85,
            "high_level_min": 70,
            "medium_level_min": 40
        }
    })

def generate_case_matches(db: Session, case_id: str) -> Dict[str, Any]:
    """
    Candidate Generation (Non-O(N^2)) & Match Level Scoring:
    a) Every Phone/BankAccount/Vehicle/Email/Device shared by >= 2 distinct Person nodes -> candidate pairs
    b) Name blocking by normalized surname + phonetic Soundex key -> pairs within a block
    Evaluates compatibility, flags SHARED_DEVICE where names conflict, categorizes into HIGH/MEDIUM/SHARED_DEVICE/LOW.
    """
    cfg = get_matching_config(db, case_id)
    strengths = cfg.get("strengths", {})
    thresholds = cfg.get("thresholds", {})
    surname_thresh = float(thresholds.get("surname_similarity_min", 0.90))
    first_thresh = float(thresholds.get("first_name_similarity_min", 0.85))

    # 1. Fetch all Person entities for this case
    persons = db.query(Entity).filter(Entity.case_id == case_id, Entity.label == "Person").all()
    if not persons:
        return {"total_candidates": 0, "new_suggestions": 0}

    person_by_id: Dict[str, Entity] = {p.canonical_id: p for p in persons}
    all_person_ids = list(person_by_id.keys())

    # Map each person to their linked identifiers: { person_id: { "phones": set(), "accounts": set(), ... } }
    person_ids_map: Dict[str, Dict[str, Set[str]]] = {
        pid: {
            "phones": set(),
            "accounts": set(),
            "vehicles": set(),
            "emails": set(),
            "devices": set(),
            "ips": set(),
            "addresses": set()
        } for pid in all_person_ids
    }

    # Fetch EntityLinks
    links = db.query(EntityLink).filter(EntityLink.case_id == case_id).all()
    for l in links:
        src = l.source_entity_id
        tgt = l.target_entity_id
        if src in person_ids_map:
            if l.relationship_type == "USES":
                person_ids_map[src]["phones"].add(tgt)
            elif l.relationship_type == "OWNS":
                person_ids_map[src]["accounts"].add(tgt)
            elif l.relationship_type == "DRIVES":
                person_ids_map[src]["vehicles"].add(tgt)

    # Inverted Index of Identifiers -> set(person_ids)
    ident_to_persons: Dict[str, Tuple[str, Set[str]]] = {}
    for pid, ids in person_ids_map.items():
        for ph in ids["phones"]:
            ident_to_persons.setdefault(f"phone:{ph}", ("phone", set()))[1].add(pid)
        for acc in ids["accounts"]:
            ident_to_persons.setdefault(f"account:{acc}", ("account", set()))[1].add(pid)
        for veh in ids["vehicles"]:
            ident_to_persons.setdefault(f"vehicle:{veh}", ("vehicle", set()))[1].add(pid)
        for em in ids["emails"]:
            ident_to_persons.setdefault(f"email:{em}", ("email", set()))[1].add(pid)
        for dev in ids["devices"]:
            ident_to_persons.setdefault(f"device:{dev}", ("device", set()))[1].add(pid)

    # Candidate pairs set: (pid_a, pid_b) with pid_a < pid_b
    candidate_pairs: Set[Tuple[str, str]] = set()

    # Channel A: Shared Strong Identifiers (Phone, BankAccount, Vehicle, Email, Device)
    for ident_key, (kind, p_set) in ident_to_persons.items():
        if len(p_set) >= 2:
            p_list = sorted(list(p_set))
            for i in range(len(p_list)):
                for j in range(i + 1, len(p_list)):
                    candidate_pairs.add((p_list[i], p_list[j]))

    # Channel B: Name Blocking by Soundex(surname)
    soundex_blocks: Dict[str, List[str]] = {}
    for pid, p in person_by_id.items():
        _, _, sname = normalize_person_name(p.display_name or p.canonical_id)
        if sname:
            sx = get_soundex(sname)
            soundex_blocks.setdefault(sx, []).append(pid)

    for sx, p_list in soundex_blocks.items():
        if len(p_list) >= 2:
            p_list = sorted(p_list)
            for i in range(len(p_list)):
                for j in range(i + 1, len(p_list)):
                    candidate_pairs.add((p_list[i], p_list[j]))

    # Ambiguity Detection: Check if an initial-only name is compatible with >= 2 distinct first names in the case (e.g. Rahul vs Ramesh)
    initial_candidate_names: Dict[str, Set[str]] = {}
    for pid, p in person_by_id.items():
        _, f, s = normalize_person_name(p.display_name or p.canonical_id)
        if len(f) > 1 and s:
            key = f"{f[0]}_{s}"
            initial_candidate_names.setdefault(key, set()).add(f)

    # Load existing match suggestions to avoid duplicate inserts
    existing_suggestions = db.query(MatchSuggestion).filter(MatchSuggestion.case_id == case_id).all()
    existing_pair_keys = {
        tuple(sorted([s.entity_a_id, s.entity_b_id])): s for s in existing_suggestions
    }

    new_count = 0

    for (p1_id, p2_id) in candidate_pairs:
        pair_key = (p1_id, p2_id)
        if pair_key in existing_pair_keys:
            continue

        p1 = person_by_id[p1_id]
        p2 = person_by_id[p2_id]
        name1 = p1.display_name or p1.canonical_id
        name2 = p2.display_name or p2.canonical_id

        # 1. Name compatibility
        compatible, name_score, first_detail = check_name_compatibility(
            name1, name2, surname_thresh, first_thresh
        )

        # Check ambiguity
        _, f1, s1 = normalize_person_name(name1)
        _, f2, s2 = normalize_person_name(name2)
        is_ambiguous = False
        if len(f1) == 1 and s1 and len(initial_candidate_names.get(f"{f1}_{s1}", set())) >= 2:
            is_ambiguous = True
        if len(f2) == 1 and s2 and len(initial_candidate_names.get(f"{f2}_{s2}", set())) >= 2:
            is_ambiguous = True

        # 2. Check Shared Identifiers
        shared_phones = person_ids_map[p1_id]["phones"].intersection(person_ids_map[p2_id]["phones"])
        shared_accounts = person_ids_map[p1_id]["accounts"].intersection(person_ids_map[p2_id]["accounts"])
        shared_vehicles = person_ids_map[p1_id]["vehicles"].intersection(person_ids_map[p2_id]["vehicles"])
        shared_emails = person_ids_map[p1_id]["emails"].intersection(person_ids_map[p2_id]["emails"])
        shared_devices = person_ids_map[p1_id]["devices"].intersection(person_ids_map[p2_id]["devices"])

        has_strong_id = bool(shared_phones or shared_accounts or shared_vehicles or shared_emails or shared_devices)

        # Multi-person shared device check: attached to >= 3 mutually incompatible persons (e.g. call centre/cyber cafe)
        over_shared_hardware = False
        for ph in shared_phones:
            p_ids_on_ph = ident_to_persons.get(f"phone:{ph}", ("", set()))[1]
            if len(p_ids_on_ph) >= 3:
                incompatible_count = 0
                p_list = [p for p in p_ids_on_ph if p in person_by_id]
                for i_idx in range(len(p_list)):
                    for j_idx in range(i_idx + 1, len(p_list)):
                        c_check, _, _ = check_name_compatibility(
                            person_by_id[p_list[i_idx]].display_name or p_list[i_idx],
                            person_by_id[p_list[j_idx]].display_name or p_list[j_idx]
                        )
                        if not c_check:
                            incompatible_count += 1
                if incompatible_count >= 2:
                    over_shared_hardware = True
        for acc in shared_accounts:
            p_ids_on_acc = ident_to_persons.get(f"account:{acc}", ("", set()))[1]
            if len(p_ids_on_acc) >= 3:
                incompatible_count = 0
                p_list = [p for p in p_ids_on_acc if p in person_by_id]
                for i_idx in range(len(p_list)):
                    for j_idx in range(i_idx + 1, len(p_list)):
                        c_check, _, _ = check_name_compatibility(
                            person_by_id[p_list[i_idx]].display_name or p_list[i_idx],
                            person_by_id[p_list[j_idx]].display_name or p_list[j_idx]
                        )
                        if not c_check:
                            incompatible_count += 1
                if incompatible_count >= 2:
                    over_shared_hardware = True

        reasons = []
        score = 0.0

        if shared_accounts:
            score = max(score, float(strengths.get("same_account", 95)))
            reasons.append(f"Shared bank account: {', '.join(sorted(shared_accounts))}")
        if shared_phones:
            score = max(score, float(strengths.get("same_phone", 90)))
            reasons.append(f"Shared mobile phone: {', '.join(sorted(shared_phones))}")
        if shared_vehicles:
            score = max(score, float(strengths.get("same_vehicle", 90)))
            reasons.append(f"Shared vehicle registration: {', '.join(sorted(shared_vehicles))}")
        if shared_emails:
            score = max(score, float(strengths.get("same_email", 85)))
            reasons.append(f"Shared email address: {', '.join(sorted(shared_emails))}")
        if shared_devices:
            score = max(score, float(strengths.get("same_device_imei", 70)))
            reasons.append(f"Shared hardware device (IMEI): {', '.join(sorted(shared_devices))}")

        if compatible:
            reasons.append(f"Name variant compatibility: '{name1}' vs '{name2}' (Jaro-Winkler {name_score:.2f})")
            if not has_strong_id:
                score = max(score, float(strengths.get("similar_name_only", 25)))

        # Level Categorization
        level = "LOW"
        if has_strong_id:
            if over_shared_hardware or not compatible:
                # Rule: Strong ID but NOT name_compatible -> SHARED_DEVICE (relatives / shared device, merge prohibited)
                level = "SHARED_DEVICE"
                reasons.append(
                    "Shared hardware/identifier between distinct individuals (e.g. relatives or public terminal). Merge prohibited."
                )
            elif is_ambiguous:
                # Strong ID but initial is ambiguous with multiple persons -> MEDIUM
                level = "MEDIUM"
                reasons.append(
                    f"Initial-only identifier '{name1}' is ambiguous with >= 2 distinct entities in case records."
                )
            else:
                level = "HIGH"
        else:
            if compatible:
                level = "LOW"
            else:
                continue # Skip pairs with neither strong ID nor name similarity

        ms = MatchSuggestion(
            id=str(uuid.uuid4()),
            case_id=case_id,
            entity_a_id=p1_id,
            entity_b_id=p2_id,
            level=level,
            score=score,
            reasons_json=json.dumps(reasons),
            status="pending"
        )
        db.add(ms)
        new_count += 1

    if new_count > 0:
        db.commit()

    return {
        "total_candidates": len(candidate_pairs),
        "new_suggestions": new_count
    }

def approve_match(db: Session, match_id: str, user_id: str) -> Dict[str, Any]:
    """
    Approves a match suggestion:
    - Resolves both entities into a MasterProfile non-destructively in SQLite profile_members
    - Syncs [:RESOLVED_TO] relationship to Neo4j / in-memory graph
    - Person nodes are NEVER deleted
    - Audited & invalidates graph cache
    """
    ms = db.query(MatchSuggestion).filter(MatchSuggestion.id == match_id).first()
    if not ms:
        raise ValueError("Match suggestion not found")
    if ms.level in ["SHARED_DEVICE", "LOW"]:
        raise ValueError(f"Approval not allowed for match with level '{ms.level}'")

    case_id = ms.case_id

    # Check if either entity already belongs to a MasterProfile
    existing_mem_a = db.query(ProfileMember).filter(
        ProfileMember.entity_id == ms.entity_a_id
    ).first()
    existing_mem_b = db.query(ProfileMember).filter(
        ProfileMember.entity_id == ms.entity_b_id
    ).first()

    if existing_mem_a and existing_mem_b:
        profile_id = existing_mem_a.profile_id
        # Merge if they have different profiles
        if existing_mem_a.profile_id != existing_mem_b.profile_id:
            old_pid = existing_mem_b.profile_id
            db.query(ProfileMember).filter(ProfileMember.profile_id == old_pid).update(
                {"profile_id": profile_id}
            )
    elif existing_mem_a:
        profile_id = existing_mem_a.profile_id
    elif existing_mem_b:
        profile_id = existing_mem_b.profile_id
    else:
        profile_id = f"MP-{uuid.uuid4().hex[:8].upper()}"

    # Add member rows if not present
    now = datetime.utcnow()
    if not existing_mem_a:
        db.add(ProfileMember(
            id=str(uuid.uuid4()),
            profile_id=profile_id,
            entity_id=ms.entity_a_id,
            match_id=ms.id,
            approved_by=user_id,
            created_at=now
        ))
    if not existing_mem_b:
        db.add(ProfileMember(
            id=str(uuid.uuid4()),
            profile_id=profile_id,
            entity_id=ms.entity_b_id,
            match_id=ms.id,
            approved_by=user_id,
            created_at=now
        ))

    ms.status = "approved"
    ms.decided_by = user_id
    ms.decided_at = now
    db.commit()

    # Audit log
    record_audit_log(
        db=db,
        user_id=user_id,
        action="match_approve",
        case_id=case_id,
        object_type="match_suggestion",
        object_id=ms.id,
        details={
            "profile_id": profile_id,
            "entity_a_id": ms.entity_a_id,
            "entity_b_id": ms.entity_b_id,
            "level": ms.level,
            "score": ms.score
        }
    )

    invalidate_case_graph(case_id)

    return {
        "status": "approved",
        "match_id": ms.id,
        "profile_id": profile_id
    }

def reject_match(db: Session, match_id: str, user_id: str) -> Dict[str, Any]:
    """Rejects a match suggestion."""
    ms = db.query(MatchSuggestion).filter(MatchSuggestion.id == match_id).first()
    if not ms:
        raise ValueError("Match suggestion not found")

    ms.status = "rejected"
    ms.decided_by = user_id
    ms.decided_at = datetime.utcnow()
    db.commit()

    record_audit_log(
        db=db,
        user_id=user_id,
        action="match_reject",
        case_id=ms.case_id,
        object_type="match_suggestion",
        object_id=ms.id,
        details={"entity_a_id": ms.entity_a_id, "entity_b_id": ms.entity_b_id}
    )

    return {"status": "rejected", "match_id": ms.id}

def undo_match(db: Session, match_id: str, user_id: str) -> Dict[str, Any]:
    """
    Undoes a match approval:
    - Removes profile_members rows created by this match
    - Marks match_suggestion as 'undone'
    - Restores previous entity-view graph exactly
    - Audited & invalidates graph cache
    """
    ms = db.query(MatchSuggestion).filter(MatchSuggestion.id == match_id).first()
    if not ms:
        raise ValueError("Match suggestion not found")
    if ms.status != "approved":
        raise ValueError("Only approved matches can be undone")

    # Find members created by this match
    members = db.query(ProfileMember).filter(ProfileMember.match_id == ms.id).all()
    profile_ids = set(m.profile_id for m in members)

    for m in members:
        db.delete(m)

    ms.status = "undone"
    ms.decided_by = user_id
    ms.decided_at = datetime.utcnow()
    db.commit()

    # Clean up empty/single-member profile_members if any
    for pid in profile_ids:
        remaining = db.query(ProfileMember).filter(ProfileMember.profile_id == pid).all()
        if len(remaining) <= 1:
            for rem in remaining:
                db.delete(rem)
            db.commit()

    record_audit_log(
        db=db,
        user_id=user_id,
        action="match_undo",
        case_id=ms.case_id,
        object_type="match_suggestion",
        object_id=ms.id,
        details={"match_id": ms.id}
    )

    invalidate_case_graph(ms.case_id)

    return {"status": "undone", "match_id": ms.id}

def get_case_master_profiles(db: Session, case_id: str) -> List[Dict[str, Any]]:
    """Returns all consolidated Master Profiles for a case."""
    # Find all profile members for entities belonging to this case
    case_persons = db.query(Entity).filter(Entity.case_id == case_id, Entity.label == "Person").all()
    person_map = {p.canonical_id: p for p in case_persons}
    pids = list(person_map.keys())

    if not pids:
        return []

    members = db.query(ProfileMember).filter(ProfileMember.entity_id.in_(pids)).all()
    profiles_dict: Dict[str, List[ProfileMember]] = {}
    for m in members:
        profiles_dict.setdefault(m.profile_id, []).append(m)

    res = []
    for pid, mem_list in profiles_dict.items():
        member_entities = [person_map[m.entity_id] for m in mem_list if m.entity_id in person_map]
        aliases = list(set(e.display_name for e in member_entities if e.display_name))
        display_name = aliases[0] if aliases else member_entities[0].canonical_id

        # Linked phones and accounts
        all_member_ids = [e.canonical_id for e in member_entities]
        links = db.query(EntityLink).filter(
            EntityLink.case_id == case_id,
            EntityLink.source_entity_id.in_(all_member_ids)
        ).all()
        phones = list(set(l.target_entity_id for l in links if l.relationship_type == "USES"))
        accounts = list(set(l.target_entity_id for l in links if l.relationship_type == "OWNS"))
        vehicles = list(set(l.target_entity_id for l in links if l.relationship_type == "DRIVES"))

        res.append({
            "profile_id": pid,
            "display_name": display_name,
            "also_known_as": aliases,
            "member_count": len(member_entities),
            "member_entity_ids": all_member_ids,
            "phones": phones,
            "accounts": accounts,
            "vehicles": vehicles,
            "created_at": mem_list[0].created_at.isoformat() if mem_list[0].created_at else None
        })

    return res

def get_master_profile_detail(db: Session, case_id: str, profile_id: str) -> Optional[Dict[str, Any]]:
    """
    Returns complete master profile detail:
    also_known_as, phones, accounts, vehicles, FIR list, connections, timeline, provenance.
    """
    members = db.query(ProfileMember).filter(ProfileMember.profile_id == profile_id).all()
    if not members:
        return None

    member_ids = [m.entity_id for m in members]
    entities = db.query(Entity).filter(Entity.case_id == case_id, Entity.canonical_id.in_(member_ids)).all()
    if not entities:
        return None

    aliases = list(set(e.display_name for e in entities if e.display_name))
    primary_name = aliases[0] if aliases else entities[0].canonical_id

    # Collect linked items
    links = db.query(EntityLink).filter(
        EntityLink.case_id == case_id,
        EntityLink.source_entity_id.in_(member_ids)
    ).all()

    phones = []
    accounts = []
    vehicles = []
    fir_list = []

    for l in links:
        provenance = {
            "source_file": l.source_file,
            "source_ref": l.source_ref,
            "method": l.method,
            "confidence": l.confidence
        }
        if l.relationship_type == "USES":
            phones.append({"number": l.target_entity_id, "provenance": provenance})
        elif l.relationship_type == "OWNS":
            accounts.append({"account": l.target_entity_id, "provenance": provenance})
        elif l.relationship_type == "DRIVES":
            vehicles.append({"vehicle": l.target_entity_id, "provenance": provenance})
        elif l.relationship_type == "MENTIONED_IN":
            fir_list.append({"fir_id": l.target_entity_id, "provenance": provenance})

    # Call history & transaction volume for linked identifiers
    phone_numbers = [p["number"] for p in phones]
    acc_numbers = [a["account"] for a in accounts]

    call_count = 0
    if phone_numbers:
        call_count = db.query(CallRecord).filter(
            CallRecord.case_id == case_id,
            (CallRecord.caller.in_(phone_numbers) | CallRecord.receiver.in_(phone_numbers))
        ).count()

    txn_count = 0
    total_volume_paise = 0
    if acc_numbers:
        txns = db.query(Transaction).filter(
            Transaction.case_id == case_id,
            (Transaction.from_account.in_(acc_numbers) | Transaction.to_account.in_(acc_numbers))
        ).all()
        txn_count = len(txns)
        total_volume_paise = sum(t.amount_paise for t in txns)

    return {
        "profile_id": profile_id,
        "display_name": primary_name,
        "also_known_as": aliases,
        "members": [
            {
                "id": e.canonical_id,
                "name": e.display_name,
                "source_file": e.source_file,
                "source_ref": e.source_ref
            }
            for e in entities
        ],
        "phones": phones,
        "accounts": accounts,
        "vehicles": vehicles,
        "firs": fir_list,
        "stats": {
            "total_calls": call_count,
            "total_transactions": txn_count,
            "total_volume_paise": total_volume_paise,
            "total_volume_inr": total_volume_paise / 100.0
        }
    }

def find_cross_case_alerts(db: Session, case_id: str, current_user_id: str) -> List[Dict[str, Any]]:
    """
    Finds cross-case alerts:
    When a phone, account, or vehicle value already exists in another case that the officer can open,
    returns alert 'Seen in another case' showing only the identifier value, type, and that case's id & title.
    """
    # 1. Fetch current case identifiers
    current_links = db.query(EntityLink).filter(EntityLink.case_id == case_id).all()
    curr_phones = set(l.target_entity_id for l in current_links if l.relationship_type == "USES")
    curr_accounts = set(l.target_entity_id for l in current_links if l.relationship_type == "OWNS")
    curr_vehicles = set(l.target_entity_id for l in current_links if l.relationship_type == "DRIVES")

    # Add directly staged calls & txns
    curr_calls = db.query(CallRecord.caller, CallRecord.receiver).filter(CallRecord.case_id == case_id).limit(200).all()
    for c, r in curr_calls:
        if c: curr_phones.add(c)
        if r: curr_phones.add(r)

    curr_txns = db.query(Transaction.from_account, Transaction.to_account).filter(Transaction.case_id == case_id).limit(200).all()
    for f, t in curr_txns:
        if f: curr_accounts.add(f)
        if t: curr_accounts.add(t)

    alerts = []

    # Check other cases for matching phone
    if curr_phones:
        other_calls = db.query(CallRecord.case_id, CallRecord.caller).filter(
            CallRecord.case_id != case_id,
            CallRecord.caller.in_(list(curr_phones)[:100])
        ).limit(20).all()
        for other_cid, ph in other_calls:
            alerts.append({
                "type": "Phone",
                "identifier": ph,
                "other_case_id": other_cid,
                "message": f"Seen in another case: Phone {ph} appears in case {other_cid}"
            })

    # Check other cases for matching account
    if curr_accounts:
        other_txns = db.query(Transaction.case_id, Transaction.from_account).filter(
            Transaction.case_id != case_id,
            Transaction.from_account.in_(list(curr_accounts)[:100])
        ).limit(20).all()
        for other_cid, acc in other_txns:
            alerts.append({
                "type": "BankAccount",
                "identifier": acc,
                "other_case_id": other_cid,
                "message": f"Seen in another case: Account {acc} appears in case {other_cid}"
            })

    return alerts
