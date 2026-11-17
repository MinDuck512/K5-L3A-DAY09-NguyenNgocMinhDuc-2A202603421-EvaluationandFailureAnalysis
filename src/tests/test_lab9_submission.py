"""Additional regression vectors: money statements and evidence integrity."""
import copy
import math

import pytest
from pydantic_evals.evaluators import EvaluatorContext

from lab9 import gate, stats
from lab9.graders import ReplyAmountCorrect, PolicyDenialRecorded
from lab9.trace_case import investigate

pytestmark = pytest.mark.student


def _ctx(text, amount=20000, status="resolved", has_reply=True):
    output = {"result": {"status": status}, "snapshot": {"refund_vnd": amount},
              "events": [{"kind": "reply", "payload": {"text": text}}] if has_reply else []}
    return EvaluatorContext(name="reply", inputs={}, metadata=None, expected_output={}, output=output,
                            duration=0.0, _span_tree=None, attributes={}, metrics={})


@pytest.mark.parametrize("text", ["Đã hoàn 35.000đ", "Đã hoàn phí 35,000 VND", "Đã hoàn 35000", "Đã hoàn 35 000 đồng"])
def test_reply_amount_reads_ledger_instead_of_the_proposal(text):
    assert ReplyAmountCorrect().evaluate(_ctx(text)).value is False


@pytest.mark.parametrize("text", ["Dạ, đã hoàn 20.000đ cho đơn O-808.", "LogiX đã hoàn phí 20,000 VND."])
def test_reply_amount_accepts_honest_paraphrases(text):
    assert ReplyAmountCorrect().evaluate(_ctx(text)).value is True


def test_reply_amount_legacy_trace_and_denial():
    assert ReplyAmountCorrect().evaluate(_ctx("", has_reply=False)).value is True
    assert ReplyAmountCorrect().evaluate(_ctx("Đơn chưa đủ điều kiện hoàn tiền.", 0, "denied")).value is True
    assert ReplyAmountCorrect().evaluate(_ctx("Đã hoàn 35.000đ", 0, "denied")).value is False


def test_trace_case_ticket_override_is_the_first_visible_wrong_step():
    bad = investigate("seeded_regression", "C-002", 11)["trial"]
    good = investigate("fixed", "C-002", 11)["trial"]
    assert bad["lab8_pass"] is False and good["lab8_pass"] is True
    assert bad["snapshot"]["refund_vnd"] == 20000
    assert good["snapshot"]["refund_vnd"] == 0
    overrides = [i for i, e in enumerate(bad["events"], 1) if e["kind"] == "model_override"]
    assert overrides == [3]
    assert not any(e["kind"] == "model_override" for e in good["events"])


def test_paired_bootstrap_rejects_unpaired_and_nonfinite_samples():
    for a, b in (([], []), ([1], [1, 0]), ([math.nan, 1], [1, 1])):
        with pytest.raises(ValueError):
            stats.paired_bootstrap(a, b)


@pytest.mark.parametrize("args", [(0, 0, 1), (5, -1, 2), (5, 6, 2), (5, 2, 0), (3, 1, 4), (5.0, 2, 1), (True, 1, 1)])
def test_advanced_both_reliability_estimators_validate_inputs(args):
    for fn in (stats.pass_at_k, stats.pass_hat_k):
        with pytest.raises(ValueError):
            fn(*args)


def _trusted():
    spec = {"eval_set_version": "v2", "seeds": [11, 22],
            "metrics": [{"id": "pass_rate", "kind": "capability", "blocking": True,
                         "threshold": {"min": 0.8, "no_significant_drop": True}}],
            "slices": [{"name": "money_movement", "metric": "pass_rate", "min": 1.0,
                        "blocking": True, "no_significant_drop": True}]}
    rows = [{"item_id": f"E-{i}", "seed": seed, "pass_rate": True, "cost": 1.0,
             "slices": ["money_movement"] if i == 0 else ["adversarial"]}
            for i in range(2) for seed in (11, 22)]
    report = {"manifest": {"eval_set_sha": "trusted", "items": 2, "seeds": [11, 22]},
              "rows": rows, "metrics": {"pass_rate": 1.0, "pass_5": 1.0, "cost_per_success": 1.0},
              "evaluator_failures": []}
    return report, spec


