"""Compare release candidates with a trusted baseline; fail closed on corrupt evidence."""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
import math
from numbers import Real
from pathlib import Path
import re

from lab8.console import utf8_stdio
from lab9 import stats
from lab9.eval import SPEC, load_spec, per_item


def _finite(value) -> bool:
    try:
        return isinstance(value, Real) and math.isfinite(value)
    except (OverflowError, TypeError, ValueError):
        return False


def _ratchet(spec: dict, base_spec: dict) -> list[str]:
    if spec.get("eval_set_version") != base_spec.get("eval_set_version"):
        return []
    problems = []
    for section, id_key in (("metrics", "id"), ("slices", "name")):
        current = {m[id_key]: m for m in spec.get(section, [])}
        for old in base_spec.get(section, []):
            key = old[id_key]
            new = current.get(key)
            if new is None:
                problems.append(f"ratchet: removed {section}/{key}")
                continue
            if old.get("blocking") and not new.get("blocking"):
                problems.append(f"ratchet: disabled blocking {section}/{key}")
            if section == "slices" and new.get("metric") != old.get("metric"):
                problems.append(f"ratchet: changed slice metric {key}")
            a, b = (old.get("threshold", {}), new.get("threshold", {})) if section == "metrics" else (old, new)
            for field in ("min", "max", "max_increase"):
                if field not in a:
                    continue
                value = b.get(field)
                if not _finite(value) or (value < a[field] if field == "min" else value > a[field]):
                    problems.append(f"ratchet: loosened {section}/{key}/{field}")
            if a.get("no_significant_drop") and not b.get("no_significant_drop"):
                problems.append(f"ratchet: removed paired-drop check {section}/{key}")
    return problems


