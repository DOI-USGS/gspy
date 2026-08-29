"""Shared fixtures.

Every fixture reads from ``examples/data_files`` and writes only into pytest's
tmp dirs. Nothing here may touch the repository tree.
"""
import os
from pathlib import Path

import numpy as np
import pytest

os.environ.setdefault("MPLBACKEND", "Agg")

import gspy
from gspy import Survey
from gspy.metadata.Metadata import Metadata

REPO = Path(__file__).resolve().parents[1]
DATA = REPO / "examples" / "data_files"
EXAMPLES = REPO / "examples"


@pytest.fixture(scope="session")
def data_path():
    return DATA


def _p(*parts):
    return str(DATA.joinpath(*parts))


# ---------------------------------------------------------------------------
# Survey builders. Each mirrors the example script of the same name, minus the
# plotting and the writes into the repo tree.
# ---------------------------------------------------------------------------

def build_resolve():
    """CSV data + models, with variable metadata merged in from a CSV table."""
    survey = Survey.from_dict(_p("resolve", "data", "Resolve_survey_md.yml"))

    data = survey.gs.add_container("data", **dict(content="raw and processed data"))
    md = Metadata.merge(
        Metadata.read(_p("resolve", "data", "Resolve_data_md_without_variables.yml")),
        Metadata.read(_p("resolve", "data", "Resolve_variable_table_md.csv"), table=True),
    )
    data.gs.add(key="raw_data", data=_p("resolve", "data", "Resolve.csv"),
                metadata_file=md)

    models = survey.gs.add_container("models", **dict(content="inverted models"))
    mod_md = Metadata.merge(
        Metadata.read(_p("resolve", "model", "Resolve_model_md.yml")),
        Metadata.read(_p("resolve", "model", "Resolve_model_variable_table_md.csv"), table=True),
    )
    models.gs.add(key="inverted_models", data=_p("resolve", "model", "Resolve_model.csv"),
                  metadata_file=mod_md)
    return survey


def build_skytem():
    """Multi-dataset survey: two tabular datasets sharing systems, models, rasters."""
    survey = Survey.from_dict(_p("skytem_csv", "data", "skytem_survey.yml"))

    data = survey.gs.add_container("data", **dict(content="raw and processed data"))
    raw = data.gs.add(key="raw_data", data=_p("skytem_csv", "data", "skytem_contractor_data.csv"),
                      metadata_file=_p("skytem_csv", "data", "skytem_contractor_data.yml"),
                      system=Metadata.read(_p("skytem_csv", "data", "skytem_system.yml")))

    # The processed data used fewer gates than the raw data, so the system that
    # recorded it is sliced off the raw data to match before being attached.
    # test_survey asserts this propagates.
    proc_systems = {"skytem_system": raw["skytem_system"].isel(lm_gate_times=np.s_[1:],
                                                              hm_gate_times=np.s_[10:]),
                    "magnetic_system": raw["magnetic_system"]}
    data.gs.add(key="processed_data", data=_p("skytem_csv", "data", "skytem_processed_data.csv"),
                metadata_file=_p("skytem_csv", "data", "skytem_processed_data.yml"),
                system=proc_systems)

    models = survey.gs.add_container("models", **dict(content="Inverted models"))
    models.gs.add(key="inverted_models",
                  data=_p("skytem_csv", "model", "skytem_inverted_models.csv"),
                  metadata_file=_p("skytem_csv", "model", "skytem_inverted_models.yml"))

    data.gs.add(key="depth_to_bedrock",
                data=_p("skytem_csv", "data", "top_dolomite_blocky_lidar.csv"),
                metadata_file=_p("skytem_csv", "data", "bedrock_picks.yml"))

    maps = survey.gs.add_container("derived_maps", **dict(content="raster products"))
    maps.gs.add(key="maps", metadata_file=_p("skytem_csv", "data", "magnetics_bedrock_picks.yml"))
    return survey


def build_tempest():
    """ASEG-GDF2, where the .dfn carries the column definitions."""
    survey = Survey.from_dict(_p("tempest_aseg", "data", "Tempest_survey_md.yml"))

    data = survey.gs.add_container("data", **dict(content="raw data"))
    raw = data.gs.add(key="raw_data", data=_p("tempest_aseg", "data", "Tempest.dat"),
                      metadata_file=_p("tempest_aseg", "data", "Tempest_data_md.yml"))

    models = survey.gs.add_container("models", **dict(content="inverted models"))
    models.gs.add(key="inverted_models", data=_p("tempest_aseg", "model", "Tempest_model.dat"),
                  metadata_file=_p("tempest_aseg", "model", "Tempest_model_md.yml"),
                  system=raw.tempest_system, derived_from=raw)

    maps = survey.gs.add_container("derived_maps", **dict(content="derived maps"))
    maps.gs.add(key="maps", metadata_file=_p("tempest_aseg", "data", "Tempest_raster_md.yml"))
    return survey


