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
    "RiNALMo-650M": ModelSpec("RiNALMo-650M", "multimolecule/rinalmo-giga", 1280, 650.0, "tierA"),
    "RiNALMo-mega": ModelSpec("RiNALMo-mega", "multimolecule/rinalmo-mega", 640, 148.0, "tierA"),
    "RNA-Sc-650M": ModelSpec("RNA-Sc-650M", "", 768, 650.0, "controlled",
                             custom_loader="rnasc"),
    "ERNIE-RNA": ModelSpec("ERNIE-RNA", "multimolecule/ernierna", 768,
                           86.0, "tierA"),
    "RNA-FM": ModelSpec("RNA-FM", "multimolecule/rnafm", 640, 96.0, "tierA"),
    "UTR-LM": ModelSpec("UTR-LM", "multimolecule/utrlm-mrl", 128, 1.2, "tierB", notes="P2 integrated 2026-09-26; UtrLmModel d_model=128 L6"),
    "mRNABERT": ModelSpec("mRNABERT", "YYLY66/mRNABERT", 768, 86.0, "tierB", custom_loader="mrnabert", notes="P2 integrated 2026-09-26; MosaicBERT, bert. prefix strip"),
    "AIDO.RNA-1.6B": ModelSpec("AIDO.RNA-1.6B", "genbio-ai/GB.RNA-1.6B", 2048, 1600.0, "tierA", strategies=("frozen", "lora"), custom_loader="gbrna", notes="P2 integrated 2026-09-26; RNABert/MegatronBERT, HF4 to 5 patched, no pip"),
    "RiboSpan-1K-40": ModelSpec("RiboSpan-1K-40", "SII-GAIR-NLP/RIBOSPAN-1K-40", 2048, 1600.0, "tierB", strategies=("frozen", "lora"), custom_loader="ribospan", notes="P2 integrated 2026-09-26; long-context, vendored GAIR-NLP/RIBOSPAN-FM code"),
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
    "RNA-Sc-10M-ck1": ModelSpec("RNA-Sc-10M-ck1", "", 512, 10.0, "controlled",
                                custom_loader="rnasc"),
    "RNA-Sc-10M-ck5": ModelSpec("RNA-Sc-10M-ck5", "", 512, 10.0, "controlled",
                                custom_loader="rnasc"),
    "RNA-Sc-10M-ck10": ModelSpec("RNA-Sc-10M-ck10", "", 512, 10.0, "controlled",
                                 custom_loader="rnasc"),
    "RNA-Sc-10M-ck15": ModelSpec("RNA-Sc-10M-ck15", "", 512, 10.0, "controlled",
                                 custom_loader="rnasc"),
    "RNA-Sc-10M-ck20": ModelSpec("RNA-Sc-10M-ck20", "", 512, 10.0, "controlled",
                                 custom_loader="rnasc"),
    "RNA-Sc-100M": ModelSpec("RNA-Sc-100M", "", 768, 100.0, "controlled",
                             custom_loader="rnasc"),
}


def get(name: str) -> ModelSpec:
    return MODEL_SPECS[name]


def load_hf(spec: ModelSpec, device: str):
    """Load multimolecule RNA LMs via the multimolecule package.

    The pypath copy is compat-patched (import guards for transformers 5.0);
    requires PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath.
    """
    from multimolecule import RnaTokenizer
    from transformers import AutoModel
    path = hf_path(spec.repo)
    assert os.path.isdir(path), "model dir missing: %s (download first)" % path
    tok = RnaTokenizer.from_pretrained(path)
    backbone = AutoModel.from_pretrained(path, trust_remote_code=True)
    return tok, backbone.to(device)


class _PseudoConfig(dict):
    """HF-config 兼容容器：属性访问 + `in`（peft _prepare_prompt_learning
    会做 `"num_key_value_heads" in model_config` 检查）。"""

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)

    def get(self, key, default=None):
        return dict.get(self, key, default)


