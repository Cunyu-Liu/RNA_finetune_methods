#!/usr/bin/env python3
"""Bounded dispatcher with strict valplateau_v2/bestval_v1 proof checks.

The registry is deliberately supplied by --jobs-json.  A production job needs
module (or command), rid, result_dir, need_gb, lr, rank, n_train and protocol.
This module does not infer historical artifacts or select a task runner.
"""
from __future__ import annotations

import argparse
import contextlib
import datetime
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import shlex
import subprocess
import sys
import time
from dataclasses import dataclass, field

import torch

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
from rnafteval import ledger
from rnafteval import valplateau as vp

GI = 1024 ** 3
CLAIM_BLOCKED = 75
JOB_KEY_FIELDS = ("model", "task", "strategy", "split", "seed",
                  "lr", "rank", "n_train", "protocol")


class RegistryError(ValueError):
    pass


@dataclass
class Job:
    task: str
    model: str
    strategy: str
    split: str
    seed: int
    args: list[str]
    need_gb: float
    lr: str | None
    rank: int | None
    n_train: int | None
    protocol: str
    rid: str
    result_dir: str
    module: str | None = None
    command: list[str] | None = None
    expected_metric: str | None = None
    job_key: str = ""
    key_fields: dict = field(default_factory=dict)

    @property
    def cell(self):
        return (self.task, self.model, self.strategy, self.split, self.seed,
                self.lr, self.rank, self.n_train, self.protocol)

    @property
    def result_path(self):
        return Path(self.result_dir) / "result.json"

    @property
    def plateau_path(self):
        return Path(self.result_dir) / "plateau.json"

    def build_command(self, device=0, python=None):
        if self.command is not None:
            cmd = list(self.command)
        else:
            cmd = [python or sys.executable, "-m", self.module]
        if any(x in ("--device", "--device-id") for x in cmd):
            raise RegistryError("command/args must not contain --device")
        if self.command is None:
            cmd += ["--model", self.model, "--strategy", self.strategy,
                    "--seed", str(self.seed), "--device", str(device)]
            if self.module == "rnafteval.e6_forget":
                return cmd + list(self.args)
            cmd += ["--split", self.split]
            if self.module not in ("rnafteval.finetune_clf",
                                   "rnafteval.finetune_spl",
                                   "rnafteval.finetune_regbase"):
                cmd += ["--task", self.task]
        else:
            cmd += ["--device", str(device)]
        return cmd + list(self.args)

    def manifest(self, log_path, git_sha):
        return {
            "job_key": self.job_key, "key_fields": self.key_fields,
            "command": [], "need_gb": self.need_gb, "code_git_sha": git_sha,
            "pid": None, "start": None, "end": None, "rc": None,
            "log": str(log_path), "result_dir": self.result_dir,
            "rid": self.rid, "status": "pending", "reason": "",
        }


def _finite_number(value):
    return (not isinstance(value, bool) and isinstance(value, (int, float))
            and math.isfinite(value))


