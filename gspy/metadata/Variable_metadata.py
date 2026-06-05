import os
from os.path import splitext
import json
import yaml
from pprint import pprint
import csv
import re

class Variable_metadata(dict):
    """Handler class for user defined metadata. Allows us to check a users input parameters in the backend """

    def __init__(self, **kwargs):

        for col in kwargs.keys():

            missing = [x for x in self.required_keys if not x in kwargs[col]]
            if len(missing) > 0:
                raise ValueError(f"Missing {missing} from {col} in {self.key} dict")

            units = kwargs[col]['units']
            if '$' in units:
                kwargs[col]['units'] = r'{}'.format(units)

        for key, value in kwargs.items():
            if key != "dimensions":
                self[key] = value

    @classmethod
    def read_csv(cls, filename):

        number_pattern = re.compile(r"[-+]?\d+(?:\.\d+)?")
        def _to_number(s):
            # Convert numeric text to int if possible, else float
            return int(s) if re.fullmatch(r"[-+]?\d+", s) else float(s)

        if filename is None:
            return {}
        
        required_keys = ['variable_name','standard_name','long_name','units','null_value']
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
        return data

    @staticmethod
    def key():
        return 'variables'

    @property
    def required_keys(self):
        return ('units',
                'standard_name',
                'long_name',
                'null_value'
                )


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
            lx = x.lower()
            if lx == "true":
                out.append(True)
            elif lx == "false":
                out.append(False)
            elif lx in ("none", "null"):
                out.append(None)
            else:
                try:
                    out.append(int(x))
                except ValueError:
                    try:
                        out.append(float(x))
                    except ValueError:
                        out.append(x)  # keep as string
        return out

    # Scalar conversions (outside of list context)
    lx = s.lower()
    if lx == "true":
        return True
    if lx == "false":
        return False
    if lx in ("none", "null"):
        return None
    try:
        return int(s)
    except ValueError:
        try:
            return float(s)
        except ValueError:
            return s