# OWNER: P1
"""Tests for merchandise HMAC tokens, entitlement policy, size demand, and volunteer masking."""
from app.engines.merchandise import PureMerchandiseEngine


def test_hmac_token_generation_and_tamper_detection():
    secret = "test_qr_secret_99812_secure"
    pid = "p_participant_101"

    token = PureMerchandiseEngine.generate_token(pid, secret)
    assert token.startswith("fest_qr_p_participant_101_")

    # Valid token passes
    is_valid, decoded_pid = PureMerchandiseEngine.verify_token(token, secret)
    assert is_valid is True
    assert decoded_pid == pid

    # Tampered token fails
    tampered_token = token[:-2] + "xx"
    is_valid_tampered, _ = PureMerchandiseEngine.verify_token(tampered_token, secret)
    assert is_valid_tampered is False

    # Wrong secret fails
    is_valid_wrong_secret, _ = PureMerchandiseEngine.verify_token(token, "wrong_secret")
    assert is_valid_wrong_secret is False


def test_svg_generation():
    token = "fest_qr_p101_abcdef12"
    svg = PureMerchandiseEngine.generate_svg(token, title="Aarohan Pass")
    assert "<svg" in svg
    assert "</svg>" in svg
    assert "Aarohan Pass" in svg


def test_entitlements_policy_per_head_vs_winner_medals():
    """Verifies that winner medals are excluded from general per-head entitlements."""
    catalog = [
        {"name": "T-shirt"},
        {"name": "ID card"},
        {"name": "lanyard"},
        {"name": "tote"},
        {"name": "winner medal"},
    ]
    claims = [
        {"canonical_participant_id": "p_01", "item_name": "ID card", "status": "ISSUED", "id": "clm_1"},
    ]
    details = {"tshirt_size": "L"}

    entitlements = PureMerchandiseEngine.evaluate_entitlements("p_01", details, claims, catalog)
    names = [e["item_name"] for e in entitlements]

    # Standard per-head items included
    assert "T-shirt" in names
    assert "ID card" in names
    assert "lanyard" in names
    assert "tote" in names

    # Winner medal is NOT general per-head distribution
    assert "winner medal" not in names

    # ID card is ISSUED
    id_card = next(e for e in entitlements if e["item_name"] == "ID card")
    assert id_card["status"] == "ISSUED"

    # T-shirt is PENDING with size L
    tshirt = next(e for e in entitlements if e["item_name"] == "T-shirt")
    assert tshirt["status"] == "PENDING"
    assert tshirt["size"] == "L"


def test_unknown_size_flagged():
    catalog = [{"name": "T-shirt"}]
    details = {"tshirt_size": None}  # missing size

    entitlements = PureMerchandiseEngine.evaluate_entitlements("p_02", details, [], catalog)
    tshirt = entitlements[0]
    assert tshirt["size"] == "UNKNOWN"
    assert tshirt["size_flag"] == "NEEDS_SIZE_COLLECTION"


def test_size_demand_and_shortages_policy_dependent():
    participants = [
        {"id": "p1", "status": "EXPECTED", "tshirt_size": "M"},
        {"id": "p2", "status": "EXPECTED", "tshirt_size": "M"},
        {"id": "p3", "status": "EXPECTED", "tshirt_size": "M"},
        {"id": "p4", "status": "EXPECTED", "tshirt_size": "L"},
        {"id": "p5", "status": "EXPECTED", "tshirt_size": "UNKNOWN"},
        {"id": "p6", "status": "MERGED", "tshirt_size": "M"},  # merged duplicate ignored!
    ]
    stock_by_size = {
        "M": 2,  # 3 needed vs 2 available -> shortage of 1
        "L": 10,  # 1 needed vs 10 available -> net +9
        "S": 5,
        "XL": 5,
        "XXL": 5,
    }

    report = PureMerchandiseEngine.calculate_size_demand_and_shortages(participants, stock_by_size)
    assert report["is_policy_dependent"] is True

    m_data = report["breakdown"]["M"]
    assert m_data["demand"] == 3
    assert m_data["stock"] == 2
    assert m_data["shortage"] == 1
    assert m_data["shortage_alert"] is True

    unknown_data = report["breakdown"]["UNKNOWN"]
    assert unknown_data["count"] == 1
    assert unknown_data["flag"] == "NEEDS_SIZE_COLLECTION"


def test_volunteer_response_masking():
    sensitive_data = {
        "claim_id": "clm_01",
        "canonical_participant_id": "p_01",
        "name": "Rohan Verma",
        "contingent": "IIT Bombay",
        "item_name": "T-shirt",
        "size": "XL",
        "phone": "+91-9876543210",  # sensitive!
        "medical_diet": "Diabetic",  # sensitive!
        "room_number": "Hostel 3, Room 204",  # sensitive!
        "status": "ISSUED",
    }

    masked = PureMerchandiseEngine.mask_for_volunteer(sensitive_data)
    assert "phone" not in masked
    assert "medical_diet" not in masked
    assert "room_number" not in masked
    assert masked["name"] == "Rohan Verma"
    assert masked["contingent"] == "IIT Bombay"
    assert masked["item_name"] == "T-shirt"
