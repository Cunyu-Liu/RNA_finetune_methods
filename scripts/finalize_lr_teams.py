"""Stage teams-native tuned jobs and promote them after the old selector exits."""
import argparse
import json
import os
from pathlib import Path
import time

from expansion_jobs import lr_tuned_jobs
from expansion_queue import load_jobs


def signature(document):
    return sorted((row["task"], row["model"], row["split"], row["selected_lr"],
                   row["selected_best_val"], row["selected_rid"])
                  for row in document["rows"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--staging", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--selector-pid", type=int, required=True)
    parser.add_argument("--poll-s", type=int, default=300)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    original = json.loads(args.selection.read_text())
    if len(original["rows"]) != 80:
        raise ValueError("frozen selection must contain 80 groups")
    expected = signature(original)
    if not args.staging.exists():
        jobs = lr_tuned_jobs(original["rows"])
        args.staging.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.staging.with_suffix(args.staging.suffix+".tmp")
        temporary.write_text(json.dumps(jobs, indent=2)+"\n")
        os.replace(temporary, args.staging)
    jobs = load_jobs(args.staging)
    if len(jobs) != 240:
        raise ValueError("staged registry must contain 240 jobs")
    while True:
        running = Path(f"/proc/{args.selector_pid}").exists()
        state = {"selector_pid": args.selector_pid, "selector_running": running,
                 "staged_jobs": len(jobs), "promoted": False, "updated_at": time.time()}
        if not running:
            current = json.loads(args.selection.read_text())
            if signature(current) != expected:
                raise ValueError("LR selection changed; refusing path-only promotion")
            temporary = args.output.with_suffix(args.output.suffix+".teams.tmp")
            temporary.write_bytes(args.staging.read_bytes())
            os.replace(temporary, args.output)
            state["promoted"] = True
        state_path = args.staging.with_suffix(".state.json")
        temporary = state_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(state, indent=2)+"\n")
        os.replace(temporary, state_path)
        print(json.dumps(state), flush=True)
        if state["promoted"] or args.once:
            return
        time.sleep(args.poll_s)


if __name__ == "__main__":
    main()
