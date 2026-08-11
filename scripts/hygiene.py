#!/usr/bin/env python3
"""Fail if any given file contains machine-specific absolute paths or leaked
personal/internal identities.

This is the local release-hygiene check for the USGS ``gspy`` release process.
Sphinx/sphinx-gallery bakes the builder's absolute paths into generated docs
(tracebacks, warnings), which then get committed under ``docs/``; the same docs
and metadata can also carry personal free-mail addresses or internal DOI
hostnames. This checker blocks both classes from entering the repository.

Absolute-path patterns (all operating systems):
  * ``/Users/<name>``            macOS home directories
  * ``/home/<name>/``            Linux home directories
  * ``<drive>:\\Users\\``          Windows profile paths (back- or forward-slash)

Identity-leak patterns:
  * personal free-mail addresses  (gmail/yahoo/hotmail/outlook/aol/icloud/...)
  * internal DOI/USGS hostnames   (``*.gs.doi.net``, ``igsk*`` build machines)

Deliberately NOT flagged, to avoid false positives:
  * System roots such as ``/usr/``, ``/System/``, ``/opt/`` (not user-specific)
  * JSON/string escapes like ``e:\\n`` in notebooks (the ``Users`` segment is
    required after a Windows drive letter)
  * Official ``@usgs.gov`` / ``@contractor.usgs.gov`` / ``@doi.gov`` addresses
    (these are the intended public contact/author identities)

Usage:
    check_absolute_paths.py FILE [FILE ...]

Exit status is non-zero when any offending pattern is found, listing each hit as
``path:line: <match>`` so it doubles as a pre-commit hook and a manual check.
"""
from __future__ import annotations

import re
import sys

# --- Absolute paths -------------------------------------------------------
# One matched group per OS-specific home-directory style. A real name segment
# must follow the separator, so a genuine leak (a real username after the
# separator) is caught while documentation placeholders like ``/Users/<name>``
# are not (which lets this file, and docs describing the rule, pass their own
# check).
_NAME = r"[A-Za-z0-9._-]"
PATH_PATTERN = re.compile(
    rf"/Users/{_NAME}|/home/{_NAME}+/|[A-Za-z]:[\\/]+Users[\\/]+{_NAME}"
)

# --- Identity leaks -------------------------------------------------------
# Personal free-mail addresses that should never be a committed contact/author
# identity in a USGS release. Official ``*.usgs.gov`` / ``doi.gov`` addresses are
# intentionally absent so they pass.
_FREEMAIL_DOMAINS = (
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com",
    "aol.com", "icloud.com", "me.com", "protonmail.com", "live.com",
)
FREEMAIL_PATTERN = re.compile(
    rf"[A-Za-z0-9._%+-]+@(?:{'|'.join(re.escape(d) for d in _FREEMAIL_DOMAINS)})",
    re.IGNORECASE,
)

# Internal DOI/USGS network hostnames: the ``*.gs.doi.net`` domain and the
# ``igsk...`` build-machine naming convention. These leak internal
# infrastructure and must not ship in a public release.
# A real name segment must precede ``.gs.doi.net`` so documentation
# placeholders like ``*.gs.doi.net`` (and this file's own comments) pass, while
# a genuine ``<hostname>.gs.doi.net`` leak is caught.
HOSTNAME_PATTERN = re.compile(
    r"[A-Za-z0-9._-]+\.gs\.doi\.net|\bigsk[a-z0-9]{4,}",
    re.IGNORECASE,
)

# (label, compiled pattern) pairs applied to every line.
CHECKS = (
    ("absolute path", PATH_PATTERN),
    ("personal email", FREEMAIL_PATTERN),
    ("internal hostname", HOSTNAME_PATTERN),
)

# Extensions treated as binary and skipped outright.
BINARY_EXTENSIONS = (
    ".zip", ".h5", ".nc", ".png", ".jpg", ".jpeg", ".gif", ".pdf",
    ".tif", ".tiff", ".ico", ".woff", ".woff2", ".ttf", ".eot",
)


def file_is_binary(data: bytes) -> bool:
    """Treat a file as binary if it has a NUL byte in its first block."""
    return b"\x00" in data[:4096]


def scan(path: str) -> list[tuple[int, str, str, str]]:
    """Return ``(line_number, label, match, line_text)`` for each offending line."""
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
    hits: list[tuple[int, str, str, str]] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        for label, pattern in CHECKS:
            match = pattern.search(line)
            if match:
                hits.append(
                    (line_number, label, match.group(0), line.strip()[:120])
                )
    return hits


def main(argv: list[str]) -> int:
    found = False
    for path in argv:
        for line_number, label, match, line in scan(path):
            found = True
            print(f"{path}:{line_number}: {label} [{match}] -> {line}")
    if found:
        print(
            "\nRelease-hygiene violation: machine-specific absolute paths, "
            "personal emails, or internal hostnames detected. Remove them "
            "before committing (see scripts/check_absolute_paths.py for the "
            "rules).",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
