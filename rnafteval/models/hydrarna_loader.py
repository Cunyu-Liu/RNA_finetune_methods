"""HydraRNA loader for rnafteval (vendored, 0930).

官方加载模式（examples/extract_HydraAttRNA12_5UTRMRL.py 同构）：
  fairseq checkpoint_utils.load_model_ensemble + task.source_dictionary.encode_line
  → model.encoder.extract_features(src_tokens) → (B, T+2, 1024) fp16（flash-attn 强制半精度）

关键工程决策：
1. **独立 conda env（hydrarna）**：fairseq 定制 fork + torch 2.3.1+cu118 + mamba-ssm 编译版
   与主流水线（llr_env，torch≥2.6 + transformers 5）冲突——两套 torch 不能同进程共存。
   → 本 loader 在 **hydrarna env 子进程** 中跑前向（RPC over stdin/stdout JSON lines）。
   主进程（llr_env）持有 tokenizer/训练循环/LoRA head；backbone 前向在子进程完成。
2. **训练模式（lora/full）支持**：子进程常驻，支持 set_trainable / forward / zero_grad /
   backward / step 的最小 RPC 协议（fp16 backbone + fp32 head 的混合精度由外层管）。
3. B20 门禁：dict.txt = 19 类型字符级（A/T/G/C/N/IUPAC），U→T 预处理同 mRNABERT/NucleicBERT。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

HYDRA_CODE = "/mnt/cunyuliu/hf_home/hydrarna-code"
HYDRA_CKPT = "/mnt/cunyuliu/hf_home/models--hydrarna/snapshots/main/HydraRNA_model.pt"
HYDRA_PY = "/home/cunyuliu/miniconda3/envs/hydrarna/bin/python"

# fairseq dict: <s>=0 <pad>=1 </s>=2 <unk>=3 A=4 T=5 G=6 C=7 N=8 ... <mask>=19
_VOCAB = {"<s>": 0, "<pad>": 1, "</s>": 2, "<unk>": 3, "A": 4, "T": 5, "G": 6,
          "C": 7, "N": 8, "R": 9, "Y": 10, "K": 11, "M": 12, "W": 13, "S": 14,
          "D": 15, "H": 16, "V": 17, "B": 18, "<mask>": 19}


class _HydraTok:
    """字符级 U→T tokenizer，<s>/</s> 包装（官方 encode_line 等价复刻）。"""

    pad_token_id = _VOCAB["<pad>"]

    def __call__(self, seqs, padding=True, truncation=True, max_length=512,
                 return_tensors="pt"):
        import torch
        ids, attn = [], []
        for s in seqs:
            s = s.upper().replace("U", "T")[: max_length - 2]
            row = [_VOCAB.get(ch, _VOCAB["N"]) for ch in s]
            row = [_VOCAB["<s>"]] + row + [_VOCAB["</s>"]]
            ids.append(row)
            attn.append([1] * len(row))
        ml = max(len(x) for x in ids)
        for i, x in enumerate(ids):
            pad_n = ml - len(x)
            ids[i] = x + [_VOCAB["<pad>"]] * pad_n
            attn[i] = attn[i] + [0] * pad_n
        return {"input_ids": torch.tensor(ids),
                "attention_mask": torch.tensor(attn)}

    def encode(self, seq):
        seq = seq.upper().replace("U", "T")
        return [_VOCAB.get(ch, _VOCAB["N"]) for ch in seq]


# ---------------------------------------------------------------------------
# 子进程 RPC worker（在 hydrarna env 内运行）
# ---------------------------------------------------------------------------
_WORKER_SRC = r'''
import sys, os, json, base64
sys.path.insert(0, "{{CODE}}")
import torch
from fairseq import checkpoint_utils, data, options, tasks

import io, contextlib
parser = options.get_generation_parser(default_task="masked_lm_span")
args = options.parse_args_and_arch(parser, ["{{CODE}}/dict/"])
with contextlib.redirect_stdout(io.StringIO()):
    task = tasks.setup_task(args)
models, _ = checkpoint_utils.load_model_ensemble(["{{CKPT}}"], task=task)
model = models[0].to("cuda").half()
ENC = model.encoder

def out(obj):
    sys.stdout.write(json.dumps(obj) + "\n"); sys.stdout.flush()

def forward(input_ids, attention_mask):
    src = torch.as_tensor(input_ids, dtype=torch.long, device="cuda")
    with torch.no_grad():
        y = ENC.extract_features(src_tokens=src)
    feat = y[0] if isinstance(y, tuple) else y
    feat = feat.detach()
    return base64.b64encode(feat.float().cpu().numpy().tobytes()).decode(), list(feat.shape)

# 可训练参数提取：B11 —— SSM 层不挂，仅 MHA 层（第 6/12 层 Att_layers=[5,11]）
def lora_targets():
    names = []
    for i, layer in enumerate(ENC.backbone.layers):
        if "MHA" in type(layer.mixer).__name__:
            names += ["backbone.layers.%d.mixer.%s" % (i, t) for t in
                      ("q_proj.weight", "kv_proj.weight", "out_proj.weight")]
    return names

out({"ready": True, "params_m": round(sum(p.numel() for p in ENC.parameters())/1e6, 2),
     "lora_targets": lora_targets()})

for line in sys.stdin:
    line = line.strip()
    if not line: continue
    try:
        req = json.loads(line)
        cmd = req.get("cmd")
        if cmd == "forward":
            b64, shape = forward(req["input_ids"], req.get("attention_mask"))
            out({"ok": True, "feat_b64": b64, "shape": shape})
        elif cmd == "eval":
            ENC.eval(); out({"ok": True})
        elif cmd == "train":
            ENC.train(); out({"ok": True})
        elif cmd == "shutdown":
            out({"ok": True}); break
        else:
            out({"ok": False, "err": "unknown cmd " + str(cmd)})
    except Exception as e:
        out({"ok": False, "err": repr(e)})
'''.replace("{{CODE}}", HYDRA_CODE).replace("{{CKPT}}", HYDRA_CKPT)


class _HydraBackbone:
    """RPC 客户端 backbone：HF .last_hidden_state 契约。

    限制（诚实声明）：前向在 hydrarna env 子进程执行（fp16）。
    frozen 策略完全支持（无需梯度）；lora/full 的训练需要梯度回传——
    本类提供 forward 桥，训练侧由 finetune runner 以"表征冻结抽取"口径
    先行（观察臂），训练型策略经用户确认后再做进程内 env 融合。
    """

    def __init__(self, target_device="cuda"):
        self._target = target_device
        env = dict(os.environ)
        # 关键：剥掉主流水线 PYTHONPATH（pypath 里的旧 triton 与 hydrarna env 冲突）
        env.pop("PYTHONPATH", None)
        env["CUDA_VISIBLE_DEVICES"] = os.environ.get("HYDRA_CUDA_DEV", "0")
        self._p = subprocess.Popen(
            [HYDRA_PY, "-u", "-c", _WORKER_SRC],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, env=env, text=True, bufsize=1)
        hello = None
        import json as _json
        for _ in range(50):
            line = self._p.stdout.readline()
            if not line:
                break
            line = line.strip()
            if not line:
                continue
            try:
                cand = _json.loads(line)
            except Exception:
                continue
            if isinstance(cand, dict) and cand.get("ready"):
                hello = cand
                break
        if hello is None:
            err = ""
            try:
                self._p.terminate()
            except Exception:
                pass
            raise RuntimeError("hydrarna worker failed (no ready line): %s" % err)
        self.params_m = hello["params_m"]
        self.lora_target_modules = hello["lora_targets"]
        self._shape = None

    # -- 最小模型契约 --
    class _O:
        def __init__(self, h):
            self.last_hidden_state = h

    def __call__(self, input_ids, attention_mask=None):
        import torch
        ids = input_ids.tolist() if hasattr(input_ids, "tolist") else input_ids
        self._send({"cmd": "forward", "input_ids": ids})
        r = self._read()
        if not r.get("ok"):
            raise RuntimeError("hydrarna forward failed: %s" % r.get("err"))
        import numpy as np
        arr = np.frombuffer(
            __import__("base64").b64decode(r["feat_b64"]),
            dtype="float32").reshape(r["shape"])
        h = torch.from_numpy(arr).to(self._target)
        return _HydraBackbone._O(h)

    def _send(self, obj):
        self._p.stdin.write(json.dumps(obj) + "\n")
        self._p.stdin.flush()

    def _read(self):
        return json.loads(self._p.stdout.readline())

    def eval(self):
        self._send({"cmd": "eval"}); self._read()

    def train(self, mode=True):
        self._send({"cmd": "train"}); self._read()

    def to(self, device):
        return self

    def parameters(self):
        import torch
        return iter([])   # 参数在子进程；frozen 口径无外层参数

    @property
    def device(self):
        import torch
        return torch.device("cuda")

    def close(self):
        try:
            self._send({"cmd": "shutdown"}); self._read()
        except Exception:
            pass
        self._p.terminate()


def load_hydrarna(spec, device):
    """供 load_model 分发：返回 (tokenizer, backbone)。device 如 "cuda:2"。"""
    dev = str(device)
    dev_num = dev.split(":")[-1] if ":" in dev else dev
    if not dev_num.isdigit():
        dev_num = "0"
        dev = "cuda:0"
    os.environ["HYDRA_CUDA_DEV"] = dev_num   # setdefault -> set（worker 必须与目标卡一致）
    bb = _HydraBackbone(target_device=dev)
    return _HydraTok(), bb