def _rnasc_pseudo_config(mcfg: dict) -> _PseudoConfig:
    return _PseudoConfig({
        "hidden_size": mcfg["d_model"],
        "num_hidden_layers": mcfg["n_layers"],
        "num_attention_heads": mcfg["n_heads"],
        "vocab_size": 5,          # ACGU + PAD (_RnaScTok)
        "pad_token_id": 4,
        "torch_dtype": "float32",
        "model_type": "rnasc",
        "architectures": ["RNAMLMEncoder"],
    })


def _attach_device_property(model):
    """peft PeftModel.device 属性转发到 base model 的 .device——
    RNAMLMEncoder 无此属性，动态注入（跟随首个参数的 device）。"""
    if hasattr(model, "device"):
        return
    try:
        model.device = next(model.parameters()).device
    except StopIteration:
        model.device = "cpu"


class _RnaScWrapper:
    """Wrap rna_sc.RNAMLMEncoder (or peft-wrapped version) into the HF
    .last_hidden_state contract. PeftModel.forward passes **kwargs, so we
    translate input_ids/attention_mask to the RNAMLMEncoder signature."""

    def __init__(self, model):
        self.m = model
        # 伪 config：peft 在 wrapper 层访问 model.config 时兜底
        core = model.m if hasattr(model, "m") else model
        cfg = getattr(core, "config", None)
        if cfg is None:
            mcfg = {"d_model": 192, "n_layers": 6, "n_heads": 6}
            blocks = getattr(core, "blocks", None)
            if blocks is not None and len(blocks):
                mcfg["n_layers"] = len(blocks)
            cfg = _rnasc_pseudo_config(mcfg)
        self.config = cfg;

    def __getattr__(self, name):
        # 转发给内部模型（peft PeftModel.__getattr__ 也走这条）
        return getattr(self.m, name)

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
        "RNA-Sc-650M": "RNA-Sc-650M_s17",
    }
    if "-ck" in model_name:
        base, idx = model_name.rsplit("-ck", 1)
        n_ck = int(idx)
    else:
        base, n_ck = model_name, None
    run_dir = os.path.join(RNASC_RUNS, run_map[base])
    cks = sorted([f for f in os.listdir(run_dir) if f.startswith("ckpt_")],
                 key=lambda f: int(f.split("_nt")[1].split("_")[0]))
    ck_file = cks[n_ck - 1] if n_ck is not None else cks[-1]
    ck = torch.load(os.path.join(run_dir, ck_file), map_location="cpu",
                    weights_only=False)
    mcfg = ck["cfg"]["arch"]
    model = RNAMLMEncoder(d_model=mcfg["d_model"], n_layers=mcfg["n_layers"],
                          n_heads=mcfg["n_heads"], d_ff=mcfg["d_ff"])
    model.load_state_dict(ck["model"])
    # 暴露 HF 风格 config + device（peft PrefixTuning 运行时读取）
    model.config = _rnasc_pseudo_config(mcfg)
    _attach_device_property(model)
    return _RnaScTok(), _RnaScWrapper(model).to(device)


class _MosaicBertWrapper:
    """Wrap MosaicBERT BertModel (returns a tuple) into the HF contract."""
    def __init__(self, model):
        self.m = model
    def __getattr__(self, name):
        return getattr(self.m, name)
    def to(self, device):
        self.m = self.m.to(device); return self
    def parameters(self):
        return self.m.parameters()
    def train(self, mode=True):
        self.m.train(mode)
    def eval(self):
        self.m.eval()
    def __call__(self, input_ids, attention_mask=None, token_type_ids=None, **kw):
        import torch
        if token_type_ids is None:
            token_type_ids = torch.zeros_like(input_ids)
        out = self.m(input_ids=input_ids, attention_mask=attention_mask,
                     token_type_ids=token_type_ids)
        h = out[0] if isinstance(out, (tuple, list)) else out.last_hidden_state
        return type("O", (), {"last_hidden_state": h})