def _positive_int(value):
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _parse_job(raw, index):
    if not isinstance(raw, dict):
        raise RegistryError("job %d is not an object" % index)
    missing = [k for k in ("task", "model", "strategy", "split", "seed",
                           "rid", "result_dir", "need_gb", "protocol")
               if k not in raw]
    if missing:
        raise RegistryError("job %d missing: %s" % (index, ",".join(missing)))
    for key in ("task", "model", "strategy", "split", "rid", "result_dir",
                "protocol"):
        if not isinstance(raw[key], str) or not raw[key]:
            raise RegistryError("job %d %s must be a nonempty string" % (index, key))
    if not _positive_int(raw["seed"]):
        raise RegistryError("job %d seed must be a positive integer" % index)
    if not _finite_number(raw["need_gb"]) or raw["need_gb"] <= 0:
        raise RegistryError("job %d need_gb must be finite and positive" % index)
    args = raw.get("args", [])
    if (not isinstance(args, list)
            or any(not isinstance(x, str) or not x for x in args)):
        raise RegistryError("job %d args must be a list of strings" % index)
    command = raw.get("command")
    module = raw.get("module")
    if (module is None) == (command is None):
        raise RegistryError("job %d requires exactly one of module/command" % index)
    if module is not None and (not isinstance(module, str) or not module):
        raise RegistryError("job %d module must be a nonempty string" % index)
    if command is not None:
        if (not isinstance(command, list) or not command
                or any(not isinstance(x, str) or not x for x in command)):
            raise RegistryError("job %d command must be a nonempty string list" % index)
    if any(x in ("--device", "--device-id") for x in args + (command or [])):
        raise RegistryError("job %d supplies --device; use the dispatcher option" % index)
    rank = raw.get("rank")
    n_train = raw.get("n_train")
    if rank is not None and not _positive_int(rank):
        raise RegistryError("job %d rank must be a positive integer or null" % index)
    if n_train is not None and (not isinstance(n_train, int)
                                or isinstance(n_train, bool) or n_train < 0):
        raise RegistryError("job %d n_train must be a nonnegative integer or null" % index)
    lr = raw.get("lr")
    if lr is not None:
        try:
            if not math.isfinite(float(lr)) or float(lr) <= 0:
                raise ValueError
            lr = str(lr)
        except (TypeError, ValueError, OverflowError):
            raise RegistryError("job %d lr must be finite and positive" % index)
    protocol = raw["protocol"]
    if protocol not in (vp.PROTOCOL, vp.BESTVAL_PROTOCOL):
        raise RegistryError("job %d unsupported protocol: %s" % (index, protocol))
    values = {k: raw.get(k) for k in JOB_KEY_FIELDS}
    values["lr"] = lr
    values["protocol"] = protocol
    key = hashlib.sha256(json.dumps(values, sort_keys=True, separators=(",", ":"),
                                    ensure_ascii=True).encode()).hexdigest()
    return Job(task=raw["task"], model=raw["model"], strategy=raw["strategy"],
               split=raw["split"], seed=raw["seed"], args=list(args),
               need_gb=float(raw["need_gb"]), lr=lr, rank=rank, n_train=n_train,
               protocol=protocol, rid=raw["rid"], result_dir=raw["result_dir"],
               module=module, command=list(command) if command is not None else None,
               expected_metric=raw.get("expected_metric"),
               job_key=key, key_fields=values)


def load_jobs(path):
    try:
        with Path(path).open() as fh:
            raw = json.load(fh)
    except (OSError, ValueError) as exc:
        raise RegistryError("cannot read jobs JSON: %s" % exc) from exc
    if not isinstance(raw, list) or not raw:
        raise RegistryError("jobs JSON must be a nonempty list")
    jobs = [_parse_job(item, i) for i, item in enumerate(raw)]
    seen = {}
    for index, job in enumerate(jobs):
        for kind, value in (("job_key", job.job_key), ("rid", job.rid),
                            ("result_dir", os.path.realpath(job.result_dir))):
            if value in seen:
                raise RegistryError("duplicate %s: %s (jobs %d and %d)" %
                                    (kind, value, seen[value][0], index))
            seen[value] = (index, job.job_key)
    return jobs


def _read_json(path):
    try:
        with Path(path).open() as fh:
            value = json.load(fh)
    except (OSError, ValueError) as exc:
        return None, "invalid %s: %s" % (Path(path).name, exc)
    if not isinstance(value, dict):
        return None, "%s is not an object" % Path(path).name
    return value, ""


def _stop_reason(protocol):
    return vp.BESTVAL_STOP_REASON if protocol == vp.BESTVAL_PROTOCOL else vp.STOP_REASON


