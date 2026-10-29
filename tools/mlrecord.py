#!/usr/bin/env python3
"""Read, check and refresh SRMD credibility records (local names only; namespaces ignored).

  python3 tools/mlrecord.py check  <record.xml> [--root DIR]
  python3 tools/mlrecord.py set    <record.xml> <classification-type> <keyword> <value>

Not validated against the published SRMD XSD or the MIC Core Schematron.
"""
import argparse, hashlib, sys
import xml.etree.ElementTree as ET
from pathlib import Path

VERIFIED = "has been verified"
VER_VALUES = ("has not been verified", "has been verified")
VAL_VALUES = ("has not been validated", "has been validated", "validated with limitations")
GATE_STATUSES = ("pass", "fail", "open", "skip")
VALIDATED = ("has been validated", "validated with limitations")
VER_KEY = "verification-validation.verification-status"
VAL_KEY = "verification-validation.validation-status"
MIC_MANDATORY = ["administrative-data.model.name", "administrative-data.model.supplier",
                 "administrative-data.model.confidentiality-level", "administrative-data.release"]


ET.register_namespace("srmd", "urn:placeholder:srmd")


def _local(tag):
    return tag.rsplit("}", 1)[-1]


def load(path):
    parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True))
    return ET.parse(path, parser=parser)


def entries(tree):
    """Return {classification_type: [(keyword, value, element)]}."""
    out = {}
    for cl in tree.getroot().iter():
        if not isinstance(cl.tag, str) or _local(cl.tag) != "Classification":
            continue
        lst = out.setdefault(cl.get("type"), [])
        for e in cl:
            if isinstance(e.tag, str) and _local(e.tag) == "Entry":
                lst.append((e.get("keyword"), (e.text or "").strip(), e))
    return out


def values(ents, ctype, keyword):
    return [v for k, v, _ in ents.get(ctype, []) if k == keyword]


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def ext_type(ents):
    cands = [t for t in ents if t and t != "org.mic-core.mic-core"]
    return cands[0] if cands else None


def gate_status(ents, ext, gate):
    vs = values(ents, ext, f"gate.{gate}")
    return vs[0].split(";")[0].strip().lower() if vs else None


def combined_digest(ents, ext, root):
    """sha256 over the sorted (path, file hash) pairs listed as model.file entries, current on disk."""
    h = hashlib.sha256()
    for v in sorted(values(ents, ext, "model.file")):
        rel = v.partition("|")[0]
        p = Path(root) / rel
        h.update(rel.encode() + b"\0" + (sha256(p).encode() if p.exists() else b"missing") + b"\0")
    return h.hexdigest()


def gate_hash(value):
    for part in value.split(";"):
        part = part.strip()
        if part.startswith("hash="):
            return part[5:]
    return None


def check(path, root):
    """Return a list of (severity, message). severity: 'fail' or 'open'."""
    tree = load(path)
    ents = entries(tree)
    f = []
    mic = "org.mic-core.mic-core"
    if mic not in ents:
        return [("fail", "no org.mic-core.mic-core classification")]
    for k in MIC_MANDATORY:
        if not values(ents, mic, k):
            f.append(("fail", f"MIC Core mandatory entry missing: {k}"))
    ext = ext_type(ents)
    if ext is None:
        f.append(("fail", "no extension classification (gates, hashes) in record"))
        return f
    # freshness
    for v in values(ents, ext, "model.file"):
        rel, _, h = v.partition("|")
        p = Path(root) / rel
        if not p.exists():
            f.append(("fail", f"G10: covered file missing: {rel}"))
        elif sha256(p) != h.strip():
            f.append(("fail", f"G10: stale record, hash differs for {rel}"))
    cur = combined_digest(ents, ext, root)
    for k, v, _ in ents.get(ext, []):
        if k.startswith(("gate.", "mirror.")):
            st = v.split(";")[0].strip().lower()
            gh = gate_hash(v)
            if gh is None and st in ("pass", "fail"):
                f.append(("fail", f"G10: {k} has a result but no hash of the files it was evaluated on"))
            elif gh is not None and gh != cur:
                f.append(("fail", f"G10: {k} was evaluated on different file versions than the current ones"))
    ver = (values(ents, mic, VER_KEY) or ["has not been verified"])[0]
    val = (values(ents, mic, VAL_KEY) or ["has not been validated"])[0]
    for key, v, allowed in ((VER_KEY, ver, VER_VALUES), (VAL_KEY, val, VAL_VALUES)):
        if v not in allowed:
            f.append(("fail", f"{key}: {v!r} is not one of {list(allowed)} (exact strings, case-sensitive)"))
    for k, v, _ in ents.get(ext, []):
        if k.startswith("gate.") and v.split(";")[0].strip().lower() not in GATE_STATUSES:
            f.append(("fail", f"{k}: status {v.split(';')[0].strip()[:40]!r} is not one of {list(GATE_STATUSES)}; "
                              "the status is the first word only. Put explanations after ';' or in a 'note.<key>' entry, "
                              "and use an accepted gap in the issue for a gate you decided to go without"))
    gaps = values(ents, ext, "accepted-gap")
    if gaps:
        names = ", ".join(sorted(v.split("|")[0] for v in gaps))
        if ver == VERIFIED:
            f.append(("fail", f"claims '{VERIFIED}' with accepted gaps ({names}): accepted gaps keep the model below it"))
        if (values(ents, ext, "intended-use.level") or ["L0"])[0] != "L0":
            f.append(("fail", f"accepted gaps ({names}) are only allowed at level L0"))
    need_ver = ["G1", "G2", "G3", "G5", "G6a", "G8", "G9"]  # G10 is judged by the digests, never stored
    level = (values(ents, ext, "intended-use.level") or ["L0"])[0]
    if ver == VERIFIED and level == "L1":
        if not any(v.strip().lower().startswith("done:") for v in values(ents, ext, "solution-verification")):
            f.append(("fail", f"claims '{VERIFIED}' at L1 without a 'solution-verification' entry starting 'done:'"))
        for v in values(ents, ext, "source"):
            parts = v.split("|")
            key = parts[0]
            if len(parts) != 3 or parts[2].strip() != "numeric-checked":
                f.append(("fail", f"claims '{VERIFIED}' at L1 but source {key} is not numeric-checked"))
    if ver == VERIFIED:
        for g in need_ver:
            s = gate_status(ents, ext, g)
            if s != "pass":
                f.append(("fail", f"claims '{VERIFIED}' but gate {g} is {s or 'absent'}"))
        if not " ".join(values(ents, ext, "coherence-checks")).startswith("passed"):
            f.append(("fail", f"claims '{VERIFIED}' without a passed coherence-checks entry"))
    if val in VALIDATED:
        s = gate_status(ents, ext, "G6b")
        if s != "pass":
            f.append(("fail", f"claims '{val}' but gate G6b is {s or 'absent'}"))
        if ver != VERIFIED:
            f.append(("fail", f"claims '{val}' while not verified"))
    return f


