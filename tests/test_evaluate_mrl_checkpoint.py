import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from evaluate_mrl_checkpoint import pearson


def test_pearson_finite_and_constant_output():
    y = np.arange(10, dtype=float)
    assert pearson(y, y) == pytest.approx(1.0)
    assert pearson(y, np.ones(10)) is None


def test_pearson_reversed_output_is_negative_one():
    y = np.arange(10, dtype=float)
    assert pearson(y, -y) == pytest.approx(-1.0)
