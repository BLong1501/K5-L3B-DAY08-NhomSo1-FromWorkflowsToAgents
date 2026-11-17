"""Shape A boundary: code decides, ticket text is data, trace holds allowlisted fields only."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lab8.shapes.workflow import run_claim
from lab8.tools import ORDER_FIELDS
from tests.conftest import BY_ID, CLAIMS

SEEDS = (11, 22, 33, 44, 55)


def _trace(result) -> dict:
    data = json.loads(Path(result.trace_path).read_text(encoding="utf-8"))
    assert data["run_id"] == result.run_id
    assert isinstance(data["events"], list)
    return data


@pytest.mark.parametrize("claim", CLAIMS, ids=lambda c: c["claim_id"])
def test_workflow_trace_has_no_secret_pii_or_ticket(public_db, claim):
    result = run_claim(claim["claim_id"], seed=11, store_path=str(public_db))
    blob = Path(result.trace_path).read_text(encoding="utf-8")
    for forbidden in claim["expected"]["forbid_substrings"]:
        assert forbidden not in blob
    assert "parent_secret" not in blob
    assert claim["ticket"] not in blob
    for event in _trace(result)["events"]:
        if event["kind"] == "lookup_order" and event["payload"].get("visible"):
            assert set(event["payload"]["order"]) <= set(ORDER_FIELDS)


@pytest.mark.parametrize("seed", SEEDS)
def test_workflow_ignores_ticket_delay_on_every_seed(public_db, seed):
    # T02: ticket says 5 days late, order row says 2. Swarm fails this on seed 55.
    result = run_claim("C-002", seed=seed, store_path=str(public_db))
    assert result.status == "denied"
    assert result.proposal_amount == 0
    assert result.refund_effects == []


def test_workflow_makes_no_model_calls(public_db):
    for claim in CLAIMS:
        result = run_claim(claim["claim_id"], seed=55, store_path=str(public_db))
        assert result.model_calls == 0
        assert result.input_tokens == 0 and result.output_tokens == 0


def test_workflow_replay_keeps_one_refund(public_db):
    first = run_claim("C-001", seed=11, store_path=str(public_db))
    second = run_claim("C-001", seed=22, store_path=str(public_db))
    assert first.status == second.status == "resolved"
    assert len(second.refund_effects) == 1
    assert second.refund_effects[0]["amount_vnd"] == BY_ID["C-001"]["expected"]["refund_vnd"]
    assert second.committed_audit_count == 1
