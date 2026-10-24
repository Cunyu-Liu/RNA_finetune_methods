"""Real RiNALMo fixed-mask NLL smoke; requires CUDA but writes no results."""
import math
import torch
from multimolecule import RnaTokenizer, RiNALMoForMaskedLM

from rnafteval.e6_forget import nll_eval
from rnafteval.models import MODEL_SPECS, hf_path


def main():
    assert torch.cuda.is_available(), "CUDA required"
    name = "RiNALMo-micro"
    path = hf_path(MODEL_SPECS[name].repo)
    tok = RnaTokenizer.from_pretrained(path)
    backbone = RiNALMoForMaskedLM.from_pretrained(path, trust_remote_code=True).to(0)
    seqs = [("AUGC" * 8)[:24], ("GCAU" * 8)[:28]]
    a = nll_eval(backbone, tok, seqs, 0, bs=1, shuffle_seed=11,
                 eval_seed=201, mask_rate=0.15)
    b = nll_eval(backbone, tok, seqs, 0, bs=2, shuffle_seed=999,
                 eval_seed=201, mask_rate=0.15)
    c = nll_eval(backbone, tok, seqs, 0, bs=2, shuffle_seed=11,
                 eval_seed=707, mask_rate=0.15)
    assert all(math.isfinite(x) for x in (a, b, c)), (a, b, c)
    assert abs(a - b) < 1e-6, (a, b)
    assert abs(a - c) > 1e-8, (a, c)
    print("E6_MLM15_REAL_OK", {"seed201_a": a, "seed201_b": b, "seed707": c})


if __name__ == "__main__":
    main()
