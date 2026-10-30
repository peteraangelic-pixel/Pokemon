#!/usr/bin/env python3
"""Offline tests for patch 0006 (arc3_winpath). No harness, no GPU.

A FakeSession reproduces the exact contract the solver.py hooks use:
_execute_action(action, batch_index, batch_size, generated_tokens) -> payload,
with record_action() invoked the same way the patched _execute_action does it.
Run: /path/to/python-with-arcengine -m unittest tests.test_winpath
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import arc3_winpath as wp  # noqa: E402


class FakeState:
    def __init__(self, counter=0, levels=0):
        self.counter = counter
        self.levels_completed = levels
        self.available_actions = [1, 2, 3]

    @property
    def frame(self):
        class F:
            pass
        f = F()
        f.data = [[self.levels_completed * 100 + self.counter]]
        return f


class FakeGame:
    def __init__(self, game_id="ls20-test"):
        self.current_state = FakeState()
        self.game_run = type("R", (), {"game_id": game_id})()


class FakeSession:
    """Toy game: ACTION1 advances a counter; 3 advances complete a level.
    ACTION3 is instant game over. Mirrors the solver hook contract."""

    def __init__(self, game_id="ls20-test", pass_index=0):
        self.game = FakeGame(game_id)
        self.game_index = 0
        self.pass_index = pass_index
        self.llm_actions = 0
        self.total_actions = 0

    def should_stop(self):
        return self.game.current_state.levels_completed >= 2

    def _execute_action(self, action, *, batch_index, batch_size,
                        generated_tokens=None):
        st = self.game.current_state
        prev_completed = st.levels_completed
        prev_grid = wp._grid_of(st)
        name = action.id.name
        self.total_actions += 1
        game_over = False
        if name == "ACTION1":
            st.counter += 1
            if st.counter >= 3:
                st.counter = 0
                st.levels_completed += 1
        elif name == "ACTION3":
            game_over = True
            st.counter = 0
        payload = {"game_over": game_over,
                   "level_completed": st.levels_completed > prev_completed}
        wp.record_action(self, action_name=name, action_data=dict(action.data),
                         previous_completed=prev_completed,
                         previous_grid=prev_grid, new_state=st, payload=payload)
        return payload

    def llm_step(self):
        import arcengine
        self.llm_actions += 1
        return self._execute_action(
            arcengine.ActionInput(id=arcengine.GameAction.ACTION1, data={}),
            batch_index=1, batch_size=1, generated_tokens=10)


class WinPathTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="wp-test-")
        self.old = dict(os.environ)
        os.environ["ARC3_WINPATH"] = "1"
        os.environ["ARC3_WINPATH_DIR"] = self.tmp
        os.environ.pop("ARC3_DEAD_SKIP", None)
        wp._SESSIONS.clear()

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.old)
        wp._SESSIONS.clear()

    def play_with_llm(self, sess, max_steps=50):
        wp.begin_session(sess)
        steps = 0
        while not sess.should_stop() and steps < max_steps:
            if wp.maybe_replay(sess):
                continue
            sess.llm_step()
            steps += 1
        wp.end_session(sess)

    def test_record_then_replay_next_pass(self):
        a = FakeSession()
        self.play_with_llm(a)
        self.assertEqual(a.game.current_state.levels_completed, 2)
        self.assertEqual(a.llm_actions, 6)  # 3 per level, nothing stored yet

        b = FakeSession()
        self.play_with_llm(b)
        self.assertEqual(b.game.current_state.levels_completed, 2)
        self.assertEqual(b.llm_actions, 0)      # both levels replayed
        self.assertEqual(b.total_actions, 6)    # but actions still counted

    def test_tampered_hash_aborts_and_marks_broken(self):
        a = FakeSession()
        self.play_with_llm(a)
        store_file = Path(self.tmp) / "ls20.json"  # base_key("ls20-test")
        data = json.loads(store_file.read_text())
        data["levels"]["0"]["hashes"][1] = "0" * 16
        store_file.write_text(json.dumps(data))

        b = FakeSession()
        wp.begin_session(b)
        self.assertTrue(wp.maybe_replay(b))     # consumed the turn, then bailed
        self.assertEqual(b.game.current_state.levels_completed, 0)
        self.assertEqual(b.total_actions, 2)    # stopped AT the mismatch
        state = wp._SESSIONS[id(b)]
        self.assertIn(0, state.broken)
        wp.end_session(b)
        data = json.loads(store_file.read_text())
        self.assertGreaterEqual(data["levels"]["0"]["fails"], 1)

    def test_init_mismatch_wastes_no_action(self):
        a = FakeSession()
        self.play_with_llm(a)
        store_file = Path(self.tmp) / "ls20.json"  # base_key("ls20-test")
        data = json.loads(store_file.read_text())
        data["levels"]["0"]["init"] = "f" * 16
        store_file.write_text(json.dumps(data))

        b = FakeSession()
        wp.begin_session(b)
        self.assertFalse(wp.maybe_replay(b))
        self.assertEqual(b.total_actions, 0)
        wp.end_session(b)

    def test_playbook_prefix_match_and_replay(self):
        book = {"version": 1, "games": {"ls20": {"levels": {"0": {
            "actions": [{"name": "ACTION1", "data": {}}] * 3,
            "init": None, "hashes": [], "n": 3, "src": "offline-sweep",
            "fails": 0}}}}}
        Path(self.tmp, "playbook.json").write_text(json.dumps(book))
        sess = FakeSession(game_id="ls20-4f2a99")  # gateway-style suffix
        wp.begin_session(sess)
        self.assertTrue(wp.maybe_replay(sess))
        self.assertEqual(sess.game.current_state.levels_completed, 1)
        wp.end_session(sess)

    def test_dead_skip_thresholds(self):
        os.environ["ARC3_DEAD_SKIP"] = "1"
        store = wp._Store("dead00")
        store.data["passes_completed"] = 3
        store.data["best_levels"] = 0
        store.save()
        repeat = FakeSession(game_id="dead00-abcdef12", pass_index=0)
        wp.begin_session(repeat)
        self.assertTrue(wp.dead_skip(repeat))   # 3 dead entries already
        wp.end_session(repeat)
        store2 = wp._Store("dead11")
        store2.data["passes_completed"] = 2
        store2.data["best_levels"] = 0
        store2.save()
        fresh = FakeSession(game_id="dead11", pass_index=0)
        wp.begin_session(fresh)
        self.assertFalse(wp.dead_skip(fresh))   # only 2 dead entries
        wp.end_session(fresh)

    def test_store_shared_across_entry_suffixes(self):
        a = FakeSession(game_id="ls20-9607627b")
        self.play_with_llm(a)
        self.assertEqual(a.llm_actions, 6)
        b = FakeSession(game_id="ls20-004f2a99")  # another entry, same game
        self.play_with_llm(b)
        self.assertEqual(b.game.current_state.levels_completed, 2)
        self.assertEqual(b.llm_actions, 0)        # replayed from a's memory
        self.assertEqual(wp.base_key("tu93-0768757b"), "tu93")
        self.assertEqual(wp.base_key("m0r0"), "m0r0")

    def test_master_switch_off_is_inert(self):
        os.environ["ARC3_WINPATH"] = "0"
        sess = FakeSession()
        wp.begin_session(sess)
        self.assertNotIn(id(sess), wp._SESSIONS)
        self.assertFalse(wp.maybe_replay(sess))
        self.assertFalse(wp.dead_skip(sess))


if __name__ == "__main__":
    unittest.main()