def _curve_options(job):
    options = {"min_delta": vp.MIN_DELTA, "patience": vp.PATIENCE,
               "abs_floor": vp.ABS_FLOOR}
    args = (job.command or []) + job.args
    for flag, key, cast in (("--patience", "patience", int),
                            ("--min-delta", "min_delta", float)):
        for index, arg in enumerate(args):
            value = None
            if arg == flag and index + 1 < len(args):
                value = args[index + 1]
            elif arg.startswith(flag + "="):
                value = arg.split("=", 1)[1]
            if value is not None:
                try:
                    options[key] = cast(value)
                except (TypeError, ValueError) as exc:
                    raise RegistryError("invalid %s in job command" % flag) from exc
    return options


def _checkpoint_error(job, source_name, source):
    checkpoint = source.get("best_checkpoint")
    if not isinstance(checkpoint, str) or not checkpoint:
        return "best_checkpoint is missing"
    path = Path(checkpoint)
    if not path.is_absolute():
        path = Path(job.result_dir) / path
    try:
        contained = path.resolve().is_relative_to(Path(job.result_dir).resolve())
    except OSError:
        contained = False
    if not contained:
        return "best_checkpoint escapes result_dir"
    if not path.is_file() or path.stat().st_size == 0:
        return "best_checkpoint file is missing or empty"
    return ""


def _bestval_result_error(result):
    errors = []
    best_epoch = result.get("best_epoch")
    best_val = result.get("best_val")
    if not isinstance(best_epoch, int) or isinstance(best_epoch, bool) or best_epoch < 0:
        errors.append("result best_epoch is missing or invalid")
    if not _finite_number(best_val):
        errors.append("result best_val is missing or invalid")
    losses = result.get("epoch_val_losses")
    if isinstance(best_epoch, int) and not isinstance(best_epoch, bool) \
            and isinstance(losses, list) and best_epoch >= len(losses):
        errors.append("result best_epoch is outside validation curve")
    return errors


def result_error(job, result):
    expected = {"run_id": job.rid, "model": job.model, "task": job.task,
                "seed": job.seed, "split": job.split, "strategy": job.strategy,
                "protocol": job.protocol, "loss_source": "validation",
                "status": "CONVERGED", "stop_reason": _stop_reason(job.protocol)}
    errors = ["result %s mismatch" % key for key, value in expected.items()
              if result.get(key) != value]
    if result.get("smoke") is not False:
        errors.append("result smoke is not false")
    is_e6 = job.task == "e6-forgetting"
    if not is_e6 and not _finite_number(result.get("value")):
        errors.append("result value is not finite numeric")
    if job.expected_metric is not None and result.get("metric") != job.expected_metric:
        errors.append("result primary metric does not match job registry")
    if not is_e6 and not _positive_int(result.get("n_train")):
        errors.append("result n_train is missing or invalid")
    if "acceptance_eligible" in result and result["acceptance_eligible"] is not True:
        errors.append("result acceptance_eligible is not true")
    if job.protocol == vp.BESTVAL_PROTOCOL and result.get("acceptance_eligible") is not True:
        errors.append("bestval result acceptance_eligible is not true")
    if "_smoke" in job.rid:
        errors.append("formal RID contains smoke tag")
    curve_options = _curve_options(job)
    for key, value in curve_options.items():
        if result.get(key) != value:
            errors.append("result %s mismatch" % key)
    val_losses = result.get("epoch_val_losses")
    best_epoch = None
    if not isinstance(val_losses, list) or not val_losses:
        errors.append("result validation curve is missing or empty")
    elif job.protocol == vp.BESTVAL_PROTOCOL:
        status, detail, best_epoch = vp.bestval_classify(val_losses, **curve_options)
        if status != "CONVERGED":
            errors.append("result bestval curve is not converged: " + detail)
    else:
        status, detail = vp.classify(val_losses, **curve_options)
        if status != "CONVERGED":
            errors.append("result validation curve is not converged: " + detail)
    if job.protocol == vp.BESTVAL_PROTOCOL:
        errors.extend(_bestval_result_error(result))
        if best_epoch is not None and result.get("best_epoch") != best_epoch:
            errors.append("result best_epoch does not match bestval stopping rule")
        if _finite_number(result.get("best_val")) and best_epoch is not None \
                and result["best_val"] != val_losses[best_epoch]:
            errors.append("result best_val does not match best epoch loss")
        checkpoint_error = _checkpoint_error(job, "result", result)
        if checkpoint_error:
            errors.append("result " + checkpoint_error)
    train_losses = result.get("epoch_train_losses")
    if (not isinstance(train_losses, list)
            or not isinstance(val_losses, list)
            or len(train_losses) != len(val_losses)):
        errors.append("result train/validation curves have different lengths")
    elif result.get("epochs_trained") != len(val_losses):
        errors.append("result epochs_trained does not match validation curve")
    if not _positive_int(result.get("n_val")):
        errors.append("result n_val is missing or invalid")
    runtime = result.get("runtime")
    if not isinstance(runtime, dict):
        errors.append("result runtime evidence is missing")
    else:
        if runtime.get("cuda_available") is not True:
            errors.append("result runtime does not prove CUDA availability")
        device = runtime.get("cuda_device")
        if not isinstance(device, str) or not device.startswith("cuda:"):
            errors.append("result runtime device is not CUDA")
        if not runtime.get("cuda_device_name"):
            errors.append("result CUDA device name is missing")
        for key in ("tokenizer_class", "tokenizer_name_or_path"):
            if not runtime.get(key):
                errors.append("result %s is missing" % key)
        if not _positive_int(runtime.get("tokenizer_vocab_size")):
            errors.append("result tokenizer_vocab_size is missing or invalid")
    return errors


