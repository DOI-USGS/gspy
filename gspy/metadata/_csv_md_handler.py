import re
import csv
import json
from .md_file_handler import __cell, _parse_cell, _parse_dict

EMPTY = object()

def read_csv(filename, table=True, **kwargs):

    if table:
        return read_variable_table(filename, **kwargs)

    with open(filename, newline="") as f:
        rows = list(csv.reader(f, **kwargs))

    source_rows = {}

    # parse each cell individually.
    # this will honor yml syntax like comments and converts to python basic types.
    cleaned = []
    for source_row, row in enumerate(rows, start=1):
        row = [_parse_cell(v) for v in row]
        # remove empty cells at the end of rows.
        while row and row[-1] is EMPTY:
            row.pop()

        if row:
            source_rows[len(cleaned)] = source_row
            cleaned.append(row)

    rows = cleaned
    return _parse_dict(source_rows, rows, row=0)[0]

def to_csv(metadata, filename):
    def emit(d, depth=0):
        out = []

        for k, v in d.items():

            # key row (indented by empty cells)
            row = [""] * depth + [__cell(k)]

            # dict
            if isinstance(v, dict):
                out.append(row)
                out += emit(v, depth + 1)

            # 1D list
            elif isinstance(v, list) and (not v or not isinstance(v[0], list)):
                row.append(":1D")
                out.append(row)
                for x in v:
                    out.append([""] * (depth + 1) + [__cell(x)])

            # 2D table
            elif isinstance(v, list) and v and isinstance(v[0], list):
                row.append(":2D")
                out.append(row)
                for r in v:
                    out.append([""] * (depth + 1) + [__cell(rr) for rr in r])

            # scalar
            else:
                row.append(__cell(v))
                out.append(row)

        return out

    rows = emit(metadata)
    with open(filename, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(rows)

def read_variable_table(filename, **kwargs):

    if filename is None:
        return {'variables':{}}

    required_keys = ['variable_name','standard_name','long_name','units','missing_value']
    with open(filename, mode="r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError("CSV must have a header row.")
        headers = [h.strip() for h in reader.fieldnames if len(h) > 0]
        missing = [x for x in required_keys if not x in headers]
        if len(missing) > 0:
            raise ValueError(f"Missing column(s) {missing} from CSV metadata file")
        attrs = [h for h in headers if h != 'variable_name']

        data = {}
        for rn,row in enumerate(reader):
            outer_key = row.get('variable_name')
            if outer_key == '':
                raise ValueError(f"Missing variable name at row {rn} with contents {row}")
            # Build inner dict from the remaining columns
            inner = {}
            for k in attrs:
                val = row.get(k)
                if val == '':
                    if k in required_keys:
                        if k == 'standard_name':
                            inner[k] = outer_key.replace(' ','_').lower()
                        else:
                            inner[k] = 'not_defined'
                else:
                    inner[k] = coerce_value(val.strip())
            data[outer_key] = inner
    return {'variables': data}

def coerce_value(s: str):
    """
    Convert a CSV string field into a typed Python value.
    Handles:
    - empty/whitespace -> None
    - JSON lists/dicts/numbers/booleans/null
    - Python literals via ast.literal_eval
    - Bare list tokens like [text, dkdkd] (no quotes)
    - numbers (int/float)
    - booleans ('true'/'false')
    Otherwise returns the cleaned string.
    """
    if s is None:
        return None
    s = s.strip()
    if s == "":
        return None

    # Try JSON first (strict, fast)
    if (s.startswith("[") and s.endswith("]")) or (s.startswith("{") and s.endswith("}")):
        try:
            return json.loads(s)
        except json.JSONDecodeError:
            # fall through
            pass

    # Try Python literal (handles quotes, tuples, dicts, numbers, booleans)
    try:
        import ast
        return ast.literal_eval(s)
    except Exception:
        pass

    # Handle bare bracketed lists like [text, dkdkd]
    if s.startswith("[") and s.endswith("]"):
        inner = s[1:-1].strip()
        if inner == "":
            return []
        # Split on commas that are not inside nested brackets/quotes (simple case)
        # Since there are no quotes, a basic split is fine:
        items = [x.strip() for x in inner.split(",")]
        # Strip any accidental surrounding quotes and coerce each token
        out = []

        for x in items:
            # Remove wrapping quotes if present
            x = re.sub(r"""^(['"])(.*)\1$""", r"\2", x)
            # Convert to bool/int/float when possible
            out.append(_get(x))
        return out

    # Scalar conversions (outside of list context)
    return _get(s)

def _get(this):
    match this.lower():
        case "true":
            return True
        case "false":
            return False
        case "none":
            return None
        case "null":
            return None
        case _:
            try:
                return int(this)
            except ValueError:
                try:
                    return float(this)
                except ValueError:
                    return this

