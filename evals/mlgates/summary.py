"""One-page summary of a gate run: passed / failed / skipped / needs a human decision, one line of cause each.

Raw per-gate output stays available (`run_gates --raw`); the summary is what a task report quotes.
"""
import re

ORDER = ("failed", "needs a human decision", "skipped", "passed")


def _cause(msg, width=150):
    one = " ".join(str(msg).split())
    first = re.split(r"(?<=[.;])\s", one, maxsplit=1)[0] if len(one) > width else one
    return first if len(first) <= width else first[: width - 1] + "…"


def classify(res, gaps=None, stored=None):
    """{category: [(gate, line)]}. gaps: accepted gaps; stored: {gate: stored record value}."""
    gaps, stored = gaps or {}, stored or {}
    out = {k: [] for k in ORDER}
    for g in sorted(res, key=lambda x: (x[0] == "R", x[0] == "M", len(x), x)):
        s, m = res[g]
        if g in gaps:
            gap = gaps[g]
            out["needs a human decision"].append(
                (g, f"{g} accepted without passing (raw result: {s}); owner {gap['owner']}: {_cause(gap['reason'], 90)}"))
        elif s == "fail":
            out["failed"].append((g, f"{g}: {_cause(m)}"))
        elif s == "open":
            out["needs a human decision"].append((g, f"{g} open: {_cause(m)}"))
        elif s == "skip":
            kept = stored.get(g, "")
            st = kept.split(";")[0].strip().lower()
            note = f" (record keeps its earlier {st}: {_cause(kept.partition(';')[2].strip(), 70)})" if st in ("pass", "fail") else ""
            out["skipped"].append((g, f"{g}: {_cause(m, 90)}{note}"))
        else:
            out["passed"].append((g, g))
    return out


def render(res, gaps=None, stored=None, question=None):
    cl = classify(res, gaps, stored)
    lines = []
    if question:
        lines.append(f"Physical question: {question}")
    for cat in ORDER:
        items = cl[cat]
        if not items:
            continue
        if cat == "passed":
            lines.append(f"PASSED ({len(items)}): " + ", ".join(g for g, _ in items))
        else:
            lines.append(f"{cat.upper()} ({len(items)}):")
            lines += [f"  - {t}" for _, t in items]
    return "\n".join(lines)
