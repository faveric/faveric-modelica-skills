"""Load a spec: YAML front matter between '---' lines."""
import re

import yaml
from pathlib import Path


def read_text(path):
    """Read as UTF-8 (BOM tolerated), never the platform default: on Windows that is cp1252 and rejects bytes like 0x81."""
    return Path(path).read_text(encoding="utf-8-sig", errors="replace")


def load_spec(path):
    text = read_text(path)
    if not text.startswith("---"):
        raise ValueError("spec has no front matter")
    _, fm, _body = text.split("---", 2)
    return _num(yaml.safe_load(fm))


def _num(x):
    """PyYAML reads 5.0e6 (no exponent sign) as a string; coerce numeric-looking strings."""
    if isinstance(x, dict):
        return {k: _num(v) for k, v in x.items()}
    if isinstance(x, list):
        return [_num(v) for v in x]
    if isinstance(x, str):
        try:
            return float(x) if re.fullmatch(r"[+-]?\d+(\.\d*)?[eE][+-]?\d+", x.strip()) else x
        except ValueError:
            return x
    return x
