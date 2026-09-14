"""Model adapters + loaders: HF RNA LMs + RNA-Sc controlled family.

All models expose (tokenizer, backbone) where backbone(**enc) returns an
object with .last_hidden_state (B, T, D) aligned to input token positions.
env: HF_ENDPOINT=hf-mirror, HF_HOME=/mnt/cunyuliu/hf_home, PYTHONPATH pypath.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

HF_HOME = "/mnt/cunyuliu/hf_home"
RNASC_RUNS = "/mnt/cunyuliu/rna-sc/runs"


def hf_path(repo: str) -> str:
    return HF_HOME + "/models/" + repo.replace("/", "--") + "/snapshots/main"


@dataclass
class ModelSpec:
    name: str
    repo: str
    d_model: int
    params_m: float
    layer: str          # tierA | tierB | appendix | controlled (rna-sc family)
    strategies: tuple = ("frozen", "lora", "head-only", "full")
    kmer: int = 1
    notes: str = ""
    custom_loader: str = ""   # "rnasc" for RNA-Sc family


MODEL_SPECS: dict[str, ModelSpec] = {
    "RiNALMo-micro": ModelSpec("RiNALMo-micro", "multimolecule/rinalmo-micro",
                               640, 33.4, "tierA"),
    "ERNIE-RNA": ModelSpec("ERNIE-RNA", "multimolecule/ernierna", 768,
                           86.0, "tierA"),
    "RNA-FM": ModelSpec("RNA-FM", "multimolecule/rnafm", 640, 96.0, "tierA"),
    "SpliceBERT": ModelSpec("SpliceBERT", "multimolecule/splicebert", 512,
                            19.2, "tierB"),
    "SpliceBERT-human510": ModelSpec(
        "SpliceBERT-human510", "gyx1130/SpliceBERT-human510", 512, 19.2,
        "tierB", notes="original ckpt"),
    "RNA-Sc-1M": ModelSpec("RNA-Sc-1M", "", 256, 1.0, "controlled",
                           custom_loader="rnasc"),
    "RNA-Sc-10M": ModelSpec("RNA-Sc-10M", "", 512, 10.0, "controlled",
                            custom_loader="rnasc"),
    "RNA-Sc-30M": ModelSpec("RNA-Sc-30M", "", 480, 30.0, "controlled",
                            custom_loader="rnasc"),
    "RNA-Sc-100M": ModelSpec("RNA-Sc-100M", "", 768, 100.0, "controlled",
                             custom_loader="rnasc"),
}


def get(name: str) -> ModelSpec:
    return MODEL_SPECS[name]


def load_hf(spec: ModelSpec, device: str):
    from transformers import AutoModel, AutoTokenizer
    path = hf_path(spec.repo)
    assert os.path.isdir(path), "model dir missing: %s (download first)" % path
    tok = AutoTokenizer.from_pretrained(path, trust_remote_code=True)
    backbone = AutoModel.from_pretrained(path, trust_remote_code=True)
    return tok, backbone.to(device)


class _RnaScWrapper:
    """Wrap rna_sc.RNAMLMEncoder (or peft-wrapped version) into the HF
    .last_hidden_state contract. PeftModel.forward passes **kwargs, so we
    translate input_ids/attention_mask to the RNAMLMEncoder signature."""

    def __init__(self, model):
        self.m = model

    def to(self, device):
        self.m = self.m.to(device)
        return self

    def parameters(self):
        return self.m.parameters()

    def train(self, mode=True):
        self.m.train(mode)

    def eval(self):
        self.m.eval()

    def __call__(self, input_ids, attention_mask=None):
        core = self.m
        # unwrap peft (its forward forwards **kwargs to base encoder)
        if hasattr(core, "base_model") and hasattr(core.base_model, "model"):
            core = core.base_model.model
        _logits, _loss, hiddens = core(input_ids, None,
                                       return_all_hiddens=True)
        h = core.ln_f(hiddens[-1])
        return type("O", (), {"last_hidden_state": h})


class _RnaScTok:
    """nt-level tokenizer matching RNA-Sc vocab (A=0 C=1 G=2 U/T=3, PAD=4)."""

    def __call__(self, seqs, padding=True, truncation=True, max_length=512,
                 return_tensors="pt"):
        import torch
        V = {"A": 0, "C": 1, "G": 2, "U": 3, "T": 3}
        PAD = 4
        ids, mask = [], []
        for s in seqs:
            s = s.upper().replace("U", "T")[:max_length]
            row = [V.get(ch, PAD) for ch in s]
            ids.append(row)
            mask.append([1] * len(row))
        maxlen = max(len(r) for r in ids)
        for i, r in enumerate(ids):
            pad = maxlen - len(r)
            ids[i] = r + [PAD] * pad
            mask[i] = mask[i] + [0] * pad
        return {"input_ids": torch.tensor(ids),
                "attention_mask": torch.tensor(mask)}


def load_rnasc(model_name: str, device: str):
    import sys
    import torch
    sys.path.insert(0, "/home/cunyuliu/rna-sc")
    from rna_sc.model import RNAMLMEncoder

    run_map = {
        "RNA-Sc-1M": "RNA-Sc-1M_s17",
        "RNA-Sc-10M": "RNA-Sc-10M_s17",
        "RNA-Sc-30M": "RNA-Sc-30M_s17",
        "RNA-Sc-100M": "RNA-Sc-100M_s17",
    }
    run_dir = os.path.join(RNASC_RUNS, run_map[model_name])
    cks = sorted([f for f in os.listdir(run_dir) if f.startswith("ckpt_")],
                 key=lambda f: int(f.split("_nt")[1].split("_")[0]))
    ck = torch.load(os.path.join(run_dir, cks[-1]), map_location="cpu",
                    weights_only=False)
    mcfg = ck["cfg"]["arch"]
    model = RNAMLMEncoder(d_model=mcfg["d_model"], n_layers=mcfg["n_layers"],
                          n_heads=mcfg["n_heads"], d_ff=mcfg["d_ff"])
    model.load_state_dict(ck["model"])
    return _RnaScTok(), _RnaScWrapper(model).to(device)


def load_model(name: str, device: str):
    spec = MODEL_SPECS[name]
    if spec.custom_loader == "rnasc":
        return spec, *load_rnasc(name, device)
    return spec, *load_hf(spec, device)
