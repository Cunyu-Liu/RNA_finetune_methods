import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from finalize_lr_teams import signature


def test_selection_signature_ignores_order_and_metadata():
    row = {"task": "mrl", "model": "RiNALMo-micro", "split": "random",
           "selected_lr": "1e-5", "selected_best_val": 0.1, "selected_rid": "ft_test"}
    assert signature({"rows": [row], "created_at": "old"}) == signature(
        {"rows": [dict(row)], "created_at": "new"})
    assert signature({"rows": [row]}) != signature(
        {"rows": [dict(row, selected_lr="3e-5")]})