def plateau_error(job, result, plateau):
    expected = {"run_id": job.rid, "protocol": job.protocol,
                "loss_source": "validation", "status": "CONVERGED",
                "stop_reason": _stop_reason(job.protocol), **_curve_options(job)}
    errors = ["plateau %s mismatch" % key for key, value in expected.items()
              if plateau.get(key) != value]
    shared = ["epoch_val_losses", "epoch_train_losses"]
    if job.protocol == vp.BESTVAL_PROTOCOL:
        shared += ["best_epoch", "best_val", "best_checkpoint", "stale_epochs"]
    for key in shared:
        if plateau.get(key) != result.get(key):
            errors.append("plateau/result %s differ" % key)
    losses = plateau.get("epoch_val_losses")
    if not isinstance(losses, list) or plateau.get("updated_epoch") != len(losses) - 1:
        errors.append("plateau updated_epoch does not match validation curve")
    if job.protocol == vp.BESTVAL_PROTOCOL:
        checkpoint_error = _checkpoint_error(job, "plateau", plateau)
        if checkpoint_error:
            errors.append("plateau " + checkpoint_error)
    return errors


def proof_state(job):
    """Return complete, running, conflict, or runnable for this exact RID."""
    try:
        row = ledger.by_run_id(job.rid)
    except OSError as exc:
        return "conflict", "cannot read ledger: %s" % exc
    if row is not None and row.get("status") == "running":
        return "running", "ledger row is running; refusing duplicate launch"
    result_dir = Path(job.result_dir)
    if result_dir.exists() and not result_dir.is_dir():
        return "conflict", "result_dir exists but is not a directory"
    if not job.result_path.is_file():
        if row is not None and row.get("status") in (
                "done", "cancelled", "invalid", "legacy"):
            return "conflict", "ledger %s but result.json/result_dir is missing" % row["status"]
        return "runnable", ""
    result, error = _read_json(job.result_path)
    if error:
        return "conflict", error
    errors = result_error(job, result)
    if errors:
        return "conflict", "; ".join(errors)
    if not job.plateau_path.exists():
        return "conflict", "result exists but plateau.json is missing"
    plateau, error = _read_json(job.plateau_path)
    if error:
        return "conflict", error
    errors = plateau_error(job, result, plateau)
    if errors:
        return "conflict", "; ".join(errors)
    if row is None or row.get("status") != "done":
        return "conflict", "valid result proof but ledger is not done"
    ledger_expected = {"protocol": job.protocol,
                       "stop_reason": _stop_reason(job.protocol),
                       "convergence_status": "CONVERGED"}
    errors = ["ledger %s mismatch" % key for key, value in ledger_expected.items()
              if row.get(key) != value]
    shared = ["epoch_val_losses", "epoch_train_losses"]
    if job.protocol == vp.BESTVAL_PROTOCOL:
        shared += ["best_epoch", "best_val", "best_checkpoint", "stale_epochs"]
    for key in shared:
        if row.get(key) != result.get(key):
            errors.append("ledger/result %s differ" % key)
    if job.protocol == vp.BESTVAL_PROTOCOL:
        checkpoint_error = _checkpoint_error(job, "ledger", row)
        if checkpoint_error:
            errors.append("ledger " + checkpoint_error)
        else:
            checkpoint_error = vp.checkpoint_proof_error(
                job.result_dir, result, row)
            if checkpoint_error:
                errors.append(checkpoint_error)
    return ("conflict", "; ".join(errors)) if errors else ("complete", "")


