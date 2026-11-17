"""Statistics for judge calibration, paired comparison and agent reliability."""
from __future__ import annotations

from collections.abc import Sequence
import math
from numbers import Integral

POS = "FAIL"


def _labels(human: Sequence[str], judge: Sequence[str]) -> tuple[list[str], list[str]]:
    if len(human) != len(judge):
        raise ValueError("human and judge must have the same length")
    result = []
    for values in (human, judge):
        if any(not isinstance(v, str) or v.strip().upper() not in {"PASS", "FAIL"} for v in values):
            raise ValueError("labels must be PASS or FAIL")
        result.append([v.strip().upper() for v in values])
    return result[0], result[1]


def confusion(human: Sequence[str], judge: Sequence[str]) -> dict[str, int]:
    h, j = _labels(human, judge)
    return {
        "tp": sum(a == POS and b == POS for a, b in zip(h, j)),
        "fp": sum(a != POS and b == POS for a, b in zip(h, j)),
        "fn": sum(a == POS and b != POS for a, b in zip(h, j)),
        "tn": sum(a != POS and b != POS for a, b in zip(h, j)),
    }


def precision_recall(human: Sequence[str], judge: Sequence[str]) -> tuple[float, float]:
    c = confusion(human, judge)
    p = c["tp"] / (c["tp"] + c["fp"]) if c["tp"] + c["fp"] else 0.0
    r = c["tp"] / (c["tp"] + c["fn"]) if c["tp"] + c["fn"] else 0.0
    return p, r


def cohen_kappa(human: Sequence[str], judge: Sequence[str]) -> float:
    c = confusion(human, judge)
    n = sum(c.values())
    if not n:
        raise ValueError("kappa is undefined for an empty sample")
    observed = (c["tp"] + c["tn"]) / n
    expected = ((c["tp"] + c["fn"]) * (c["tp"] + c["fp"]) +
                (c["tn"] + c["fp"]) * (c["tn"] + c["fn"])) / n**2
    if expected == 1.0:
        raise ValueError("kappa is undefined when expected agreement is one")
    return (observed - expected) / (1.0 - expected)


def rogan_gladen(observed_rate: float, sensitivity: float, specificity: float) -> float:
    if any(not math.isfinite(v) or not 0 <= v <= 1 for v in (observed_rate, sensitivity, specificity)):
        raise ValueError("rates must be finite probabilities")
    denominator = sensitivity + specificity - 1.0
    if math.isclose(denominator, 0.0, abs_tol=1e-15):
        raise ValueError("Rogan-Gladen is undefined for an uninformative classifier")
    return max(0.0, min(1.0, (observed_rate + specificity - 1.0) / denominator))


def paired_bootstrap(a: Sequence[float], b: Sequence[float], *, n_resamples: int = 1000,
                     rng: int = 2027, confidence: float = 0.95) -> tuple[float, float, float]:
    import numpy as np
    from scipy.stats import bootstrap

    if len(a) != len(b) or not len(a):
        raise ValueError("paired samples must be nonempty and have equal length")
    if not isinstance(n_resamples, Integral) or isinstance(n_resamples, bool) or n_resamples < 1:
        raise ValueError("n_resamples must be a positive integer")
    if not math.isfinite(confidence) or not 0 < confidence < 1:
        raise ValueError("confidence must lie strictly between zero and one")
    x, y = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    if x.ndim != 1 or y.ndim != 1 or not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError("samples must be one-dimensional and finite")
    delta = float(np.mean(x) - np.mean(y))
    if np.array_equal(x, y):
        return 0.0, 0.0, 0.0
    if len(x) == 1:
        return delta, delta, delta

    def difference(u, v, axis=-1):
        return np.mean(u, axis=axis) - np.mean(v, axis=axis)

    result = bootstrap((x, y), difference, paired=True, method="percentile",
                       n_resamples=int(n_resamples), confidence_level=confidence,
                       rng=np.random.default_rng(rng))
    return delta, float(result.confidence_interval.low), float(result.confidence_interval.high)


def _validate_k(n: int, c: int, k: int) -> None:
    if any(not isinstance(v, Integral) or isinstance(v, bool) for v in (n, c, k)):
        raise ValueError("n, c and k must be integers")
    if n < 1 or not 0 <= c <= n or not 1 <= k <= n:
        raise ValueError("require n >= 1, 0 <= c <= n and 1 <= k <= n")


def pass_at_k(n: int, c: int, k: int) -> float:
    """Chance that at least one of k draws without replacement passes."""
    _validate_k(n, c, k)
    return 1.0 - math.comb(n - c, k) / math.comb(n, k)


def pass_hat_k(n: int, c: int, k: int) -> float:
    """Chance that all k draws without replacement pass."""
    _validate_k(n, c, k)
    return math.comb(c, k) / math.comb(n, k)