def _report_check(report: dict, spec: dict, name: str) -> tuple[list[str], dict]:
    problems, indexed = [], {}
    if not isinstance(report, dict):
        return [f"{name}: report must be an object"], indexed
    manifest, rows, metrics = report.get("manifest"), report.get("rows"), report.get("metrics")
    if not isinstance(manifest, dict) or not isinstance(rows, list) or not isinstance(metrics, dict):
        return [f"{name}: missing manifest/rows/metrics"], indexed
    if (manifest.get("metric_spec_version") is not None and
            manifest["metric_spec_version"] != spec.get("metric_spec_version")):
        problems.append(f"{name}: report was evaluated with another metric spec version")
    if not isinstance(manifest.get("eval_set_sha"), str) or not manifest["eval_set_sha"]:
        problems.append(f"{name}: missing eval_set_sha")
    failures = report.get("evaluator_failures", [])
    if not isinstance(failures, list) or failures:
        problems.append(f"{name}: evaluator_failures must be empty")
    seeds, count = manifest.get("seeds"), manifest.get("items")
    if (not isinstance(seeds, list) or not seeds or
            any(type(s) is not int for s in seeds) or len(set(seeds)) != len(seeds)):
        return problems + [f"{name}: invalid seed manifest"], indexed
    if type(count) is not int or count < 1:
        return problems + [f"{name}: invalid item count"], indexed
    if spec.get("seeds") is not None and set(seeds) != set(spec["seeds"]):
        problems.append(f"{name}: seeds differ from the metric spec")
    if len(rows) != count * len(seeds):
        problems.append(f"{name}: row count differs from items x seeds")
    definitions = spec.get("metrics", [])
    graded = [m["id"] for m in definitions if m["id"] not in {"pass_5", "cost_per_success"}
              and not re.fullmatch(r"pass_(?:at|hat)_\d+", m["id"])]
    for mid, value in metrics.items():
        if value is not None and not _finite(value):
            problems.append(f"{name}: non-finite or non-numeric metric {mid}")
    for m in definitions:
        if not _finite(metrics.get(m["id"])):
            problems.append(f"{name}: missing/non-finite metric {m['id']}")
    item_slices = {}
    for position, row in enumerate(rows):
        if not isinstance(row, dict):
            problems.append(f"{name}: invalid row {position}")
            continue
        item, seed = row.get("item_id"), row.get("seed")
        if not isinstance(item, str) or not item or type(seed) is not int:
            problems.append(f"{name}: invalid item/seed at row {position}")
            continue
        key = item, seed
        if key in indexed:
            problems.append(f"{name}: duplicated (item, seed) {key}")
        indexed[key] = row
        if seed not in seeds:
            problems.append(f"{name}: row seed not in manifest")
        tags = row.get("slices", [])
        if not isinstance(tags, list) or any(not isinstance(t, str) for t in tags) or len(set(tags)) != len(tags):
            problems.append(f"{name}: invalid slice tags at {key}")
        else:
            tag_set = frozenset(tags)
            if item in item_slices and item_slices[item] != tag_set:
                problems.append(f"{name}: inconsistent slice tags for {item}")
            item_slices[item] = tag_set
        for mid in graded:
            if not _finite(row.get(mid)) or not 0 <= row[mid] <= 1:
                problems.append(f"{name}: missing/invalid grader value {mid} at {key}")
        if "cost" in row and (not _finite(row["cost"]) or row["cost"] < 0):
            problems.append(f"{name}: invalid cost at {key}")
    item_ids = {key[0] for key in indexed}
    expected = {(item, seed) for item in item_ids for seed in seeds}
    if len(item_ids) != count or set(indexed) != expected:
        problems.append(f"{name}: incomplete item x seed coverage")
    if problems:
        return problems, indexed

    # Recompute published summaries from the actual rows, rather than trusting a green number.
    expected_metrics = {}
    for m in definitions:
        mid = m["id"]
        if mid in graded:
            values = [row[mid] for row in rows]
            expected_metrics[mid] = sum(values) if m.get("kind") == "safety" else sum(values) / len(values)
    if all("pass_rate" in row for row in rows):
        by_item = defaultdict(list)
        for row in rows:
            by_item[row["item_id"]].append(bool(row["pass_rate"]))
        expected_metrics["pass_5"] = sum(all(values) for values in by_item.values()) / len(by_item)
        for mid in metrics:
            match = re.fullmatch(r"pass_(at|hat)_(\d+)", mid)
            if match:
                fn = stats.pass_at_k if match[1] == "at" else stats.pass_hat_k
                try:
                    expected_metrics[mid] = sum(fn(len(v), sum(v), int(match[2])) for v in by_item.values()) / len(by_item)
                except ValueError:
                    problems.append(f"{name}: undefined reliability metric {mid}")
        if "cost_per_success" in metrics:
            if not all(_finite(row.get("cost")) for row in rows):
                problems.append(f"{name}: missing row cost")
            else:
                successes = sum(bool(row["pass_rate"]) for row in rows)
                if not successes:
                    problems.append(f"{name}: no successful trial for cost/success")
                else:
                    expected_metrics["cost_per_success"] = sum(row["cost"] for row in rows) / successes
    for mid, expected_value in expected_metrics.items():
        if mid in metrics and (not _finite(metrics[mid]) or
                not math.isclose(float(metrics[mid]), expected_value, rel_tol=1e-9, abs_tol=0.000051)):
            problems.append(f"{name}: aggregate {mid} disagrees with rows")
    return problems, indexed


def integrity_check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> list[str]:
    problems = []
    for section, key in (("metrics", "id"), ("slices", "name")):
        entries = spec.get(section, [])
        names = [m.get(key) for m in entries if isinstance(m, dict)]
        if len(names) != len(entries) or any(not isinstance(n, str) or not n for n in names) or len(set(names)) != len(names):
            return [f"invalid or duplicate {section} definitions"]
    for definition in spec.get("metrics", []) + spec.get("slices", []):
        constraints = definition.get("threshold", {}) if "id" in definition else definition
        if not isinstance(constraints, dict):
            return ["invalid threshold object"]
        if any(not _finite(constraints[k]) for k in ("min", "max", "max_increase") if k in constraints):
            return ["non-finite threshold in metric spec"]
    if base_spec is not None:
        problems.extend(_ratchet(spec, base_spec))
    pr_problems, pr_rows = _report_check(pr, spec, "PR")
    base_problems, base_rows = _report_check(base, base_spec or spec, "baseline")
    problems.extend(pr_problems + base_problems)
    if pr_problems or base_problems:
        return problems
    if set(pr_rows) != set(base_rows):
        problems.append("PR item/seed set differs from baseline")
    for key in set(pr_rows) & set(base_rows):
        if set(pr_rows[key].get("slices") or []) != set(base_rows[key].get("slices") or []):
            problems.append(f"slice tags differ from baseline at {key}")
    return problems


