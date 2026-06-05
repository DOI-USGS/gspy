import csv
from .md_file_handler import __cell, _parse_cell, _parse_dict

EMPTY = object()

def read_csv(filename, **kwargs):
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