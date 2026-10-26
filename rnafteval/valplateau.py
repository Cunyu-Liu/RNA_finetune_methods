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
BESTVAL_PROTOCOL = "bestval_v1"
MIN_DELTA = 0.02
PATIENCE = 3
ABS_FLOOR = 0.008
STOP_REASON = "validation_plateau_min_delta_patience"
BESTVAL_STOP_REASON = "validation_no_improvement_patience"


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
    parser.add_argument("--convergence-mode", choices=("plateau", "bestval"),
                        default="plateau")
    parser.add_argument("--patience", type=int, default=PATIENCE)
    parser.add_argument("--min-delta", type=float, default=MIN_DELTA)


def validate_convergence_args(args):
    if getattr(args, "convergence_mode", "plateau") != "plateau" \
            and not getattr(args, "converge", False):
        raise ValueError("--convergence-mode bestval requires --converge")


def protocol_tag(args):
    if not getattr(args, "converge", False):
        return ""
    mode = getattr(args, "convergence_mode", "plateau")
    if mode == "plateau":
        return "_valplateau_v2"
    if mode == "bestval":
        return "_bestval_v1"
    raise ValueError("unknown convergence mode %r" % mode)


def make_tracker(out_dir, args, run_id, save_best):
    kwargs = dict(patience=args.patience, min_delta=args.min_delta,
                  run_id=run_id)
    if protocol_tag(args) == "_bestval_v1":
        return BestValTracker(out_dir, save_best=save_best, **kwargs)
    return PlateauTracker(out_dir, **kwargs)


def backbone_state_dict(backbone):
    return (backbone.m if hasattr(backbone, "m") else backbone).state_dict()


def load_backbone_state_dict(backbone, state):
    core = backbone.m if hasattr(backbone, "m") else backbone
    core.load_state_dict(state, strict=not hasattr(core, "get_base_model"))


def save_best_checkpoint(path, backbone, head, optimizer=None, **metadata):
    """Atomically save best-val model state; wrappers expose state via .m."""
    state = {"backbone": backbone_state_dict(backbone),
             "head": head.state_dict(), **metadata}
    if optimizer is not None:
        state["optimizer"] = optimizer.state_dict()
    tmp = str(path) + ".tmp"
    torch.save(state, tmp)
    os.replace(tmp, path)


def checkpoint_proof_error(result_dir, result, ledger_row=None):
    """Validate best.ckpt tensors and its agreement with result/ledger evidence."""
    path = Path(result_dir) / "best.ckpt"
    if result.get("protocol") != BESTVAL_PROTOCOL:
        return "result protocol is not bestval_v1"
    if result.get("best_checkpoint") != "best.ckpt":
        return "result best_checkpoint is not best.ckpt"
    best_epoch = result.get("best_epoch")
    best_val = result.get("best_val")
    losses = result.get("epoch_val_losses")
    if not isinstance(best_epoch, int) or isinstance(best_epoch, bool) \
            or best_epoch < 0:
        return "result best_epoch is missing or invalid"
    if not isinstance(losses, list) or best_epoch >= len(losses):
        return "result best_epoch is outside validation curve"
    if best_val != losses[best_epoch] or not isinstance(best_val, (int, float)) \
            or isinstance(best_val, bool) or not math.isfinite(best_val):
        return "result best_val does not match validation curve"
    try:
        if not path.is_file() or path.stat().st_size == 0:
            return "best.ckpt is missing or empty"
    except OSError as exc:
        return "best.ckpt is unreadable: %s" % exc
    try:
        state = torch.load(path, map_location="cpu", weights_only=True)
    except (OSError, ValueError, RuntimeError, TypeError, EOFError) as exc:
        return "best.ckpt is unreadable: %s" % exc
    if not isinstance(state, dict):
        return "best.ckpt is not a state dictionary"
    for key in ("backbone", "head"):
        tensors = state.get(key)
        if not isinstance(tensors, dict) or not tensors:
            return "best.ckpt %s state_dict is missing or empty" % key
        if not all(torch.is_tensor(value) for value in tensors.values()):
            return "best.ckpt %s contains non-tensor state" % key
    for key, expected in (("epoch", best_epoch), ("best_epoch", best_epoch),
                          ("best_val", best_val)):
        if state.get(key) != expected:
            return "best.ckpt %s does not match result" % key
    if ledger_row is not None:
        for key in ("best_epoch", "best_val", "best_checkpoint"):
            if ledger_row.get(key) != result.get(key):
                return "ledger/result %s differs" % key
    return ""


def restore_best_checkpoint(tracker, backbone, head, device="cpu"):
    if tracker.best_epoch is None:
        raise RuntimeError("no best validation checkpoint was recorded")
    path = Path(tracker.out_dir) / "best.ckpt"
    state = torch.load(path, map_location=device, weights_only=True)
    if state.get("best_epoch") != tracker.best_epoch:
        raise RuntimeError("best checkpoint epoch does not match tracker")
    load_backbone_state_dict(backbone, state["backbone"])
    head.load_state_dict(state["head"])
    return state