def load_mrnabert(spec: ModelSpec, device: str):
    """Load mRNABERT (MosaicBERT custom code). Checkpoint keys carry a
    bert. prefix while BertModel expects them unprefixed; forward returns a
    tuple (sequence_output, pooled) -> wrap to .last_hidden_state."""
    import torch
    from transformers import AutoConfig, AutoTokenizer
    path = hf_path(spec.repo)
    assert os.path.isdir(path), "model dir missing: %s" % path
    cfg = AutoConfig.from_pretrained(path, trust_remote_code=True)
    import transformers_modules.main.bert_layers as bl
    tok = AutoTokenizer.from_pretrained(path, trust_remote_code=True)
    model = bl.BertModel(cfg)
    sd = torch.load(os.path.join(path, "pytorch_model.bin"),
                    map_location="cpu", weights_only=False)
    sd = {(k[5:] if k.startswith("bert.") else k): v for k, v in sd.items()}
    model.load_state_dict(sd, strict=False)
    return tok, _MosaicBertWrapper(model.to(device))


def _fix_modeling_file(path):
    """Patch vendored transformers-4.x modeling code for transformers>=5:
    provide fallbacks for helpers removed from transformers.pytorch_utils."""
    txt = open(path).read()
    marker = "from transformers.pytorch_utils import ("
    if "find_pruneable_heads_and_indices" not in txt or "except ImportError" in txt:
        return
    k = txt.index(marker)
    end = txt.index(")", k) + 1
    block = txt[k:end]
    fallback = """try:
%s
except ImportError:  # transformers>=5 removed these helpers
    from transformers.pytorch_utils import apply_chunking_to_forward
    import torch as _torch
    from torch import nn as _nn

    def find_pruneable_heads_and_indices(heads, n_heads, head_size, already_pruned_heads):
        mask = _torch.ones(n_heads, head_size)
        heads = set(heads) - already_pruned_heads
        for head in heads:
            head = head - sum(1 if h < head else 0 for h in already_pruned_heads)
            mask[head] = 0
        mask = mask.view(-1).contiguous().eq(1)
        index = _torch.arange(len(mask))[mask].long()
        return heads, index

    def prune_linear_layer(layer, index, dim=0):
        index = index.to(layer.weight.device)
        W = layer.weight.index_select(dim, index).clone().detach()
        if layer.bias is not None:
            b = layer.bias.clone().detach() if dim == 1 else layer.bias[index].clone().detach()
        new_size = list(layer.weight.size()); new_size[dim] = len(index)
        new_layer = _nn.Linear(new_size[1], new_size[0], bias=layer.bias is not None).to(layer.weight.device)
        new_layer.weight.requires_grad = False
        new_layer.weight.copy_(W.contiguous()); new_layer.weight.requires_grad = True
        if layer.bias is not None:
            new_layer.bias.requires_grad = False
            new_layer.bias.copy_(b.contiguous()); new_layer.bias.requires_grad = True
        return new_layer""" % ("\n".join("    " + l for l in block.splitlines()))
    open(path, "w").write(txt[:k] + fallback + txt[end:])


