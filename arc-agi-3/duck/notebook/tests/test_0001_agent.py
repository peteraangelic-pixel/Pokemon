import os, sys
sys.path.insert(0, '.')
os.environ.update({"ARC3_LEVEL_NOTES": "1", "ARC3_STUCK_AUDIT_TOKENS": "60000", "ARC3_EXPERIMENT_HINT": "1",
                   "LOCAL_ANALYZER_CONTEXT_WINDOW": "20000", "LOCAL_ANALYZER_MAX_OUTPUT": "2000",
                   "ARC3_CONTEXT_DRAIN_TOKENS": "6000", "ARC3_MEMORY_SECTIONS": "off"})
import inference.agent.tool_agent as t
a = t.ToolAgent(model="flashnext", base_url="http://127.0.0.1:9/v1", api_key="x")
assert "thinking time is scarcer" in a._system_prompt
assert a._arc3_base_system_prompt == a._system_prompt
# build long history: notes in early assistant message
hist = [{"role": "user", "content": "start " + "x" * 3000},
        {"role": "assistant", "content": "LEVEL 1 NOTES: Clicking a tile rotates its row; the goal is to match the target pattern shown top-left. Solved with 6 clicks."}]
for i in range(40):
    hist += [{"role": "user", "content": f"turn {i} " + "y" * 3000}, {"role": "assistant", "content": f"reply {i} " + "z" * 1500}]
msgs = [{"role": "system", "content": a._system_prompt}, *hist]
out = a._trim_messages_for_context(msgs, tools=None)
print("before", len(msgs), "after", len(out), "evicted:", a._has_evicted)
assert len(out) < len(msgs)
assert "## Notes from levels you already solved" in out[0]["content"] and "rotates its row" in out[0]["content"]
assert a._system_prompt == out[0]["content"]
assert not any("LEVEL 1 NOTES" in str(m.get("content")) for m in out[1:])  # original note evicted, survives in system
assert out[1]["role"] == "user"
print("trim integration ok; system prompt grew by", len(out[0]["content"]) - len(a._arc3_base_system_prompt), "chars")

# user prompt: level transition -> notes request; tokens -> audit
summary = {"executed_count": 3, "executed_actions": ["UP", "UP", "LEFT"], "level": 3, "level_transition": True,
           "start_action_num": 10, "end_action_num": 12}
up = a._build_user_prompt(12, valid_actions=["UP", "DOWN", "LEFT", "RIGHT"], previous_step_summary=summary)
assert "LEVEL 2 NOTES:" in up, up[:2000]
a._session_generated_tokens = 130000; a._tokens_at_level_start = 0; a._arc3_audits_on_level = 0
summary2 = dict(summary, level_transition=False, level=3)
up2 = a._build_user_prompt(20, valid_actions=["UP"], previous_step_summary=summary2)
assert "STRATEGY AUDIT: about 130k tokens" in up2 and a._arc3_audits_on_level == 2
up3 = a._build_user_prompt(21, valid_actions=["UP"], previous_step_summary=summary2)
assert "STRATEGY AUDIT" not in up3
a._session_generated_tokens = 181000
assert "STRATEGY AUDIT" in a._build_user_prompt(22, valid_actions=["UP"], previous_step_summary=summary2)
# level transition bookkeeping
a._actions_at_level_start = 5
a._last_step_summary = summary
a._update_summarized_knowledge_from_step_summary()
assert a._arc3_level_actions.get(2) == 7 and a._arc3_audits_on_level == 0, a._arc3_level_actions
print("prompt + bookkeeping ok")
# toggles off -> identical behaviour
for k in ("ARC3_LEVEL_NOTES", "ARC3_STUCK_AUDIT_TOKENS", "ARC3_EXPERIMENT_HINT"): os.environ.pop(k)
b = t.ToolAgent(model="flashnext", base_url="http://127.0.0.1:9/v1", api_key="x")
assert "as few in-game actions as possible" in b._system_prompt
outb = b._trim_messages_for_context([{"role": "system", "content": b._system_prompt}, *hist], tools=None)
assert outb[0]["content"] == b._system_prompt == b._arc3_base_system_prompt
upb = b._build_user_prompt(12, valid_actions=["UP"], previous_step_summary=summary)
assert "NOTES" not in upb
print("toggles-off ok")
