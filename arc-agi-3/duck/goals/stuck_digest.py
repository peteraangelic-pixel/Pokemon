"""Compact digest of the stuck level from an agent transcript (for failure classification)."""
import re, sys
TAGS = r'(THINKING|TOOL CALL: python|MODEL RESPONSE META|ANALYZER STATUS|USER PROMPT|SYSTEM PROMPT|TOOL RESULT: python)'

def segments(text):
    parts = re.split(r'\n?\[' + TAGS + r'\]\n', text)
    level = 1; out = []
    for i in range(1, len(parts) - 1, 2):
        tag, body = parts[i], parts[i + 1]
        if tag == "USER PROMPT":
            m = re.search(r"Current state: step \d+, level (\d+)", body)
            if m: level = int(m.group(1))
        out.append((level, tag, body))
    return out

def digest(path, stuck_level=None, tail=1500, goal_lines=10):
    seg = segments(open(path, errors="replace").read())
    if stuck_level is None: stuck_level = max(l for l, *_ in seg)
    s = [(t, b) for l, t, b in seg if l == stuck_level]
    th = [b for t, b in s if t == "THINKING"]
    goal = []
    for b in th:
        for line in b.splitlines():
            if re.search(r"win condition|goal is|the goal|to win|level complete|objective", line, re.I):
                goal.append(line.strip()[:300])
    print(f"## {path.split('/')[-1]} stuck level {stuck_level}: {len(th)} thinking blocks, {sum(map(len, th))} chars")
    print("### goal statements (first/last)")
    for line in (goal[:goal_lines // 2] + ["..."] + goal[-goal_lines // 2:]) if len(goal) > goal_lines else goal:
        print("-", line)
    for b in th[-2:]:
        print("### thinking tail\n" + b[-tail:])

if __name__ == "__main__":
    digest(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else None)