def bestval_classify(losses, min_delta=MIN_DELTA, patience=PATIENCE,
                     abs_floor=ABS_FLOOR):
    """Audit the no-substantial-improvement stopping condition."""
    try:
        numeric = all(not isinstance(x, bool) and isinstance(x, (int, float))
                      and math.isfinite(x) for x in losses)
    except (TypeError, ValueError, OverflowError):
        numeric = False
    if not losses or not numeric or patience < 1 or min_delta < 0 \
            or abs_floor < 0:
        return "INVALID", "invalid bestval curve or parameters", None
    best = losses[0]
    best_epoch = 0
    stale = 0
    for epoch, loss in enumerate(losses[1:], 1):
        if best - loss > max(best * min_delta, abs_floor):
            best, best_epoch, stale = loss, epoch, 0
        else:
            stale += 1
        if stale >= patience:
            if epoch != len(losses) - 1:
                return "INVALID", "curve continues after bestval stop", None
            return "CONVERGED", "no substantive validation improvement for %d epochs" % patience, best_epoch
    return "NOT_CONVERGED", "patience not exhausted", best_epoch


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


class BestValTracker:
    """Best-validation checkpointing with no-improvement early stopping."""

    def __init__(self, out_dir, patience=PATIENCE, min_delta=MIN_DELTA,
                 abs_floor=ABS_FLOOR, run_id="", save_best=None):
        if save_best is None:
            raise ValueError("bestval requires a save_best callback")
        if patience < 1:
            raise ValueError("patience must be >= 1")
        if min_delta < 0 or abs_floor < 0:
            raise ValueError("min_delta and abs_floor must be >= 0")
        self.out_dir = Path(out_dir)
        self.path = self.out_dir / "plateau.json"
        self.patience = patience
        self.min_delta = min_delta
        self.abs_floor = abs_floor
        self.run_id = run_id
        self.save_best = save_best
        self.train_losses = []
        self.val_losses = []
        self.best_epoch = None
        self.best_val = None
        self.stale_epochs = 0
        self.status = "RUNNING"
        self.stop_reason = None
        self.stop_detail = None

    def record(self, epoch, train_loss, val_loss):
        if epoch == 0:
            self.train_losses = []
            self.val_losses = []
            self.best_epoch = None
            self.best_val = None
            self.stale_epochs = 0
            self.status = "RUNNING"
            self.stop_reason = None
            self.stop_detail = None
        if epoch != len(self.val_losses):
            raise ValueError("bestval epochs must be contiguous and start at 0")
        train_loss = round(float(train_loss), 6)
        val_loss = round(float(val_loss), 6)
        if not math.isfinite(train_loss):
            raise FloatingPointError("training: non-finite epoch loss")
        if not math.isfinite(val_loss):
            raise FloatingPointError("non-finite validation epoch loss")
        self.train_losses.append(train_loss)
        self.val_losses.append(val_loss)
        tolerance = max(self.best_val * self.min_delta, self.abs_floor) \
            if self.best_epoch is not None else 0.0
        improved = self.best_epoch is None or self.best_val - val_loss > tolerance
        if improved:
            self.best_epoch = epoch
            self.best_val = val_loss
            self.stale_epochs = 0
            self.save_best(epoch=epoch, val_loss=val_loss)
        else:
            self.stale_epochs += 1
        if self.stale_epochs >= self.patience:
            self.status = "CONVERGED"
            self.stop_reason = BESTVAL_STOP_REASON
            self.stop_detail = (
                "no substantive validation improvement for %d epochs; best epoch %d"
                % (self.stale_epochs, self.best_epoch))
        payload = {
            "run_id": self.run_id, "protocol": BESTVAL_PROTOCOL,
            "loss_source": "validation",
            "epoch_train_losses": list(self.train_losses),
            "epoch_val_losses": list(self.val_losses),
            "updated_epoch": epoch, "best_epoch": self.best_epoch,
            "best_checkpoint": "best.ckpt",
            "best_val": self.best_val, "stale_epochs": self.stale_epochs,
            "status": self.status, "stop_reason": self.stop_reason,
            "stop_detail": self.stop_detail, "min_delta": self.min_delta,
            "patience": self.patience, "abs_floor": self.abs_floor,
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
            "protocol": BESTVAL_PROTOCOL, "loss_source": "validation",
            "epoch_train_losses": self.train_losses,
            "epoch_val_losses": self.val_losses,
            "epochs_trained": len(self.val_losses),
            "best_epoch": self.best_epoch, "best_val": self.best_val,
            "stale_epochs": self.stale_epochs, "status": self.status,
            "stop_reason": self.stop_reason, "stop_detail": self.stop_detail,
            "min_delta": self.min_delta, "patience": self.patience,
            "abs_floor": self.abs_floor,
            "best_checkpoint": "best.ckpt",
        }


def result_ledger_fields(result):
    """Separate convergence from ledger completion; never mark RUNNING done."""
    fields = {k: v for k, v in result.items() if k != "run_id"}
    if result.get("protocol") in (PROTOCOL, BESTVAL_PROTOCOL):
        if result.get("status") != "CONVERGED":
            raise RuntimeError("validation has not converged; refusing ledger done")
        expected_reason = BESTVAL_STOP_REASON \
            if result["protocol"] == BESTVAL_PROTOCOL else STOP_REASON
        if result.get("stop_reason") != expected_reason:
            raise RuntimeError("validation stop evidence is missing; refusing ledger done")
        fields["convergence_status"] = fields.pop("status")
    return fields


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
