import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from revalidate_lora_checkpoint import source_run_id


def test_source_ids_target_formal_fixedsplit_lora_cells():
    assert [source_run_id(seed) for seed in (17, 29, 43)] == [
        f"ft_rinalmomicro_noncodingrnafamily_lora_s{seed}_random_bestval_v1_fixedsplit"
        for seed in (17, 29, 43)
    ]


def test_source_id_rejects_nonformal_seed():
    with pytest.raises(ValueError, match="formal seeds"):
        source_run_id(101)
