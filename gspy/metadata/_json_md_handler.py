import json

def read_json(filename):
    with open(filename) as f:
        out = json.loads(f.read())
    return out

def to_json(dict, filename, indent=4, **kwargs):
    with open(filename, "w") as f:
        json.dump(dict, f, indent=indent)