"""T0.2.5 ledger 单测：strategy 维度 / 重复启动断言 / 崩溃恢复 / flock 并发。

运行: PYTHONPATH=/home/cunyuliu/rna-ft-eval python tests/test_ledger.py
（使用临时目录，不触碰正式 ledger.jsonl）
"""
import os
import sys
import tempfile
import threading

sys.path.insert(0, "/home/cunyuliu/rna-ft-eval")
import rnafteval.ledger as L


def main():
    tmpdir = tempfile.mkdtemp()
    L.LEDGER = os.path.join(tmpdir, "test_ledger.jsonl")
    L.LOCK = os.path.join(tmpdir, "test_ledger.lock")

    rid = L.run_id("ERNIE-RNA", "modification", "lora", 17, "random")
    assert "lora" in rid and "s17" in rid and "random" in rid
    r = L.claim("ERNIE-RNA", "modification", "lora", 17, "random", device=0)
    assert r["claimed"] and r["row"]["strategy"] == "lora"

    L.update(rid, "done", value=0.99)
    r2 = L.claim("ERNIE-RNA", "modification", "lora", 17, "random")
    assert not r2["claimed"] and "already done" in r2["reason"]

    rid2 = L.claim("RNA-FM", "secondary-structure", "frozen", 29, "family")["row"]["run_id"]
    L.update(rid2, "running")
    assert not L.claim("RNA-FM", "secondary-structure", "frozen", 29, "family")["claimed"]

    rid3 = L.claim("SpliceBERT", "noncoding-rna-family", "lora", 43, "random")["row"]["run_id"]
    assert L.claim("SpliceBERT", "noncoding-rna-family", "lora", 43, "random")["claimed"]

    L.update(rid3, "done", value=0.75, epochs=3)
    row = L.by_run_id(rid3)
    assert row["value"] == 0.75 and row["status"] == "done"
    assert L.counts_by("lora").get("done", 0) >= 2

    def worker(i):
        L.claim("M%d" % i, "task-x", "frozen", 17, "random")
    ts = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert len([r for r in L.summary() if r["task"] == "task-x"]) == 10

    print("test_ledger: 8/8 PASS")


if __name__ == "__main__":
    main()
