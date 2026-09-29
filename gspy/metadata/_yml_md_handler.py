import re

import numpy as np
import yaml

KEY = re.compile(r"^(\s*)([^\s#:'\"-][^:]*?):(\s|$)(.*)$")

def read_yml(filename):
    with open(filename) as f:
        out = yaml.safe_load(f)
    return out

def _inline(rest):
    """The comment after a value, skipping any ``#`` inside quotes."""
    quote = None
    for i, char in enumerate(rest):
        if quote:
            quote = None if char == quote else quote
        elif char in "'\"":
            quote = char
        elif char == "#" and (i == 0 or rest[i - 1].isspace()):
            return rest[i + 1:].strip()
    return None

def read_yml_comments(filename):
    """``{path of keys: {'above': [lines], 'inline': str}}`` for the comments in a yml.

    A comment block directly above a key is that key's; a blank line between them
    cuts it loose. A block opening the file and followed by a blank line is the
    header, filed under the empty path.

    """
    comments, pending, stack, seen_key = {}, [], [], False

    with open(filename) as f:
        for line in f:
            stripped = line.strip()
            if stripped.startswith("#"):
                pending.append(stripped[1:].strip())
                continue
            if not stripped:
                if pending and not seen_key and () not in comments:
                    comments[()] = dict(above=pending)
                pending = []
                continue

            match = KEY.match(line)
            if match is None:
                pending = []
                continue

            indent, key, rest = len(match[1]), match[2].strip(), match[4]
            while stack and stack[-1][0] >= indent:
                stack.pop()
            stack.append((indent, key))
            seen_key = True

            path = tuple(k for _, k in stack)
            inline = _inline(rest)
            if pending or inline:
                comments[path] = dict(above=pending) if pending else {}
                if inline:
                    comments[path]["inline"] = inline
            pending = []

    return comments

def _scalar(value):
    """``value`` as written after its key, quoted only where it would not read back as itself."""
    if isinstance(value, (np.ndarray, np.generic)):
        value = value.tolist()
    if isinstance(value, str):
        try:
            if yaml.safe_load(f"k: {value}") == {"k": value}:
                return value
        except yaml.YAMLError:
            pass
        return "'" + value.replace("'", "''") + "'"
    return value

def to_yml(this, filename, comments=None, **kwargs):

    comments = comments or {}

    def __above(path, indent, file):
        for line in comments.get(path, {}).get("above", []):
            file.write(f"{'    '*indent}# {line}".rstrip() + "\n")

    def __inline(path):
        inline = comments.get(path, {}).get("inline")
        return f" # {inline}" if inline else ""

    def __yaml_dump(this, file, indent=0, path=()):
        if isinstance(this, dict):
            if path:
                __above(path, indent, file)
                file.write(f"{'    '*indent}{path[-1]}:{__inline(path)}\n")
                indent += 1
            for key, value in this.items():
                __yaml_dump(value, file, indent=indent, path=path + (key,))
        else:
            __above(path, indent, file)
            file.write(f"{'    '*indent}{path[-1]}: {_scalar(this)}{__inline(path)}\n")

    with open(filename, "w") as f:
        if () in comments:
            __above((), 0, f)
            f.write("\n")
        __yaml_dump(this, f)
