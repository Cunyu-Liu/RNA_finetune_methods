"""Real-tokenizer B20 smoke; no model weights or CUDA required."""
import torch
from multimolecule import RnaTokenizer

from rnafteval.base_alignment import align_base_labels
from rnafteval.finetune_spl import encode_seqs
from rnafteval.models import MODEL_SPECS, _RnaScTok, hf_path
from rnafteval.models.nucleicbert_loader import _NucleicBertTok


def main():
    seq = "ACGUACG"
    labels = list(range(len(seq)))
    tokenizers = [
        (name, RnaTokenizer.from_pretrained(hf_path(MODEL_SPECS[name].repo)))
        for name in ("RiNALMo-micro", "ERNIE-RNA", "RNA-FM", "SpliceBERT")
    ]
    tokenizers += [("NucleicBERT", _NucleicBertTok()), ("RNA-Sc", _RnaScTok())]
    for name, tok in tokenizers:
        rows = [{"seq": seq, "labels": labels}]
        enc = encode_seqs(tok, [seq], "cpu", 16)
        y, mask = align_base_labels(tok, enc, rows, 16, dtype=torch.long)
        assert int(mask.sum()) == len(seq), (name, mask)
        assert y[mask].tolist() == labels, name
        enc_trunc = encode_seqs(tok, [seq], "cpu", 5)
        yt, mt = align_base_labels(tok, enc_trunc, rows, 5, dtype=torch.long)
        expected = min(len(seq), 5) if name == "RNA-Sc" else 3
        assert int(mt.sum()) == expected, (name, mt)
        assert yt[mt].tolist() == labels[:expected], name
        print("B20_REAL_OK", name, "positions", mask[0].nonzero().flatten().tolist(),
              "truncated", int(mt.sum()))


if __name__ == "__main__":
    main()
