"""Offline unit tests for arc3_replay (no harness / no arcengine needed)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import arc3_replay as R


def test_frame_hash_stable_and_level_bound():
    g = [[1, 2], [3, 4]]
    assert R.frame_hash(g, level=1) == R.frame_hash([[1, 2], [3, 4]], level=1)
    assert R.frame_hash(g, level=1) != R.frame_hash(g, level=2)
    assert R.frame_hash(g) != R.frame_hash([[1, 2], [3, 5]])
    assert R.frame_hash(None) != R.frame_hash([[0]])


def test_extract_segments_closes_on_level_up():
    entries = [
        ("a1", 1, "h1"), ("a2", 1, "h2"),          # level 1 segment
        ("b1", 2, "h3"),                            # level 2 segment
        ("c1", 3, "h4"), ("c2", 3, "h5"),           # level 3 open segment
    ]
    segs = R.extract_level_segments(entries, initial_hash="h0")
    assert segs[1]["actions"] == ["a1", "a2"] and segs[1]["complete"] is True
    assert segs[1]["end_hash"] == "h2"
    assert segs[1]["step_hashes"] == ["h1", "h2"]
    assert segs[1]["start_hash"] == "h0"
    assert segs[2]["start_hash"] == "h2"
    assert segs[2]["actions"] == ["b1"] and segs[2]["complete"] is True
    assert segs[3]["complete"] is False  # stream ended mid-level


def test_extract_segments_keeps_shortest_on_revisit():
    entries = [
        ("a1", 1, "h1"), ("a2", 1, "h2"), ("a3", 1, "h3"),
        ("b1", 2, "h4"),
        ("x1", 1, "h1"),  # game-over revisit of level 1, shorter
        ("y1", 2, "h4"),
    ]
    segs = R.extract_level_segments(entries)
    assert segs[1]["actions"] == ["x1"]
    assert segs[2]["actions"] == ["b1"]


def test_store_roundtrip_shortest_wins(tmp_path):
    store = R.SolutionStore(tmp_path)
    assert store.best("g1", 1) is None
    assert store.record("g1", 1, start_hash="s", actions=["a", "b", "c"], end_hash="e")
    # longer candidate must not overwrite
    assert not store.record("g1", 1, start_hash="s", actions=["a", "b", "c", "d"], end_hash="e")
    assert store.best("g1", 1)["actions"] == ["a", "b", "c"]
    # shorter candidate replaces
    assert store.record("g1", 1, start_hash="s", actions=["a"], end_hash="e")
    assert store.best("g1", 1)["actions"] == ["a"]
    assert store.levels("g1") == [1]
    assert store.best("g1", 2) is None


def test_plan_replay_requires_start_hash_match(tmp_path):
    store = R.SolutionStore(tmp_path)
    store.record("g1", 2, start_hash="abc", actions=["m"], end_hash="z")
    plan = R.plan_replay(store, "g1", 2, "abc")
    assert plan["actions"] == ["m"] and plan["expected_end_hash"] == "z"
    assert R.plan_replay(store, "g1", 2, "INNY") is None   # diverged start
    assert R.plan_replay(store, "g1", 3, "abc") is None    # unsolved level
    assert R.plan_replay(store, "gX", 2, "abc") is None    # unknown game


def test_verify_step():
    assert R.verify_replay_step("h", "h") is True
    assert R.verify_replay_step("h", "X") is False
    assert R.verify_replay_step(None, "X") is True


def test_env_gating(monkeypatch):
    monkeypatch.delenv("ARC3_REPLAY", raising=False)
    assert R.replay_enabled() is False
    monkeypatch.setenv("ARC3_REPLAY", "1")
    assert R.replay_enabled() is True
    monkeypatch.setenv("ARC3_REPLAY_MAX_ACTIONS_PER_LEVEL", "5")
    assert R.max_actions_per_level() == 5


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
