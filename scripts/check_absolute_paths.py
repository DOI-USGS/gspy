#!/usr/bin/env python3
"""Fail if any given file contains a machine-specific absolute path.

Sphinx/sphinx-gallery bakes the builder's absolute paths into generated docs
(tracebacks, warnings), which then get committed under ``docs/``. This checker
blocks those from entering the repository.

Detected patterns (all operating systems):
  * ``/Users/<name>``            macOS home directories
  * ``/home/<name>/``            Linux home directories
  * ``<drive>:\\Users\\``          Windows profile paths (back- or forward-slash)

Deliberately NOT flagged, to avoid false positives:
  * System roots such as ``/usr/``, ``/System/``, ``/opt/`` (not user-specific)
  * JSON/string escapes like ``e:\\n`` in notebooks (the ``Users`` segment is
    required after a Windows drive letter)

Usage:
    check_absolute_paths.py FILE [FILE ...]

Exit status is non-zero when any offending path is found, listing each hit as
``path:line: <match>`` so it doubles as a pre-commit hook and a manual check.
"""
from __future__ import annotations

import re
import sys

# One matched group per OS-specific home-directory style. A real name segment
# must follow the separator, so a genuine leak (a real username after the
# separator) is caught while documentation placeholders like ``/Users/<name>``
# are not (which lets this file, and docs describing the rule, pass their own
# check).
_NAME = r"[A-Za-z0-9._-]"
PATTERN = re.compile(
    rf"/Users/{_NAME}|/home/{_NAME}+/|[A-Za-z]:[\\/]+Users[\\/]+{_NAME}"
)

# Extensions treated as binary and skipped outright.
BINARY_EXTENSIONS = (
    ".zip", ".h5", ".nc", ".png", ".jpg", ".jpeg", ".gif", ".pdf",
    ".tif", ".tiff", ".ico", ".woff", ".woff2", ".ttf", ".eot",
)


def file_is_binary(data: bytes) -> bool:
    """Treat a file as binary if it has a NUL byte in its first block."""
    return b"\x00" in data[:4096]


def scan(path: str) -> list[tuple[int, str, str]]:
    """Return ``(line_number, match, line_text)`` for each offending line."""
    if path.lower().endswith(BINARY_EXTENSIONS):
        return []
    try:
        with open(path, "rb") as handle:
            data = handle.read()
    except OSError:
        return []
    if file_is_binary(data):
        return []

    text = data.decode("utf-8", "replace")
    hits: list[tuple[int, str, str]] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        match = PATTERN.search(line)
        if match:
            hits.append((line_number, match.group(0), line.strip()[:120]))
    return hits


def main(argv: list[str]) -> int:
    found = False
    for path in argv:
        for line_number, match, line in scan(path):
            found = True
            print(f"{path}:{line_number}: absolute path [{match}] -> {line}")
    if found:
        print(
            "\nMachine-specific absolute paths detected. Remove them before "
            "committing (see scripts/check_absolute_paths.py for the rules).",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
