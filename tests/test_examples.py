"""Smoke tier: run the real gallery scripts end to end.

The scripts read and write with paths relative to their own directory, so they run
in a copy of examples/ under tmp. Nothing here touches the repository tree.

Marked slow: the copy is ~130 MB and the scripts do the full ingest plus plotting.
Deselect with ``-m "not slow"``.
"""
import os
import shutil
import subprocess
import sys

import pytest

from conftest import EXAMPLES

CREATING = "Creating_GS_Files"
INTERACTING = "Interacting_With_GS_Files"


def scripts_in(directory):
    return sorted(p.name for p in (EXAMPLES / directory).glob("plot_*.py"))


# The Interacting examples open NetCDF files that the Creating examples produce, so
# they cannot run in a fresh checkout on their own.
PREREQUISITES = {
    "plot_coordinate_reference_systems.py": f"{CREATING}/plot_csv_skytem.py",
    "plot_xarray_methods.py": f"{CREATING}/plot_aseg_tempest.py",
}

pytestmark = pytest.mark.slow


@pytest.fixture(scope="session")
def examples_copy(tmp_path_factory):
    """examples/ without the NetCDF artifacts, so the scripts have to make them."""
    dest = tmp_path_factory.mktemp("examples") / "examples"
    shutil.copytree(EXAMPLES, dest, ignore=shutil.ignore_patterns("*.nc", "*.zarr"))
    return dest


@pytest.fixture(scope="session")
def run_example(examples_copy):
    """Run a script by "<directory>/<name>", once per session, and cache the result."""
    done = {}

    def run(relpath):
        if relpath not in done:
            script = examples_copy / relpath
            done[relpath] = subprocess.run([sys.executable, script.name],
                                           cwd=script.parent, capture_output=True,
                                           text=True,
                                           env={**os.environ, "MPLBACKEND": "Agg"})
        return done[relpath]

    return run


def assert_ran(result, relpath):
    assert result.returncode == 0, \
        f"{relpath} exited {result.returncode}\n{result.stderr[-3000:]}"


@pytest.mark.parametrize("name", scripts_in(CREATING))
def test_creating_example_runs(run_example, name):
    relpath = f"{CREATING}/{name}"
    assert_ran(run_example(relpath), relpath)


@pytest.mark.parametrize("name", scripts_in(INTERACTING))
def test_interacting_example_runs(run_example, name):
    if name in PREREQUISITES:
        prerequisite = PREREQUISITES[name]
        assert_ran(run_example(prerequisite), prerequisite)

    relpath = f"{INTERACTING}/{name}"
    assert_ran(run_example(relpath), relpath)


def test_the_creating_examples_write_the_files_the_interacting_ones_read(run_example,
                                                                        examples_copy):
    """Documents the coupling: without these two, half the gallery cannot build."""
    for relpath in PREREQUISITES.values():
        assert_ran(run_example(relpath), relpath)

    assert (examples_copy / "data_files" / "skytem_csv" / "skytem.nc").exists()
    assert (examples_copy / "data_files" / "tempest_aseg" / "Tempest.nc").exists()