def _load_vendored(spec, device, pkg, module_stems, cfg_name, model_name,
                   tok_name, model_classes, vocab_name="vocab.txt",
                   extra_files=()):
    """Load a model whose HF repo ships modeling code but no auto_map and whose
    upstream pip package would break the shared env (numpy<2 etc.).

    Steps: copy vendored files into a local package under /mnt, patch them for
    transformers>=5, import as a package, build config/model, instantiate the
    slow tokenizer directly, and load safetensors shards manually (HF>=5
    refuses .bin on torch<2.6). No pip install -> shared env untouched.
    """
    import os, sys, shutil, glob, importlib, torch
    base = hf_path(spec.repo)
    assert os.path.isdir(base), "model dir missing: %s" % base
    pkgdir = os.path.join("/mnt/cunyuliu", pkg)
    os.makedirs(pkgdir, exist_ok=True)
    init = os.path.join(pkgdir, "__init__.py")
    if not os.path.exists(init):
        open(init, "w").write("")
    files = list(extra_files) + [vocab_name]
    for f in files:
        src = os.path.join(base, f)
        if os.path.exists(src):
            shutil.copy(src, os.path.join(pkgdir, f))
    for stem in module_stems:
        src = os.path.join(base, stem + ".py")
        if os.path.exists(src):
            _fix_modeling_file(src)
            shutil.copy(src, os.path.join(pkgdir, stem + ".py"))
    if "/mnt/cunyuliu" not in sys.path:
        sys.path.insert(0, "/mnt/cunyuliu")
    mods = {st: importlib.import_module("%s.%s" % (pkg, st)) for st in module_stems}
    mmod = next(m for k, m in mods.items() if "modeling" in k)
    for cname in model_classes:
        cls = getattr(mmod, cname, None)
        if cls is None:
            continue
        if not hasattr(cls, "get_head_mask"):
            def _ghm(self, head_mask, num_hidden_layers, is_attention_chunked=False):
                if head_mask is not None:
                    raise NotImplementedError("head_mask shim unsupported")
                return [None] * num_hidden_layers
            cls.get_head_mask = _ghm
        if not hasattr(cls, "warn_if_padding_and_no_attention_mask"):
            setattr(cls, "warn_if_padding_and_no_attention_mask", lambda self, *a, **k: None)
    cfgmod = next(m for k, m in mods.items() if "configuration" in k)
    cfg = getattr(cfgmod, cfg_name).from_pretrained(base)
    for k, v in (("is_decoder", False), ("add_cross_attention", False),
                 ("chunk_size_feed_forward", 0), ("output_attentions", False),
                 ("output_hidden_states", False), ("pruned_heads", {}),
                 ("tie_word_embeddings", True), ("use_cache", False)):
        try:
            if getattr(cfg, k, "_missing_") == "_missing_":
                setattr(cfg, k, v)
        except Exception:
            try:
                setattr(cfg, k, v)
            except Exception:
                pass
    tokmod = next(m for k, m in mods.items() if "tokeniz" in k)
    tok = getattr(tokmod, tok_name)(vocab_file=os.path.join(pkgdir, vocab_name))
    model = getattr(mmod, model_name)(cfg)
    sd = {}
    st = sorted(glob.glob(os.path.join(base, "*.safetensors")))
    if st:
        from safetensors.torch import load_file
        for f in st:
            sd.update(load_file(f))
    else:
        # repo ships only .bin; transformers>=5 refuses .bin on torch<2.6
        # (CVE-2025-32434) -> load the checkpoint ourselves.
        for f in sorted(glob.glob(os.path.join(base, "pytorch_model*.bin"))):
            sd.update(torch.load(f, map_location="cpu", weights_only=True))
    assert sd, "no checkpoint weights in %s" % base
    model.load_state_dict(sd, strict=False)
    return tok, model.to(torch.float32).to(device)


def load_gbrna(spec, device):
    """AIDO.RNA / GB.RNA (model_type rnabert)."""
    return _load_vendored(
        spec, device, "gbrna_pkg",
        module_stems=["configuration_rnabert", "modeling_rnabert", "tokenization_rnabert"],
        cfg_name="RNABertConfig", model_name="RNABertModel",
        tok_name="RNABertTokenizer",
        model_classes=["RNABertPreTrainedModel", "RNABertModel", "RNABertForMaskedLM"],
        extra_files=("configuration_rnabert.py",))


def load_ribospan(spec, device):
    """RiboSpan (model_type ribospan), 1.6B long-context RNA LM."""
    return _load_vendored(
        spec, device, "ribospan_pkg",
        module_stems=["configuration", "modeling", "tokenization"],
        cfg_name="RiboSpanConfig", model_name="RiboSpanModel",
        tok_name="RiboSpanTokenizer",
        model_classes=["RiboSpanPreTrainedModel", "RiboSpanModel", "RiboSpanForMaskedLM"],
        extra_files=())


def load_model(name: str, device: str):
    spec = MODEL_SPECS[name]
    if spec.custom_loader == "rnasc":
        return spec, *load_rnasc(name, device)
    if spec.custom_loader == "mrnabert":
        return spec, *load_mrnabert(spec, device)
    if spec.custom_loader == "gbrna":
        return spec, *load_gbrna(spec, device)
    if spec.custom_loader == "ribospan":
        return spec, *load_ribospan(spec, device)
    return spec, *load_hf(spec, device)
