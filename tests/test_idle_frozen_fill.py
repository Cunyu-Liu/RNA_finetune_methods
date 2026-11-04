import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import idle_frozen_fill as fill


def job(rid, model='RiNALMo-micro'):
    return SimpleNamespace(rid=rid, model=model)


def test_memory_requires_margin_and_preserves_core_window():
    assert not fill.memory_allows(8.99)
    assert fill.memory_allows(9.0)
    assert fill.memory_allows(18.99)
    assert not fill.memory_allows(19.0)
    assert not fill.memory_allows(28.0)


def test_next_runnable_skips_complete_and_dense():
    jobs = [job('done'), job('micro_dense_subset'), job('next'), job('other', 'RNA-FM')]
    states = {'done': ('complete', ''), 'next': ('runnable', '')}
    selected = fill.next_runnable(jobs, lambda j: states[j.rid])
    assert selected.rid == 'next'


def test_next_runnable_stops_on_running_or_conflict():
    for state in ('running', 'conflict'):
        with pytest.raises(RuntimeError, match=state):
            fill.next_runnable([job('bad')], lambda j: (state, 'unsafe'))


def test_child_env_pins_artifact_root(monkeypatch):
    monkeypatch.delenv('RNAFT_ARTIFACT_ROOT', raising=False)
    env = fill.child_env()
    assert env['RNAFT_ARTIFACT_ROOT'] == str(fill.ARTIFACTS)
