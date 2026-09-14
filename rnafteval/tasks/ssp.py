"""Secondary-structure prediction (BEACON SSP, bpRNA) — per-base pair task.

Data layout (HF mirror of official Drive folder):
  beacon_raw/secondary-structure/bpRNA/bpRNA.csv   — id,sequence,... columns
  beacon_raw/secondary-structure/bpRNA/{TR0,VL0,TS0}/shard-XX/*.npy
      each npy: (L, L) float matrix, 1 = paired (i, j)

Official split TR0/VL0/TS0 = random arm. Family arm: MMseqs2 re-cluster
(make_family_split.py, shared with ncrna pipeline).

Metric (BEACON official): pair-level precision / recall / F1 over the
upper-triangle predicted pair set (threshold 0.5 on sigmoid scores).
"""
from __future__ import annotations

import csv
import glob
import os

import numpy as np

BEACON_SS = "/mnt/cunyuliu/rna-ft-eval/data/beacon_raw/secondary-structure"
BPRNA = os.path.join(BEACON_SS, "bpRNA")

MAX_LEN = 320          # v1 protocol cap (documented deviation: memory)
MAX_SEQS = None        # None = all


def load_metadata() -> dict[str, dict]:
    """Parse bpRNA.csv -> {id: {seq, dot, family}}.

    Actual columns: ,data_name,file_name,seq,dot_string,seq_len
    (file_name = bpRNA_<SOURCE>_<num>, data_name = TR0/VL0/TS0).
    Family key = SOURCE tag prefix (bpRNA_RFAM_123 -> bpRNA_RFAM);
    MMseqs2 clustering in the family-split script refines this.
    """
    meta = {}
    path = os.path.join(BPRNA, "bpRNA.csv")
    if not os.path.exists(path):
        return meta
    with open(path, newline="") as fh:
        rdr = csv.reader(fh)
        header = [h.strip() for h in next(rdr)]
        idx = {h: i for i, h in enumerate(header)}
        idc = idx.get("file_name", idx.get("id", 1))
        seqc = idx.get("seq", 3)
        dotc = idx.get("dot_string", idx.get("dot_bracket", 4))
        dnc = idx.get("data_name", 1)
        for row in rdr:
            if not row or len(row) <= max(idc, seqc, dotc):
                continue
            rid = row[idc].strip()
            seq = row[seqc].strip().upper().replace("T", "U")
            fam = "_".join(rid.split("_")[:-1])  # bpRNA_RFAM_123 -> bpRNA_RFAM
            meta[rid] = {"seq": seq, "dot": row[dotc].strip(),
                         "family": fam, "data_name": row[dnc].strip()}
    return meta


def dot_to_pairs(dot: str) -> set[tuple[int, int]]:
    """Dot-bracket -> set of paired (i, j), i < j. Pseudoknot bracket classes
    ([{< each get their own stack)."""
    stacks: dict[str, list[int]] = {}
    closes = {")": "(", "]": "[", "}": "{", ">": "<"}
    pairs = set()
    for i, ch in enumerate(dot):
        if ch in "([{<":
            stacks.setdefault(ch, []).append(i)
        elif ch in closes:
            op = closes[ch]
            if stacks.get(op):
                j = stacks[op].pop()
                pairs.add((min(i, j), max(i, j)))
    return pairs


def load_split(split: str, meta: dict[str, dict] | None = None,
               max_len: int = MAX_LEN, max_seqs: int | None = MAX_SEQS,
               family_key: str | None = None) -> list[dict]:
    """Load one TR0/VL0/TS0 split into records.

    Record: {id, seq, dot, pairs, matrix_path, L, family}.
    Sequences longer than max_len are truncated with their targets (protocol
    cap; kept-fraction reported by the returned stats print).
    """
    if meta is None:
        meta = load_metadata()
    d = os.path.join(BPRNA, split)
    recs = []
    files = sorted(glob.glob(os.path.join(d, "shard-*", "*.npy")))
    n_long = 0
    for f in files:
        rid = os.path.splitext(os.path.basename(f))[0]
        m = meta.get(rid)
        if m is None:
            continue
        seq = m["seq"][:max_len]
        if len(m["seq"]) > max_len:
            n_long += 1
        L = len(seq)
        if L < 2:
            continue
        rec = {"id": rid, "seq": seq, "dot": m["dot"][:max_len],
               "family": m["family"], "matrix_path": f, "L": L}
        if m["dot"]:
            rec["pairs"] = sorted(dot_to_pairs(m["dot"][:max_len]))
        recs.append(rec)
        if max_seqs and len(recs) >= max_seqs:
            break
    print("[ssp] split=%s n=%d n_long_capped=%d" % (split, len(recs), n_long),
          flush=True)
    return recs


def load_matrix(rec: dict) -> np.ndarray:
    a = np.load(rec["matrix_path"])
    L = rec["L"]
    return (a[:L, :L] > 0.5).astype(np.int8)


def sanity_check() -> dict:
    """Cross-check dot-bracket pairs vs npy matrix on a sample."""
    meta = load_metadata()
    out = {"n_meta": len(meta)}
    tr = load_split("TR0", meta, max_seqs=50)
    agree, disagree, no_dot = 0, 0, 0
    for r in tr:
        if "pairs" not in r:
            no_dot += 1
            continue
        M = load_matrix(r)
        np_pairs = {(i, j) for i in range(r["L"]) for j in range(i + 1, r["L"])
                    if M[i, j]}
        db = set(map(tuple, r["pairs"]))
        if db == np_pairs:
            agree += 1
        else:
            disagree += 1
    out.update({"agree": agree, "disagree": disagree, "no_dot": no_dot})
    return out


if __name__ == "__main__":
    print(sanity_check())
