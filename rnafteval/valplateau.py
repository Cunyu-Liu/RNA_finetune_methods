"""Validation-loss plateau convergence and per-epoch evidence."""
from __future__ import annotations

import itertools
import json
import math
import os
from pathlib import Path

import torch

PROTOCOL = "valplateau_v2"
LEGACY_PROTOCOL = "valplateau_v1"
MIN_DELTA = 0.02
PATIENCE = 3
ABS_FLOOR = 0.008
STOP_REASON = "validation_plateau_min_delta_patience"


def classify(losses, min_delta=MIN_DELTA, patience=PATIENCE,
             abs_floor=ABS_FLOOR):
    """Classify a loss curve using the preregistered relative/absolute rule."""
    if not losses:
        return "EMPTY", "no epochs recorded"
    try:
        finite = all(not isinstance(x, bool) and isinstance(x, (int, float))
                     and math.isfinite(x) for x in losses)
    except (TypeError, ValueError, OverflowError):
        finite = False
    if not finite:
        return "INVALID", "non-finite or non-numeric epoch loss"
    if patience < 1 or min_delta < 0 or abs_floor < 0:
        return "INVALID", "patience must be positive and tolerances non-negative"
    if len(losses) < patience + 1:
        return "TOO_SHORT", "n=%d < patience+1=%d" % (
            len(losses), patience + 1)
    best = min(losses)
    if best <= 0:
        return "INVALID", "non-positive loss cannot use relative delta"
    tail = losses[-patience:]
    tol = max(best * min_delta, abs_floor)
    if all(x <= best + tol for x in tail):
        return "CONVERGED", "tail within max(%.1f%%, %.3f) of best %.4f" % (
            min_delta * 100, abs_floor, best)
    return "NOT_CONVERGED", "tail still improving (best %.4f, tail %s)" % (
        best, ["%.4f" % x for x in tail])


def add_convergence_args(parser):
    parser.add_argument("--converge", action="store_true",
                        help="train until independent validation loss plateaus")
    parser.add_argument("--patience", type=int, default=PATIENCE)
    parser.add_argument("--min-delta", type=float, default=MIN_DELTA)


def training_epochs(args):
    """Fixed legacy epochs, or an unbounded epoch stream for --converge."""
    return itertools.count() if getattr(args, "converge", False) else range(args.epochs)


class PlateauTracker:
    """Own one v2 run's curves; never merge epochs from an older artifact."""

    def __init__(self, out_dir, patience=PATIENCE, min_delta=MIN_DELTA,
                 abs_floor=ABS_FLOOR, run_id=""):
        if patience < 1:
            raise ValueError("patience must be >= 1")
        if min_delta < 0 or abs_floor < 0:
            raise ValueError("min_delta and abs_floor must be >= 0")
        self.path = Path(out_dir) / "plateau.json"
        self.patience = patience
        self.min_delta = min_delta
        self.abs_floor = abs_floor
        self.run_id = run_id
        self.train_losses = []
        self.val_losses = []
        self.status = "RUNNING"
        self.stop_reason = None
        self.stop_detail = None

    def record(self, epoch, train_loss, val_loss):
        if epoch == 0:
            self.train_losses = []
            self.val_losses = []
            self.status = "RUNNING"
            self.stop_reason = None
            self.stop_detail = None
        if epoch != len(self.val_losses):
            raise ValueError("v2 epochs must be contiguous and start at 0")
        self.train_losses.append(round(float(train_loss), 6))
        self.val_losses.append(round(float(val_loss), 6))
        train_status, train_detail = classify(
            self.train_losses, self.min_delta, self.patience, self.abs_floor)
        if train_status == "INVALID":
            raise FloatingPointError("training: " + train_detail)
        status, detail = classify(self.val_losses, self.min_delta,
                                  self.patience, self.abs_floor)
        if status == "INVALID":
            raise FloatingPointError(detail)
        if status == "CONVERGED":
            self.status = "CONVERGED"
            self.stop_reason = STOP_REASON
            self.stop_detail = detail
        payload = {
            "run_id": self.run_id,
            "protocol": PROTOCOL,
            "loss_source": "validation",
            "epoch_train_losses": list(self.train_losses),
            "epoch_val_losses": list(self.val_losses),
            "updated_epoch": epoch,
            "status": self.status,
            "stop_reason": self.stop_reason,
            "stop_detail": self.stop_detail,
            "min_delta": self.min_delta,
            "patience": self.patience,
            "abs_floor": self.abs_floor,
        }
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        with tmp.open("w") as fh:
            json.dump(payload, fh, indent=2, allow_nan=False)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, self.path)
        return self.status == "CONVERGED"

    def result_fields(self):
        return {
            "protocol": PROTOCOL,
            "loss_source": "validation",
            "epoch_train_losses": self.train_losses,
            "epoch_val_losses": self.val_losses,
            "epochs_trained": len(self.val_losses),
            "status": self.status,
            "stop_reason": self.stop_reason,
            "stop_detail": self.stop_detail,
            "min_delta": self.min_delta,
            "patience": self.patience,
            "abs_floor": self.abs_floor,
        }


def runtime_evidence(tok, device):
    """Capture the actual tokenizer and CUDA execution context after loading."""
    dev = torch.device(device)
    index = dev.index if dev.index is not None else torch.cuda.current_device()
    vocab_size = getattr(tok, "vocab_size", None)
    if vocab_size is None:
        vocab = getattr(tok, "_vocab", None)
        if vocab is None:
            getter = getattr(tok, "get_vocab", None)
            vocab = getter() if callable(getter) else None
        vocab_size = len(vocab) if vocab is not None else 0
    evidence = {
        "cuda_available": bool(torch.cuda.is_available()),
        "cuda_device": str(dev),
        "cuda_device_name": torch.cuda.get_device_name(index),
        "cuda_runtime_version": torch.version.cuda,
        "torch_version": torch.__version__,
        "tokenizer_class": "%s.%s" % (type(tok).__module__, type(tok).__name__),
        "tokenizer_name_or_path": str(getattr(tok, "name_or_path", "") or ""),
        "tokenizer_vocab_size": int(vocab_size),
    }
    if dev.type != "cuda" or not evidence["cuda_available"]:
        raise RuntimeError("validation convergence protocol requires real CUDA")
    return evidence
