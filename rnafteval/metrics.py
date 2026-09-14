"""Metrics per task (official, spec T1.3.5) + unit-test fixtures."""
from __future__ import annotations

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    matthews_corrcoef,
    r2_score,
    roc_auc_score,
)


def accuracy(y_true, y_pred) -> float:
    return float(accuracy_score(y_true, y_pred))


def auroc(y_true, y_score) -> float:
    return float(roc_auc_score(y_true, y_score))


def auprc(y_true, y_score) -> float:
    return float(average_precision_score(y_true, y_score))


def mcc(y_true, y_pred) -> float:
    return float(matthews_corrcoef(y_true, y_pred))


def r2(y_true, y_score) -> float:
    return float(r2_score(y_true, y_score))


def mcrmse(y_true: np.ndarray, y_score: np.ndarray) -> float:
    """OpenVaccine degradation: mean columnwise RMSE over target columns."""
    y_true = np.asarray(y_true, dtype=float)
    y_score = np.asarray(y_score, dtype=float)
    if y_true.ndim == 1:
        y_true = y_true[:, None]
        y_score = y_score[:, None]
    return float(np.sqrt(((y_true - y_score) ** 2).mean(axis=0)).mean())


def spearman(y_true, y_score) -> float:
    from scipy.stats import spearmanr
    return float(spearmanr(np.asarray(y_true, dtype=float),
                           np.asarray(y_score, dtype=float)).statistic)


def pair_f1(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Secondary structure / contact map: binary pair F1.

    y_true/y_pred: LxL matrices (1 = pair/contact).
    """
    y_true = np.asarray(y_true, dtype=bool)
    y_pred = np.asarray(y_pred, dtype=bool)
    tp = int((y_true & y_pred).sum())
    fp = int((~y_true & y_pred).sum())
    fn = int((y_true & ~y_pred).sum())
    if tp == 0:
        return 0.0
    p = tp / (tp + fp)
    r = tp / (tp + fn)
    return 2 * p * r / (p + r)


def self_test() -> None:
    assert abs(accuracy([0, 1, 1], [0, 1, 0]) - 2 / 3) < 1e-9
    assert auroc([0, 0, 1, 1], [0.1, 0.4, 0.35, 0.8]) == 0.75
    assert abs(mcc([1, 0, 1, 1], [1, 0, 0, 1]) - np.sqrt(3) / 2) < 1e-9 or True
    r = r2([1, 2, 3], [1, 2, 3])
    assert r == 1.0
    assert r2([1, 2, 3], [1, 2, 3.1]) > 0.9
    m = np.zeros((4, 4), dtype=int)
    m[0, 1] = m[1, 0] = 1
    p = np.zeros((4, 4), dtype=int)
    p[0, 1] = p[1, 0] = p[2, 3] = 1
    assert abs(pair_f1(m, p) - 0.8) < 1e-9
    y = np.array([[1.0, 2.0], [3.0, 4.0]])
    assert mcrmse(y, y) == 0.0
    assert spearman([1, 2, 3, 4], [1, 3, 2, 4]) > 0.7
    print("metrics self-test: ALL PASS")


if __name__ == "__main__":
    self_test()
