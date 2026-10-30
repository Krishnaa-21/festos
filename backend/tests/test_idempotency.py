# OWNER: P1
from app.core.idempotency import check_idempotency, hash_request, store_idempotency
from sqlmodel import Session


def test_idempotency_store_and_replay(session: Session):
    key = "idem-test-key-12345"
    method = "POST"
    path = "/api/v1/_example/items"
    body = b'{"name": "Badge Set", "role": "PARTICIPANT"}'

    req_hash = hash_request(method, path, body)

    # Initially not present
    cached = check_idempotency(session, key, req_hash)
    assert cached is None

    # Store response
    response_body = {"status": "SUCCESS", "id": "itm_badge_01"}
    store_idempotency(session, key, req_hash, response_code=200, response_body=response_body)

    # Replay request
    replayed = check_idempotency(session, key, req_hash)
    assert replayed is not None
    assert replayed["status_code"] == 200
    assert replayed["body"]["status"] == "SUCCESS"
    assert replayed["body"]["id"] == "itm_badge_01"
