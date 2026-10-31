import argparse
import json
from pathlib import Path

import expansion_jobs as registry


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    jobs = []
    for model in ("RiNALMo-micro", "RiNALMo-mega", "RiNALMo-650M"):
        for strategy in ("frozen", "lora", "full"):
            for split in ("random", "family"):
                for level in (6000, 10000):
                    for seed in (17, 29, 43):
                        base = registry.DEFAULTS["crispr-off-target"]["batch"]
                        if model == "RiNALMo-650M":
                            batch_size = min(base, 4 if strategy == "full" else 8)
                        elif model == "RiNALMo-mega" and strategy == "full":
                            batch_size = min(base, 8)
                        else:
                            batch_size = base
                        jobs.append(registry.job_for(
                            "crispr-off-target", model, strategy, split, seed,
                            n_train=level, batch_size=batch_size,
                            need_gb=8 if model == "RiNALMo-micro" else
                            16 if model == "RiNALMo-mega" else 28))
    assert len(jobs) == 108
    assert len({job["rid"] for job in jobs}) == 108
    assert len({job["result_dir"] for job in jobs}) == 108
    assert all(job["task"] == "crispr-off-target" for job in jobs)
    assert {job["n_train"] for job in jobs} == {6000, 10000}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_name(args.output.name + ".tmp")
    temporary.write_text(json.dumps(jobs, indent=2) + "\n")
    temporary.replace(args.output)
    print(json.dumps({"jobs": len(jobs), "levels": [6000, 10000],
                      "output": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
