"""Check that no exercise can be skipped without the notebook complaining.

An exercise that quietly succeeds when left as ``...`` is worse than no exercise
at all: the user moves on believing they answered it.  For every exercise cell,
this builds the solutions notebook with that one cell reverted to its blank
version and runs it, expecting the run to stop with an error.  A run that
finishes cleanly means that blank is invisible and needs restructuring.

Run from the workshop root:

    python tools/audit_blanks.py

"""
import nbformat as nbf
from nbclient import NotebookClient
from nbclient.exceptions import CellExecutionError
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent

PAIRS = [
    ('1_skytem_from_scratch.ipynb', 'solutions/1_skytem_from_scratch_solutions.ipynb'),
    ('2_tempest_aseg.ipynb', 'solutions/2_tempest_aseg_solutions.ipynb'),
]

BANNER = '# EXERCISE - complete the lines marked with ...'


def label_for(notebook, index):
    """The nearest ``### Exercise n.n`` heading above a cell, for reporting."""
    for cell in reversed(notebook.cells[:index]):
        if cell.cell_type == 'markdown':
            for line in cell.source.splitlines():
                if line.startswith('### Exercise'):
                    # With the index too, because one heading can cover several cells
                    return f"{line.lstrip('# ').strip()} (cell {index})"
    return f'cell {index}'


def exercise_cells(exercise, solution):
    """Indices where the handout differs from the solution, with the blank source."""
    assert len(exercise.cells) == len(solution.cells), \
        "handout and solution have drifted apart - rebuild both"

    return [(i, blank.source)
            for i, (blank, filled) in enumerate(zip(exercise.cells, solution.cells))
            if BANNER in blank.source and blank.source != filled.source]


def fails_when_blank(solution_path, index, blank_source):
    """True if reverting one cell to its blank stops the run with an error."""
    notebook = nbf.read(solution_path, as_version=4)
    notebook.cells[index].source = blank_source

    # allow_errors=False so the run stops at the first error rather than pushing
    # on through every remaining cell.  Stopping early is the outcome we want.
    client = NotebookClient(notebook, timeout=1200, kernel_name='python3',
                            allow_errors=False,
                            resources={'metadata': {'path': str(HERE)}})
    try:
        client.execute()
    except CellExecutionError:
        return True
    return False


def main():
    ok = True

    for exercise_name, solution_name in PAIRS:
        exercise = nbf.read(HERE / exercise_name, as_version=4)
        solution = nbf.read(HERE / solution_name, as_version=4)
        cells = exercise_cells(exercise, solution)

        print(f"\n{exercise_name}  ({len(cells)} exercise cells)")

        caught = 0
        for index, blank_source in cells:
            label = label_for(exercise, index)
            if fails_when_blank(HERE / solution_name, index, blank_source):
                caught += 1
                print(f"  fails visibly   {label}")
            else:
                ok = False
                print(f"  SILENT PASS     {label}  <-- left blank and nothing complained")

        print(f"  {caught}/{len(cells)} exercise cells fail visibly when left blank")

    print("\nAUDIT PASSED" if ok else "\nAUDIT FAILED")
    raise SystemExit(0 if ok else 1)


if __name__ == '__main__':
    main()