def rehash(path, root):
    tree = load(path)
    ents = entries(tree)
    ext = ext_type(ents)
    n = 0
    for k, v, el in ents.get(ext, []):
        if k == "model.file":
            rel = v.partition("|")[0]
            el.text = f"{rel}|{sha256(Path(root) / rel)}"
            n += 1
    tree.write(path, encoding="utf-8", xml_declaration=True)
    return n


def set_entry(path, ctype, keyword, value, create=True):
    """Set an entry's value; create it when absent (never a silent no-op)."""
    tree = load(path)
    ents = entries(tree)
    for k, v, el in ents.get(ctype, []):
        if k == keyword:
            el.text = value
            tree.write(path, encoding="utf-8", xml_declaration=True)
            return True
    if not create:
        return False
    for cl in tree.getroot().iter():
        if isinstance(cl.tag, str) and _local(cl.tag) == "Classification" and cl.get("type") == ctype:
            ns = cl.tag[: cl.tag.index("}") + 1] if cl.tag.startswith("{") else ""
            new = ET.SubElement(cl, ns + "Entry", {"keyword": keyword})
            new.text = value
            tree.write(path, encoding="utf-8", xml_declaration=True)
            return True
    raise KeyError(f"classification {ctype!r} not found in record")


def replace_entries(path, ctype, keyword, vals):
    """Replace all entries of a keyword (for repeated keys such as model.file and source)."""
    tree = load(path)
    for cl in tree.getroot().iter():
        if isinstance(cl.tag, str) and _local(cl.tag) == "Classification" and cl.get("type") == ctype:
            ns = cl.tag[: cl.tag.index("}") + 1] if cl.tag.startswith("{") else ""
            for e in [e for e in cl if isinstance(e.tag, str) and e.get("keyword") == keyword]:
                cl.remove(e)
            for v in vals:
                ET.SubElement(cl, ns + "Entry", {"keyword": keyword}).text = v
            tree.write(path, encoding="utf-8", xml_declaration=True)
            return
    raise KeyError(ctype)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["check", "set"])
    ap.add_argument("record")
    ap.add_argument("rest", nargs="*")
    ap.add_argument("--root", default=".")
    a = ap.parse_args(argv)
    if a.cmd == "check":
        res = check(a.record, a.root)
        for sev, msg in res:
            print(f"{sev.upper()}: {msg}")
        return 1 if any(s == "fail" for s, _ in res) else 0
    if a.rest[1].startswith(("gate.", "mirror.")) or a.rest[1] in ("model.file", "source", "intended-use.level", "accepted-gap", "acceptance"):
        print("refused: generated keys are written by evals/run_gates.py --write only")
        return 2
    ok = set_entry(a.record, a.rest[0], a.rest[1], a.rest[2])
    print("set" if ok else "entry not found")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