def _paired(a: dict, b: dict, spec: dict) -> tuple[float, float, float]:
    if set(a) != set(b) or not a:
        raise ValueError("paired comparison requires the same nonempty set of items")
    bs, keys = spec.get("bootstrap", {}), sorted(a)
    return stats.paired_bootstrap([a[k] for k in keys], [b[k] for k in keys],
                                 n_resamples=bs.get("n_resamples", 1000), rng=bs.get("rng", 2027),
                                 confidence=bs.get("confidence", 0.95))


def slice_check(pr: dict, base: dict, spec: dict) -> tuple[list[str], list[str]]:
    blocked, lines = [], []
    for entry in spec.get("slices", []):
        name, metric = entry["name"], entry["metric"]
        identifier = f"slice:{name}/{metric}"
        a, b = per_item(pr, metric, name), per_item(base, metric, name)
        fail, note = False, ""
        if not a or set(a) != set(b):
            value, fail, note = None, True, "missing paired slice items"
        else:
            value = sum(a.values()) / len(a)
            if "min" in entry and value < entry["min"]:
                fail = True
            if entry.get("no_significant_drop"):
                delta, lo, hi = _paired(a, b, spec)
                note = f"delta {delta:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
                fail = fail or hi < 0
        if fail and entry.get("blocking"):
            blocked.append(identifier)
        verdict = "BLOCK" if fail and entry.get("blocking") else "warn" if fail else "ok"
        lines.append(f"  {identifier:<35} {str(value):<12} {note} {verdict}")
    return blocked, lines


def check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> tuple[list[str], list[str]]:
    problems = integrity_check(pr, base, spec, base_spec)
    if problems:
        return ["integrity"], [f"  INTEGRITY {p}" for p in problems]
    if pr["manifest"]["eval_set_sha"] != base["manifest"]["eval_set_sha"]:
        return ["eval_set_sha"], ["  EVAL SET differs: rebuild the baseline on the same eval set"]
    blocked, lines = [], []
    for metric in spec["metrics"]:
        mid, threshold = metric["id"], metric.get("threshold", {})
        value = pr["metrics"].get(mid)
        fail, note = value is None, ""
        if value is not None:
            fail = (("max" in threshold and value > threshold["max"]) or
                    ("min" in threshold and value < threshold["min"]))
            if "max_increase" in threshold and base["metrics"].get(mid):
                fail = fail or value > base["metrics"][mid] * (1 + threshold["max_increase"])
            if threshold.get("no_significant_drop"):
                a, b = per_item(pr, mid), per_item(base, mid)
                if not a or set(a) != set(b):
                    fail, note = True, "missing paired items"
                else:
                    delta, lo, hi = _paired(a, b, spec)
                    note = f"Δ {delta:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
                    fail = fail or hi < 0
        if fail and metric.get("blocking"):
            blocked.append(mid)
        verdict = "BLOCK" if fail and metric.get("blocking") else "warn" if fail else "ok"
        lines.append(f"  {mid:<22} {str(value):<8} {json.dumps(threshold):<40} {note:<28} {verdict}")
    sb, sl = slice_check(pr, base, spec)
    return blocked + sb, lines + sl


def main(argv: list[str] | None = None) -> int:
    utf8_stdio()
    ap = argparse.ArgumentParser(prog="lab9.gate")
    ap.add_argument("--pr", required=True)
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--spec", default=str(SPEC))
    ap.add_argument("--base-spec", help="trusted baseline metric spec for the ratchet check")
    args = ap.parse_args(argv)
    read = lambda path: json.loads(Path(path).read_text(encoding="utf-8"))
    pr, base = read(args.pr), read(args.baseline)
    blocked, lines = check(pr, base, load_spec(Path(args.spec)),
                           load_spec(Path(args.base_spec)) if args.base_spec else None)
    print(f"gate: PR {pr.get('run_id', '?')} vs main {base.get('run_id', '?')} · eval set {pr.get('manifest', {}).get('eval_set_sha', '?')}")
    print("\n".join(lines))
    if blocked:
        print(f"exit 1 — blocked: {', '.join(blocked)}")
        return 1
    print("exit 0 — merge")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
