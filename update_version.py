import argparse

Parser = argparse.ArgumentParser(description="update_version", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
Parser.add_argument('version', help='version')
args = Parser.parse_args()

with open("pyproject.toml", "r") as f:
    lines = f.readlines()

with open("pyproject.toml", "w") as f:
    for line in lines:
        if "version =" in line:
            f.write('version = "{}"\n'.format(args.version))
        else:
            f.write(line)