import os, sys
sys.path.insert(0, '.')
import inference.agent.tool_agent as t

# 1. extraction
msgs = [
    {"role": "assistant", "reasoning_content": "I should write `LEVEL 1 NOTES:` and states the mechanics you verified ... at most 4 short sentences"},
    {"role": "assistant", "content": "LEVEL 1 NOTES: Arrow keys move the blue 2x2 block; touching yellow coins collects them; the level ends when all coins are collected. Solved by sweeping rows.\n\nNow acting."},
    {"role": "user", "content": "LEVEL 2 NOTES: user text must be ignored entirely here ok"},
    {"role": "assistant", "content": [{"type": "text", "text": "level 2 notes: Pushing the grey box onto the red pad opens the door; then reach the door with the player."}]},
]
n = t._extract_level_notes(msgs)
assert set(n) == {1, 2}, n
assert n[1].startswith("Arrow keys") and "Now acting" not in n[1], n[1]
print("extract ok:", n)

# 2. system prompt hint toggle
os.environ.pop("ARC3_EXPERIMENT_HINT", None)
p0 = t._build_system_prompt(tool_output_tokens=3072)
assert "as few in-game actions as possible" in p0
os.environ["ARC3_EXPERIMENT_HINT"] = "1"
p1 = t._build_system_prompt(tool_output_tokens=3072)
assert "as few in-game actions as possible" not in p1 and "thinking time is scarcer" in p1
print("hint ok, prompt delta chars:", len(p1) - len(p0))

# 3. refresh on a dummy object bound to the real methods
class A: pass
a = A()
a._arc3_base_system_prompt = "BASE"
a._system_prompt = "BASE"
a._arc3_level_notes = {}
a._arc3_level_actions = {1: 23}
a._arc3_level_notes_block = t.ToolAgent._arc3_level_notes_block.__get__(a)
refresh = t.ToolAgent._arc3_refresh_level_notes.__get__(a)
sm = {"role": "system", "content": "BASE"}
out = refresh(msgs, sm)
assert out is not sm and out["content"].startswith("BASE\n\n## Notes from levels") and "about 23 actions" in out["content"]
assert a._system_prompt == out["content"] and sm["content"] == "BASE"
out2 = refresh([], {"role": "system", "content": a._system_prompt})
assert out2["content"] == out["content"]  # stable, notes kept
other = {"role": "system", "content": "SUMMARY PROMPT"}
assert refresh(msgs, other) is other
bad = refresh(None, sm)  # must not raise
print("refresh ok\n", out["content"])

# 4. trim integration on a real ToolAgent if constructible
os.environ["ARC3_LEVEL_NOTES"] = "1"
import inspect
print("ToolAgent init sig:", str(inspect.signature(t.ToolAgent.__init__))[:300])
