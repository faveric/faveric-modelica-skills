"""Accepted gaps: an owner decision to go without one gate, recorded in the issue header.

  accepted_gaps:
    - {gate: G5, owner: <name>, date: 2026-01-31, reason: <why the gate cannot or should not run>}

Granular: one entry per gate. Any accepted gap means the model is at L0 for that gate and can never
claim "has been verified". The gate's own result stays in the record; acceptance only stops it from
failing the run. G10 and RECORD cannot be accepted: they judge the evidence itself.
"""
ACCEPTABLE = ("G1", "G2", "G3", "G5", "G6a", "G6b", "G8", "G9")


def parse(spec):
    """Return ({gate: {owner, date, reason}}, [problems])."""
    gaps, problems = {}, []
    for i, g in enumerate(spec.get("accepted_gaps") or []):
        gate = str((g or {}).get("gate", "")).strip()
        if gate not in ACCEPTABLE:
            problems.append(f"accepted_gaps[{i}]: gate {gate!r} cannot be accepted (allowed: {', '.join(ACCEPTABLE)})")
            continue
        if gate in gaps:
            problems.append(f"accepted_gaps: {gate} listed twice")
        for key in ("owner", "reason"):
            if not str(g.get(key) or "").strip():
                problems.append(f"accepted_gaps[{i}] ({gate}): '{key}' is required")
        gaps[gate] = {"owner": str(g.get("owner") or "").strip(), "date": str(g.get("date") or "").strip(),
                      "reason": " ".join(str(g.get("reason") or "").split())}
    if gaps and spec.get("level") != "L0":
        problems.append(f"accepted gaps ({', '.join(sorted(gaps))}) require level L0 in the issue, which is {spec.get('level')!r}")
    return gaps, problems


def blocking(res, gaps):
    """Gates that fail and were not accepted."""
    return sorted(g for g, (s, _) in res.items() if s == "fail" and g not in gaps)


def record_values(gaps):
    """Values for the repeated record keyword 'accepted-gap': gate|owner|date|reason."""
    return [f"{g}|{v['owner']}|{v['date']}|{v['reason'].replace('|', '/')}" for g, v in sorted(gaps.items())]


def acceptance_text(gaps):
    return "accepted with skipped gates: " + ", ".join(sorted(gaps)) if gaps else "none"
