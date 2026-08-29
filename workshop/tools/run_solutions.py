"""Execute the solutions notebooks to check that every cell runs.

The solutions notebooks live in ``solutions/`` but their paths are written
relative to the workshop root, which is where a participant runs Jupyter from.
So they are executed with the root as the working directory.

Usage
-----
    python tools/run_solutions.py

"""
import sys
from pathlib import Path

import matplotlib
import nbformat
from nbclient import NotebookClient

matplotlib.use('Agg')

HERE = Path(__file__).resolve().parent.parent

NOTEBOOKS = ['solutions/1_skytem_from_scratch_solutions.ipynb',
             'solutions/2_tempest_aseg_solutions.ipynb']


def run(path):
    notebook = nbformat.read(str(path), as_version=4)
    client = NotebookClient(notebook, timeout=1200, kernel_name='python3',
                            resources={'metadata': {'path': str(HERE)}})
    client.execute()
    nbformat.write(notebook, str(path))


failures = 0
for name in NOTEBOOKS:
    print(f"executing {name} ...", flush=True)
    try:
        run(HERE / name)
    except Exception as e:
        failures += 1
        print(f"  FAILED: {type(e).__name__}")
        print(f"  {e}"[:4000])
    else:
        print("  ok")

sys.exit(1 if failures else 0)
