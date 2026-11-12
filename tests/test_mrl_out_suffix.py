from types import SimpleNamespace

from rnafteval.finetune_mrl import _run_extra


def args(**updates):
    value = dict(lr=3e-4, rank=8, n_train=20000, smoke=False,
                 converge=True, convergence_mode="bestval", out_suffix="")
    value.update(updates)
    return SimpleNamespace(**value)


def test_default_run_extra_is_unchanged():
    assert _run_extra(args()) == "_bestval_v1"


def test_revalidation_suffix_is_preserved_in_run_id():
    assert _run_extra(args(out_suffix="_reval20261111")) == "_bestval_v1_reval20261111"
    assert _run_extra(args(lr=3e-5, out_suffix="_reval20261111")) == "_lr3e-05_bestval_v1_reval20261111"
