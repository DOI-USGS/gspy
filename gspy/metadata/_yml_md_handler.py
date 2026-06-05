import yaml

def read_yml(filename):
    with open(filename) as f:
        out = yaml.safe_load(f)
    return out

def to_yml(this, filename, **kwargs):

    def __yaml_dump(this, file, indent=0, key=None):
        if isinstance(this, dict):
            if key is not None:
                file.write(f"{'    '*indent}{key}:\n")
                indent += 1
            for key, value in this.items():
                __yaml_dump(value, file, indent=indent, key=key)
        else:
            file.write(f"{'    '*indent}{key}: {this}\n")

    with open(filename, "w") as f:
        __yaml_dump(this, f)