def utc_now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def code_git_sha():
    configured = os.environ.get("RNAFT_CODE_GIT_SHA")
    if configured:
        return configured
    try:
        value = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=str(REPO_ROOT),
            stderr=subprocess.DEVNULL, text=True).strip()
        return value or "UNKNOWN"
    except (OSError, subprocess.SubprocessError):
        return "UNKNOWN"


def child_env(git_sha):
    env = os.environ.copy()
    env["RNAFT_CODE_GIT_SHA"] = git_sha
    env["CODE_GIT_SHA"] = git_sha
    paths = ["/root/rnaft/pypath", str(REPO_ROOT), "/home/cunyuliu/rna-sc"]
    env["PYTHONPATH"] = os.pathsep.join(dict.fromkeys(
        paths + [p for p in env.get("PYTHONPATH", "").split(os.pathsep) if p]))
    env.setdefault("HF_HOME", "/root/hf_home")
    env.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
    return env


class ManifestStore:
    def __init__(self, state_dir):
        self.root = Path(state_dir)
        self.logs = self.root / "logs"
        self.locks = self.root / "locks"
        self.logs.mkdir(parents=True, exist_ok=True)
        self.locks.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "manifest.jsonl"

    def log_path(self, job):
        return self.logs / (job.job_key[:20] + ".log")

    def write(self, record):
        with self.path.open("a") as fh:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
            try:
                fh.write(json.dumps(record, sort_keys=True, allow_nan=False) + "\n")
                fh.flush()
                os.fsync(fh.fileno())
            finally:
                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)

    @contextlib.contextmanager
    def _lock(self, kind, identity):
        digest = hashlib.sha256(identity.encode()).hexdigest()[:24]
        handle = (self.locks / (kind + "-" + digest + ".lock")).open("a+")
        acquired = False
        try:
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                acquired = True
            except BlockingIOError as exc:
                if kind == "model":
                    raise ModelBusy("model run lock is held") from exc
                raise AlreadyRunning("cell run lock is held") from exc
            yield
        finally:
            if acquired:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            handle.close()

    def model_lock(self, model):
        return self._lock("model", model)

    def run_locks(self, job):
        return self._lock("cell", repr(job.cell))


class AlreadyRunning(RuntimeError):
    pass


class ModelBusy(AlreadyRunning):
    pass


def _finish(store, record, status, reason="", rc=None):
    record.update(status=status, reason=reason, rc=rc, end=utc_now())
    store.write(record)
    return {"job_key": record["job_key"], "rid": record["rid"],
            "status": status, "reason": reason, "rc": rc,
            "ok": status != "failed"}


def verify_jobs(jobs):
    outcomes = []
    for job in jobs:
        state, reason = proof_state(job)
        if state != "complete":
            outcomes.append((job, state, reason))
            print("INCOMPLETE %s %s %s" % (job.job_key, state, reason), flush=True)
    print("EXPANSION_VERIFY jobs=%d complete=%d incomplete=%d" %
          (len(jobs), len(jobs) - len(outcomes), len(outcomes)), flush=True)
    return 1 if outcomes else 0


