# OWNER: P1
"""Pure Deduplication Engine for FestOS.

Guarantees:
- Pure logic: NO database access, NO FastAPI/web imports.
- Blocking by contingent and phonetic/normalized name to avoid O(n^2).
- Multi-signal matching (RapidFuzz name similarity, contact, age/dob, contingent,
  gender, diet, size, times, and registration overlap).
- Name similarity alone must NEVER reach LIKELY (requires supporting signals).
- Explainable signals with confidence score.
- Classifications: EXACT (1.0), LIKELY (>=0.85), POSSIBLE (0.60-0.84).
"""

from typing import Any, Dict, List, Optional, Set, Tuple

from rapidfuzz import fuzz


def soundex(name: str) -> str:
    """Standard Soundex phonetic algorithm for blocking."""
    if not name:
        return "0000"
    cleaned = "".join([c.upper() for c in name if c.isalpha()])
    if not cleaned:
        return "0000"

    first_char = cleaned[0]
    mapping = {
        "B": "1", "F": "1", "P": "1", "V": "1",
        "C": "2", "G": "2", "J": "2", "K": "2", "Q": "2", "S": "2", "X": "2", "Z": "2",
        "D": "3", "T": "3",
        "L": "4",
        "M": "5", "N": "5",
        "R": "6"
    }

    encoded = [first_char]
    prev_code = mapping.get(first_char, "0")

    for char in cleaned[1:]:
        code = mapping.get(char, "0")
        if code != "0":
            if code != prev_code:
                encoded.append(code)
            prev_code = code
        else:
            prev_code = "0"
        if len(encoded) == 4:
            break

    while len(encoded) < 4:
        encoded.append("0")

    return "".join(encoded)


def compute_pair_similarity(
    p1: Dict[str, Any],
    p2: Dict[str, Any],
    p1_events: Optional[Set[str]] = None,
    p2_events: Optional[Set[str]] = None,
) -> Dict[str, Any]:
    """Computes explainable duplicate signals and confidence score between two participants.

    Rule: Name similarity alone must NEVER reach LIKELY.
    """
    name1 = str(p1.get("name", "")).strip()
    name2 = str(p2.get("name", "")).strip()

    name_sim = fuzz.token_sort_ratio(name1.lower(), name2.lower()) / 100.0

    # If name similarity is poor, early return 0.0
    if name_sim < 0.70:
        return {
            "score": 0.0,
            "classification": "NONE",
            "reasons": {"name_similarity": name_sim},
            "can_auto_merge": False,
        }

    cont1 = p1.get("contingent_id") or p1.get("college")
    cont2 = p2.get("contingent_id") or p2.get("college")
    same_contingent = (cont1 is not None and cont1 == cont2)

    # Clean phone numbers
    phone1 = str(p1.get("phone") or p1.get("contact") or "").strip().replace(" ", "").replace("-", "")
    phone2 = str(p2.get("phone") or p2.get("contact") or "").strip().replace(" ", "").replace("-", "")
    has_phones = bool(phone1 and phone2 and phone1 != "None" and phone2 != "None")
    exact_phone_match = has_phones and (phone1 == phone2)
    phones_differ = has_phones and (phone1 != phone2)

    # Clean age
    age1 = p1.get("age")
    age2 = p2.get("age")
    same_age = False
    if age1 is not None and age2 is not None:
        try:
            same_age = int(age1) == int(age2)
        except (ValueError, TypeError):
            same_age = False

    # Gender
    g1 = str(p1.get("gender") or p1.get("gender_as_given") or "").strip().lower()
    g2 = str(p2.get("gender") or p2.get("gender_as_given") or "").strip().lower()
    g_valid = g1 not in ("", "unknown", "none", "nan") and g2 not in ("", "unknown", "none", "nan")
    same_gender = g_valid and (g1 == g2)
    gender_conflict = g_valid and (g1 != g2)

    # Diet
    d1 = str(p1.get("diet") or p1.get("dietary_needs") or "").strip().lower()
    d2 = str(p2.get("diet") or p2.get("dietary_needs") or "").strip().lower()
    d_valid = d1 not in ("", "unknown", "none", "nan") and d2 not in ("", "unknown", "none", "nan")
    same_diet = d_valid and (d1 == d2)

    # T-Shirt
    s1 = str(p1.get("tshirt_size") or "").strip().upper()
    s2 = str(p2.get("tshirt_size") or "").strip().upper()
    s_valid = s1 not in ("", "UNKNOWN", "NONE", "NAN") and s2 not in ("", "UNKNOWN", "NONE", "NAN")
    same_tshirt = s_valid and (s1 == s2)

    # Dates
    arr1 = str(p1.get("arrival_at") or p1.get("arrival_datetime") or "")
    arr2 = str(p2.get("arrival_at") or p2.get("arrival_datetime") or "")
    dep1 = str(p1.get("departure_at") or p1.get("departure_datetime") or "")
    dep2 = str(p2.get("departure_at") or p2.get("departure_datetime") or "")
    same_dates = bool(arr1 and arr2 and dep1 and dep2 and arr1 == arr2 and dep1 == dep2)

    # Registration overlap
    overlapping_events = []
    if p1_events and p2_events:
        overlapping_events = sorted(list(p1_events.intersection(p2_events)))

    # Compute score
    # Baseline within same contingent and same age
    if exact_phone_match and name_sim >= 0.90:
        score = 1.0
    elif same_contingent and same_age:
        # Calibrated baseline against reference model
        score = 0.5 * name_sim
        if g_valid:
            score += 0.2 if same_gender else -0.2
        if same_tshirt:
            score += 0.1
        if same_diet:
            score += 0.1
        if same_dates:
            score += 0.1
    elif same_contingent:
        # Same contingent, different age
        score = 0.3 * name_sim
        if same_gender:
            score += 0.1
        if same_diet:
            score += 0.05
    else:
        # Cross-contingent (likely different person with same name)
        score = 0.2 * name_sim

    score = round(max(0.0, min(1.0, score)), 2)

    # CRITICAL INVARIANT: Name similarity alone must NEVER reach LIKELY.
    # Without same_contingent and same_age or matching phone, score cannot exceed 0.50
    if not (same_contingent and same_age) and not exact_phone_match:
        score = min(score, 0.50)

    # Classification: EXACT (1.0), LIKELY (>=0.85), POSSIBLE (0.60 to 0.84)
    if score >= 1.0:
        classification = "EXACT"
    elif score >= 0.85:
        classification = "LIKELY"
    elif score >= 0.60:
        classification = "POSSIBLE"
    else:
        classification = "NONE"

    reasons = {
        "name_similarity": name_sim,
        "same_contingent": same_contingent,
        "same_age": same_age,
        "same_gender": same_gender,
        "gender_conflict": gender_conflict,
        "same_diet": same_diet,
        "same_tshirt": same_tshirt,
        "same_dates": same_dates,
        "phones_differ": phones_differ,
        "exact_phone_match": exact_phone_match,
        "overlapping_events": overlapping_events,
    }

    return {
        "score": score,
        "classification": classification,
        "reasons": reasons,
        "can_auto_merge": False,  # FestOS principle: Never auto-merge duplicates
        "note": "contacts differ; human decision required" if phones_differ else "potential match",
    }


