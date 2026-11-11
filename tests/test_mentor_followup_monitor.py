import json

from mentor_followup_monitor import DORA, write_dora_registry


def test_dora_registry_contains_240_unique_jobs():
    write_dora_registry()
    jobs = json.loads(DORA.read_text())
    assert len(jobs) == 240
    assert {job["strategy"] for job in jobs} == {"dora"}
    assert len({job["rid"] for job in jobs}) == 240
    assert len({job["result_dir"] for job in jobs}) == 240
    assert all(job["result_dir"].startswith(
        "/teams/HoulabData_1788502323/liucunyu/") for job in jobs)