def dry_run(jobs, device):
    for job in jobs:
        command = job.build_command(device)
        print(json.dumps({"job_key": job.job_key, "rid": job.rid,
                          "result_dir": job.result_dir, "need_gb": job.need_gb,
                          "command": command, "shell_command": shlex.join(command),
                          "unique": True}, sort_keys=True), flush=True)
    print("EXPANSION_DRY_RUN jobs=%d workers_not_started=true" % len(jobs), flush=True)
    return 0


def dispatch(jobs, workers=1, device=0, state_dir="/root/rnaft/expansion_queue",
             poll_s=30.0):
    store = ManifestStore(state_dir)
    git_sha = code_git_sha()
    pending = []
    outcomes = []
    records = {}
    for job in jobs:
        record = job.manifest(store.log_path(job), git_sha)
        record["command"] = job.build_command(device)
        records[job.job_key] = record
        state, reason = proof_state(job)
        if state == "complete":
            outcomes.append(_finish(store, record, "skipped", "complete proof"))
        elif state == "running":
            outcomes.append(_finish(store, record, "skipped", reason))
        elif state == "conflict":
            outcomes.append(_finish(store, record, "failed", reason))
        else:
            pending.append(job)
    if not pending:
        return _report(jobs, outcomes)
    try:
        free_bytes, total_bytes = torch.cuda.mem_get_info(device)
    except Exception as exc:
        for job in pending:
            outcomes.append(_finish(store, records[job.job_key], "failed",
                                    "CUDA memory check failed: %s" % exc))
        return _report(jobs, outcomes)
    budget_gb = free_bytes / GI
    for job in list(pending):
        if job.need_gb * GI > total_bytes:
            outcomes.append(_finish(
                store, records[job.job_key], "failed",
                "need_gb %.3f exceeds total device memory %.3f" %
                (job.need_gb, total_bytes / GI)))
            pending.remove(job)
    if not pending:
        return _report(jobs, outcomes)
    running = {}

    def finish_running(job, rc, reason=""):
        item = running.pop(job.job_key)
        nonlocal budget_gb
        budget_gb += item["need_gb"]
        item["lock"].__exit__(None, None, None)
        item["model_lock"].__exit__(None, None, None)
        item["log"].close()
        if rc == CLAIM_BLOCKED:
            outcome = _finish(store, item["record"], "skipped",
                              "claim blocked (rc=75)", rc)
        elif rc != 0:
            outcome = _finish(store, item["record"], "failed",
                              reason or "runner exited %s" % rc, rc)
        else:
            state, proof_reason = proof_state(job)
            if state == "complete":
                outcome = _finish(store, item["record"], "done", rc=rc)
            else:
                outcome = _finish(store, item["record"], "failed",
                                  "rc=0 but proof is %s: %s" % (state, proof_reason), rc)
        outcomes.append(outcome)

    while pending or running:
        for job in list(running.values()):
            rc = job["process"].poll()
            if rc is not None:
                finish_running(job["job"], rc)
        while pending and len(running) < workers:
            if not running:
                # External workers may release memory while this queue waits.
                # Refresh only with no owned jobs, avoiding double subtraction.
                try:
                    free_now, _ = torch.cuda.mem_get_info(device)
                    budget_gb = max(budget_gb, free_now / GI)
                except Exception:
                    pass
            job = pending[0]
            record = records[job.job_key]
            state, reason = proof_state(job)
            if state == "complete":
                outcomes.append(_finish(store, record, "skipped", "complete proof"))
                pending.pop(0)
                continue
            if state == "running":
                outcomes.append(_finish(store, record, "skipped", reason))
                pending.pop(0)
                continue
            if state == "conflict":
                outcomes.append(_finish(store, record, "failed", reason))
                pending.pop(0)
                continue
            if job.need_gb > budget_gb:
                # Memory pressure is a wait state, not a failed scientific run.
                break
            if any(item["job"].model == job.model for item in running.values()):
                break
            model_lock = store.model_lock(job.model)
            lock = None
            try:
                model_lock.__enter__()
            except ModelBusy as exc:
                outcomes.append(_finish(store, record, "skipped", str(exc)))
                pending.pop(0)
                continue
            try:
                lock = store.run_locks(job)
                lock.__enter__()
            except AlreadyRunning as exc:
                model_lock.__exit__(None, None, None)
                outcomes.append(_finish(store, record, "skipped", str(exc)))
                pending.pop(0)
                continue
            try:
                free_bytes, _total = torch.cuda.mem_get_info(device)
            except Exception as exc:
                lock.__exit__(None, None, None)
                model_lock.__exit__(None, None, None)
                outcomes.append(_finish(store, record, "failed",
                                        "CUDA memory check failed: %s" % exc))
                pending.pop(0)
                continue
            if free_bytes < job.need_gb * GI:
                lock.__exit__(None, None, None)
                model_lock.__exit__(None, None, None)
                break
            log_handle = store.log_path(job).open("a", buffering=1)
            command = job.build_command(device)
            record.update(command=command, start=utc_now(), status="running")
            try:
                process = subprocess.Popen(
                    command, cwd=str(REPO_ROOT), env=child_env(git_sha),
                    stdout=log_handle, stderr=subprocess.STDOUT)
            except OSError as exc:
                log_handle.close()
                lock.__exit__(None, None, None)
                model_lock.__exit__(None, None, None)
                outcomes.append(_finish(store, record, "failed",
                                        "subprocess launch failed: %s" % exc))
                pending.pop(0)
                continue
            record["pid"] = process.pid
            store.write(record)
            print("START %s rid=%s pid=%d need_gb=%.3f command=%s" %
                  (job.job_key, job.rid, process.pid, job.need_gb,
                   shlex.join(command)), file=log_handle, flush=True)
            budget_gb -= job.need_gb
            running[job.job_key] = {
                "job": job, "process": process, "record": record,
                "need_gb": job.need_gb, "lock": lock,
                "model_lock": model_lock, "log": log_handle,
            }
            pending.pop(0)
        if pending or running:
            time.sleep(poll_s)
    return _report(jobs, outcomes)