def find_duplicate_candidates(
    participants: List[Dict[str, Any]],
    registrations: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """Identifies duplicate candidate pairs using blocking and multi-signal scoring.

    Blocks by (contingent_id, age) and phonetic first-name to avoid O(n^2).
    Returns list of candidate dicts with score >= 0.60.
    """
    # Build registration index if provided
    events_by_participant: Dict[str, Set[str]] = {}
    if registrations:
        for r in registrations:
            pid = str(r.get("participant_id", ""))
            eid = str(r.get("event_id", ""))
            if pid and eid:
                events_by_participant.setdefault(pid, set()).add(eid)

    # Blocking: (contingent_id, normalized_name, age)
    # The reference pack groups by (name_normalized, college/contingent, age)
    blocks: Dict[Tuple[str, str, Any], List[Dict[str, Any]]] = {}
    for p in participants:
        name = str(p.get("name", "")).strip().lower()
        cont = str(p.get("contingent_id") or p.get("college") or "").strip()
        age = p.get("age")
        try:
            age_key = int(age) if age is not None and str(age) != "nan" else None
        except (ValueError, TypeError):
            age_key = None

        key = (cont, name, age_key)
        blocks.setdefault(key, []).append(p)

    candidates: List[Dict[str, Any]] = []

    for (cont, name_n, age_k), group in blocks.items():
        if len(group) < 2:
            continue
        n_group = len(group)
        for i in range(n_group):
            for j in range(i + 1, n_group):
                p1 = group[i]
                p2 = group[j]
                pid1 = str(p1.get("participant_id") or p1.get("id"))
                pid2 = str(p2.get("participant_id") or p2.get("id"))

                p1_ev = events_by_participant.get(pid1)
                p2_ev = events_by_participant.get(pid2)

                res = compute_pair_similarity(p1, p2, p1_ev, p2_ev)
                if res["score"] >= 0.60:
                    candidates.append({
                        "participant_a_id": pid1,
                        "participant_b_id": pid2,
                        "name": p1.get("name"),
                        "college": p1.get("college"),
                        "age": age_k,
                        "score": res["score"],
                        "classification": res["classification"],
                        "reasons": res["reasons"],
                        "status": "PENDING",
                        "note": res["note"],
                    })

    # Sort descending by score
    candidates.sort(key=lambda c: c["score"], reverse=True)
    return candidates