def build_loupe():
    """Loupe .dat via explicit file_type, plus Workbench .xyz models."""
    survey = Survey.from_dict(_p("loupe", "data", "LoupeEM_survey_md.yml"))

    data = survey.gs.add_container("data", **dict(content="data container"))
    data.gs.add(key="raw_data", data=_p("loupe", "data", "Kankakee.dat"),
                metadata_file=_p("loupe", "data", "loupe_data_metadata.yml"), file_type="loupe")

    models = survey.gs.add_container("models", **dict(content="models container"))
    models.gs.add(key="inversion", data=_p("loupe", "model", "Kankakee_MOD_dat.xyz"),
                  metadata_file=_p("loupe", "model", "models.yml"))
    return survey


def build_workbench():
    """Workbench .xyz, where gate times are embedded in the file header."""
    survey = Survey.from_dict(_p("workbench", "survey.yml"))

    data = survey.gs.add_container("data", **dict(content="raw data"))
    data.gs.add(key="raw_data",
                data=_p("workbench", "data", "prod_726_729raw_RAW_export.xyz"),
                metadata_file=_p("workbench", "data", "raw_data.yml"))

    models = survey.gs.add_container("models", **dict(content="inverse models"))
    models.gs.add(key="inversion",
                  data=_p("workbench", "model", "prod_726_729_LBv2_bky_MOD_dat.xyz"),
                  metadata_file=_p("workbench", "model", "models.yml"))
    return survey


def build_magnetics():
    """A tabular dataset and a raster dataset in one container."""
    survey = Survey.from_dict(_p("magnetics", "WI_Magnetics_survey_md.yml"))

    data = survey.gs.add_container("magnetic_data",
                                   **dict(content="raw flightline and gridded magnetic data"))
    data.gs.add(key="raw_data", data=_p("magnetics", "WI_Magnetics.csv"),
                metadata_file=_p("magnetics", "WI_Magnetics_raw_data_md.yml"))
    data.gs.add(key="grids", metadata_file=_p("magnetics", "WI_Magnetics_grids_md.yml"))
    return survey


def build_tifs():
    """Rasters only: a 2D grid, and a 3D grid stacked from several tifs."""
    survey = Survey.from_dict(_p("tempest_aseg", "data", "Tempest_survey_md.yml"))

    container = survey.gs.add_container("derived_products", **dict(content="gridded maps"))
    container.gs.add(key="mag_map", metadata_file=_p("tempest_aseg", "data", "Tempest_raster_md.yml"))
    container.gs.add(key="all_maps", metadata_file=_p("tempest_aseg", "data", "Tempest_rasters_md.yml"))
    return survey


BUILDERS = {
    "resolve": build_resolve,
    "skytem": build_skytem,
    "tempest": build_tempest,
    "loupe": build_loupe,
    "workbench": build_workbench,
    "magnetics": build_magnetics,
    "tifs": build_tifs,
}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def resolve_survey():
    return build_resolve()


@pytest.fixture(scope="session")
def skytem_survey():
    return build_skytem()


@pytest.fixture(scope="session")
def tempest_survey():
    return build_tempest()


@pytest.fixture(scope="session")
def loupe_survey():
    return build_loupe()


@pytest.fixture(scope="session")
def workbench_survey():
    return build_workbench()


@pytest.fixture(scope="session")
def magnetics_survey():
    return build_magnetics()


@pytest.fixture(scope="session")
def tifs_survey():
    return build_tifs()


@pytest.fixture(scope="session", params=sorted(BUILDERS))
def survey(request):
    """(name, tree) for each example survey in turn, built once per session.

    Read-only. Anything that writes must use ``roundtrip`` instead, because
    ``to_netcdf`` mutates the tree it writes.
    """
    return request.param, request.getfixturevalue(f"{request.param}_survey")


@pytest.fixture(scope="session", params=sorted(BUILDERS))
def roundtrip(request, tmp_path_factory):
    """(name, survey, reopened) after a write to a temp NetCDF.

    Builds its own survey rather than reusing the ``survey`` fixture: to_netcdf
    stamps attrs onto the tree and deletes survey-level system nodes, which
    would make the read-only assertions depend on test execution order.
    """
    name = request.param
    built = BUILDERS[name]()
    path = tmp_path_factory.mktemp("nc") / f"{name}.nc"
    built.gs.to_netcdf(path)
    return name, built, gspy.open_datatree(path)["survey"]


def gs_leaves(survey, structures=("tabular", "raster")):
    """Dataset nodes that hold ingested data, i.e. not systems or parameters."""
    root = survey.parent if survey.parent is not None else survey
    return [n for n in root.subtree if n.attrs.get("structure") in structures]


def data_row_count(filename):
    """Rows in a delimited text file, excluding the header and blank lines.

    Counting non-empty lines rather than newlines because the example CSVs are
    inconsistent about a trailing newline.
    """
    with open(filename) as f:
        return sum(1 for line in f if line.strip()) - 1
