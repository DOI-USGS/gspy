from collections.abc import Iterable
import yaml

EMPTY = object()

def _parse_cell(value):
    if value is None: # this happens when cell is empty in an xlsx
        return EMPTY

    text = str(value).strip()
    if not text:
        return EMPTY

    try:
        return yaml.safe_load(text)
    except Exception:
        return None

def _indent(this):
    return next((i for i, v in enumerate(this) if v is not EMPTY), -1)

def _parse_dict(source_rows, rows, row, depth=0):
        out = {}
        _start_row = row-1

        nrows = len(rows)


        while row < nrows:
            cur = rows[row]
            ind = _indent(cur)

            if ind < depth: # we decreased the indent. that means this block has ended.
                break
            if ind != depth: # we did not encounter an indent where expected.
                raise ValueError(f"Unexpected indent on row {source_rows[row]}")

            key = cur[ind]
            vals = [v for v in cur[ind + 1:] if v is not EMPTY]
            tag = str(vals[0]).lower() if len(vals) == 1 else None

            if not vals:
                # if the next row indent is not increased by 1, then assume that this was just an empty entry, which is valid.
                if  ((row+1 >= nrows) or (_indent(rows[row+1]) <= ind)):
                    val, row = '', row+1
                else: #parse it as a nested dict.
                    val, row = _parse_dict(source_rows, rows, row + 1, depth + 1)

            elif tag in {":list", ":array", ":1d"}:
                val, row = _parse_list(source_rows, rows, row + 1, depth + 1)

            elif tag in {":table", ":table:rows", ":2d", ":2d:rows"}:
                val, row = _parse_table(source_rows, rows, row + 1, depth + 1)

            elif tag in {":table:cols", ":table:columns", ":2d:cols", ":2d:columns"}:
                val, row = _parse_table(source_rows, rows, row + 1, depth + 1)
                val = [list(c) for c in zip(*val)]

            else:
                val = vals[0] if len(vals) == 1 else vals
                row += 1

            out[key] = val

        if not out:
            raise ValueError(f"Unexpected empty block begining on row {source_rows[_start_row]}.")

        return out, row

def _parse_list(source_rows, rows, row, depth):
    # parses a row into a scalar or a 1D list
    out = []

    nrows = len(rows)

    while row < nrows:
        cur = rows[row]
        ind = _indent(cur)

        if ind < depth:
            break
        if ind != depth:
            raise ValueError(f"Unexpected indent on row {source_rows[row]}")

        out.append(_tail(cur, depth))
        row += 1

    return out, row

def _parse_table(source_rows, rows, row, depth):
    # parses a 2D set of cells
    out = []

    nrows = len(rows)

    while row < nrows:
        cur = rows[row]
        ind = _indent(cur)

        if ind < depth:
            break
        if ind != depth:
            raise ValueError(f"Unexpected indent on row {source_rows[row]}")

        out.append([v for v in cur[depth:] if v is not EMPTY])
        row += 1

    return out, row

def _tail(row, col):
    vals = [v for v in row[col:] if v is not EMPTY]
    if not vals:
        return None
    return vals[0] if len(vals) == 1 else vals

def __cell(v):
    if isinstance(v, str) or not isinstance(v, Iterable):
        return str(v)
    return f"[{', '.join(__cell(item) for item in v)}]"