def _report(jobs, outcomes):
    failed = [item for item in outcomes if not item["ok"]]
    print("EXPANSION_DONE jobs=%d done=%d skipped=%d failed=%d" %
          (len(jobs), sum(x["status"] == "done" for x in outcomes),
           sum(x["status"] == "skipped" for x in outcomes), len(failed)), flush=True)
    for item in failed:
        print("FAILED %s %s" % (item["rid"], item["reason"]),
              file=sys.stderr, flush=True)
    return 1 if failed or len(outcomes) != len(jobs) else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs-json", required=True)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--verify-only", action="store_true")
    mode.add_argument("--dry-run", action="store_true")
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--device", type=int, default=0)
    parser.add_argument("--state-dir", default="/root/rnaft/expansion_queue")
    parser.add_argument("--poll-s", "--poll-interval", dest="poll_s",
                        type=float, default=30.0)
    args = parser.parse_args(argv)
    if args.workers < 1:
        parser.error("--workers must be >= 1")
    if args.device < 0:
        parser.error("--device must be >= 0")
    if not math.isfinite(args.poll_s) or args.poll_s <= 0:
        parser.error("--poll-s must be finite and positive")
    try:
        jobs = load_jobs(args.jobs_json)
    except RegistryError as exc:
        parser.error(str(exc))
    if args.dry_run:
        return dry_run(jobs, args.device)
    if args.verify_only:
        return verify_jobs(jobs)
    return dispatch(jobs, workers=args.workers, device=args.device,
                    state_dir=args.state_dir, poll_s=args.poll_s)


if __name__ == "__main__":
    raise SystemExit(main())