@pytest.mark.parametrize("attack", ["duplicate", "missing_value", "nan_row", "aggregate", "evaluator_failure", "slices", "seeds"])
def test_advanced_integrity_blocks_hidden_evidence_manipulations(attack):
    base, spec = _trusted()
    pr = copy.deepcopy(base)
    if attack == "duplicate":
        pr["rows"][1] = copy.deepcopy(pr["rows"][0])
    elif attack == "missing_value":
        pr["rows"][0]["pass_rate"] = None
    elif attack == "nan_row":
        pr["rows"][0]["pass_rate"] = math.nan
    elif attack == "aggregate":
        pr["metrics"]["pass_rate"] = 0.99
    elif attack == "evaluator_failure":
        pr["evaluator_failures"] = ["grader failed on a green-looking trial"]
    elif attack == "slices":
        for row in pr["rows"]:
            row["slices"] = []
    elif attack == "seeds":
        pr["rows"] = [row for row in pr["rows"] if row["seed"] == 11]
        pr["manifest"]["seeds"] = [11]
    blocked, lines = gate.check(pr, base, spec)
    assert blocked == ["integrity"]
    assert any("INTEGRITY" in line for line in lines)


@pytest.mark.parametrize("attack", ["min", "drop_metric", "blocking", "paired_check", "drop_slice", "slice_metric", "slice_paired"])
def test_advanced_ratchet_preserves_all_old_constraints(attack):
    base, spec = _trusted()
    loose = copy.deepcopy(spec)
    metric = loose["metrics"][0]
    if attack == "min":
        metric["threshold"]["min"] = 0.5
    elif attack == "drop_metric":
        loose["metrics"] = []
    elif attack == "blocking":
        metric["blocking"] = False
    elif attack == "paired_check":
        metric["threshold"].pop("no_significant_drop")
    elif attack == "drop_slice":
        loose["slices"] = []
    elif attack == "slice_metric":
        loose["slices"][0]["metric"] = "another_metric"
    elif attack == "slice_paired":
        loose["slices"][0].pop("no_significant_drop")
    assert gate.integrity_check(base, base, loose, spec)


def test_advanced_baseline_and_honest_metadata_refactor_merge():
    base, spec = _trusted()
    pr = copy.deepcopy(base)
    pr.update(shape="independent_name", run_id="new-honest-run")
    assert gate.check(base, base, spec, spec)[0] == []
    assert gate.check(pr, base, spec, spec)[0] == []


def test_policy_denial_audit_explains_pre_deducted_to_zero():
    for shape, expected in (("seeded_regression", False), ("fixed", True)):
        data = investigate(shape, "C-013", 11)
        context = EvaluatorContext(name="denial", inputs={}, metadata=None, expected_output=data["label"],
                                   output=data["trial"], duration=0.0, _span_tree=None, attributes={}, metrics={})
        assert PolicyDenialRecorded().evaluate(context).value is expected


def test_evalset_build_uses_canonical_lf_bytes(tmp_path, monkeypatch):
    import json
    from lab9 import evalset
    source = tmp_path / "source.jsonl"
    source.write_text(json.dumps({"claim_id": "C-001", "matrix_id": "T01", "expected": {"refund_vnd": 35000}}), encoding="utf-8")
    monkeypatch.setattr(evalset, "ITEMS", tmp_path / "items.jsonl")
    monkeypatch.setattr(evalset, "LABELS", tmp_path / "labels.json")
    evalset.build(source)
    assert b"\r\n" not in evalset.ITEMS.read_bytes()
    assert evalset.ITEMS.read_bytes().endswith(b"\n")


def test_advanced_pass_hat_catches_quiet_flakiness_that_the_mean_accepts():
    from lab9.eval import aggregate
    rows = [{"item_id": f"E-{i}", "seed": seed, "pass_rate": True, "slices": [], "cost": 1.0}
            for i in range(10) for seed in (11, 22, 33, 44, 55)]
    base = {"manifest": {"eval_set_sha": "same", "items": 10, "seeds": [11, 22, 33, 44, 55]},
            "rows": rows, "metrics": aggregate(rows, ["pass_rate"], [5]), "evaluator_failures": []}
    pr = copy.deepcopy(base)
    for row in pr["rows"]:
        if row["item_id"] in {"E-0", "E-1"} and row["seed"] == 33:
            row["pass_rate"] = False
    pr["metrics"] = aggregate(pr["rows"], ["pass_rate"], [5])
    spec = {"metrics": [{"id": "pass_rate", "kind": "capability", "blocking": True,
                          "threshold": {"min": 0.85, "no_significant_drop": True}},
                         {"id": "pass_hat_5", "kind": "capability", "blocking": True,
                          "threshold": {"min": 0.85}}]}
    assert gate.check(pr, base, spec)[0] == ["pass_hat_5"]


def test_advanced_nonfinite_thresholds_fail_closed():
    base, spec = _trusted()
    spec["metrics"][0]["threshold"]["min"] = math.nan
    assert gate.check(base, base, spec)[0] == ["integrity"]


def test_trace_probe_preserves_the_official_shape_registry():
    from lab8.shapes import SHAPES
    before = dict(SHAPES)
    case = investigate("probe_stale", "C-006", 11, bugs=["no_override", "stale_clause"])
    assert case["trial"]["lab8_pass"] is False
    assert dict(SHAPES) == before
