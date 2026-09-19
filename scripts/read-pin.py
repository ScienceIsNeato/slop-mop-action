#!/usr/bin/env python3
"""Print the slopmop version pin declared in action.yml.

Parsing the file is the point, not a means to an end: the move-major-tag
workflow runs this immediately before repointing `v2`, so an action.yml that
does not load, or has lost its pin, stops the tag move instead of shipping a
broken action to every consumer at once.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

ACTION = Path(__file__).resolve().parents[1] / "action.yml"


def main() -> int:
    try:
        spec = yaml.safe_load(ACTION.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        print(f"action.yml is not valid YAML: {exc}", file=sys.stderr)
        return 1

    try:
        pin = spec["inputs"]["slopmop-version"]["default"]
    except (TypeError, KeyError):
        print(
            "action.yml has no inputs.slopmop-version.default — consumers would "
            "install an unpinned slopmop.",
            file=sys.stderr,
        )
        return 1

    if not isinstance(pin, str) or not pin.strip():
        print(
            f"slopmop-version default is not a version specifier: {pin!r}",
            file=sys.stderr,
        )
        return 1

    print(pin.strip())
    return 0


if __name__ == "__main__":
    sys.exit(main())
