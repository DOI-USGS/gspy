"""Integration tier: build each example survey, assert its shape, round-trip it.

Expected paths and dimension sizes were captured from the pipelines as they
behave today, so a change in what GSPy produces from unchanged input shows up
here as a diff rather than as a silently different NetCDF file.
"""
import gspy
import numpy as np
import pytest
from gspy import Metadata, Survey
from gspy.gs_dataset.Tabular import Tabular
from gspy.gs_datatree.Container import Container
from pyproj import CRS

from conftest import DATA, build_magnetics, data_row_count, gs_leaves

CF_GLOBAL_ATTRS = ("title", "institution", "source", "history", "references")
CF_VAR_ATTRS = ("standard_name", "long_name", "units", "missing_value")

RESOLVE_CSV = str(DATA / "resolve" / "data" / "Resolve.csv")
RESOLVE_MD = str(DATA / "resolve" / "data" / "Resolve_data_md.yml")
# The same variables as Resolve_data_md.yml with the three system sections removed,
# so the couplets it names can only be checked against a system passed separately.
RESOLVE_MD_NO_SYSTEMS = str(DATA / "resolve" / "data" / "Resolve_data_md_nosystems.yml")
SKYTEM_SURVEY_MD = str(DATA / "skytem_csv" / "data" / "skytem_survey.yml")
SKYTEM_SYSTEM_MD = str(DATA / "skytem_csv" / "data" / "skytem_system.yml")
SPATIAL_REF = {"wkid": 3071, "authority": "EPSG", "vertical_crs": "NAVD88"}

EXPECTED_PATHS = {
    "resolve": {
        "data", "models", "data/raw_data", "models/inverted_models",
        "data/raw_data/resolve_system", "data/raw_data/magnetic_system",
        "data/raw_data/radiometric_system",
        "models/inverted_models/inversion_parameters",
    },
    "skytem": {
        "data", "models", "derived_maps",
        "data/raw_data", "data/processed_data", "data/depth_to_bedrock",
        "models/inverted_models", "derived_maps/maps",
        "data/raw_data/skytem_system", "data/raw_data/magnetic_system",
        "data/processed_data/skytem_system", "data/processed_data/magnetic_system",
        "models/inverted_models/inversion_parameters",
    },
    "tempest": {
        "data", "models", "derived_maps", "data/raw_data",
        "models/inverted_models", "derived_maps/maps",
        "data/raw_data/tempest_system", "models/inverted_models/tempest_system",
        "models/inverted_models/inversion_parameters",
        "derived_maps/maps/magnetic_system",
    },
    "loupe": {
        "data", "models", "data/raw_data", "models/inversion",
        "data/raw_data/loupe_system", "models/inversion/loupe_system",
        "models/inversion/inversion_parameters",
    },
    "workbench": {
        "data", "models", "data/raw_data", "models/inversion",
        "data/raw_data/nominal_system", "models/inversion/nominal_system",
        "models/inversion/inversion_parameters",
    },
    "magnetics": {
        "magnetic_data", "magnetic_data/raw_data", "magnetic_data/grids",
        "magnetic_data/raw_data/magnetic_system",
    },
    "tifs": {
        "derived_products", "derived_products/mag_map", "derived_products/all_maps",
        "derived_products/mag_map/magnetic_system",
    },
}

# index length of each tabular leaf, against the row count of its source file
INDEX_FROM_SOURCE = {
    "resolve": {"data/raw_data": ("resolve", "data", "Resolve.csv"),
                "models/inverted_models": ("resolve", "model", "Resolve_model.csv")},
    "skytem": {"data/raw_data": ("skytem_csv", "data", "skytem_contractor_data.csv"),
               "data/processed_data": ("skytem_csv", "data", "skytem_processed_data.csv"),
               "data/depth_to_bedrock": ("skytem_csv", "data", "top_dolomite_blocky_lidar.csv"),
               "models/inverted_models": ("skytem_csv", "model", "skytem_inverted_models.csv")},
    "magnetics": {"magnetic_data/raw_data": ("magnetics", "WI_Magnetics.csv")},
}

# leaves whose source format is not line-per-record, so pinned instead
EXPECTED_INDEX = {
    "tempest": {"data/raw_data": 2001, "models/inverted_models": 2001},
    "loupe": {"data/raw_data": 2474, "models/inversion": 5547},
    "workbench": {"data/raw_data": 338, "models/inversion": 926},
}


def relpaths(survey):
    root = survey.parent if survey.parent is not None else survey
    return {n.path[len("/survey/"):] for n in root.subtree if n.path.startswith("/survey/")}


class TestStructure:

    def test_expected_tree_paths(self, survey):
        name, tree = survey
        assert relpaths(tree) == EXPECTED_PATHS[name]

    def test_survey_node_is_typed_survey(self, survey):
        _, tree = survey
        assert tree.attrs["type"] == "survey"

    def test_survey_has_required_cf_attrs(self, survey):
        _, tree = survey
        missing = [a for a in CF_GLOBAL_ATTRS if a not in tree.attrs]
        assert missing == []

    def test_containers_are_typed(self, survey):
        _, tree = survey
        for child in tree.children.values():
            assert child.attrs.get("type") in ("container", "system"), child.path

    def test_data_leaves_have_a_structure(self, survey):
        _, tree = survey
        leaves = gs_leaves(tree)
        assert leaves, "no tabular or raster leaves found"
        for leaf in leaves:
            assert leaf.attrs["structure"] in ("tabular", "raster")

    def test_systems_are_typed_system(self, survey):
        _, tree = survey
        root = tree.parent if tree.parent is not None else tree
        systems = [n for n in root.subtree if n.name and n.name.endswith("_system")]
        assert systems, "expected at least one system node"
        for s in systems:
            assert s.attrs.get("type") == "system", s.path


class TestSpatialRef:

    def test_data_leaves_carry_spatial_ref(self, survey):
        """Only tabular/raster leaves. System and parameters nodes have none."""
        _, tree = survey
        for leaf in gs_leaves(tree):
            assert "spatial_ref" in leaf.coords, leaf.path

    def test_spatial_ref_wkt_is_parseable(self, survey):
        _, tree = survey
        for leaf in gs_leaves(tree):
            wkt = leaf["spatial_ref"].attrs.get("crs_wkt")
            assert wkt, f"{leaf.path} has no crs_wkt"
            assert CRS.from_wkt(wkt) is not None


class TestVariableMetadata:

    def test_data_vars_carry_cf_attrs(self, survey):
        """Scoped to tabular/raster leaves; systems and parameters do not have these."""
        _, tree = survey
        offenders = []
        for leaf in gs_leaves(tree):
            for var in leaf.dataset.data_vars:
                if var.endswith("_bnds"):
                    continue
                missing = [a for a in CF_VAR_ATTRS if a not in leaf[var].attrs]
                if missing:
                    offenders.append(f"{leaf.path}:{var} missing {missing}")
        assert offenders == []


class TestDimensions:

    def test_every_tabular_leaf_has_the_expected_index_length(self, survey):
        """Counted from the source file where the format is one line per record,
        pinned otherwise. Comparing the keys as well as the sizes means a new
        tabular leaf cannot appear without an expectation being recorded for it.
        """
        name, tree = survey
        expected = {path: data_row_count(DATA.joinpath(*parts))
                    for path, parts in INDEX_FROM_SOURCE.get(name, {}).items()}
        expected.update(EXPECTED_INDEX.get(name, {}))

        tabular = {leaf.path[len("/survey/"):] for leaf in gs_leaves(tree, ("tabular",))}
        assert set(expected) == tabular
        for path, size in expected.items():
            assert tree[path].sizes["index"] == size, path

    def test_sliced_system_keeps_its_sliced_dims(self, skytem_survey):
        """The processed data attaches a system sliced with isel; the slice must survive.

        Raw is lm 28 / hm 32; processed drops 1 low-moment and 10 high-moment gates.
        """
        raw = skytem_survey["data/raw_data/skytem_system"]
        proc = skytem_survey["data/processed_data/skytem_system"]
        assert (raw.sizes["lm_gate_times"], raw.sizes["hm_gate_times"]) == (28, 32)
        assert (proc.sizes["lm_gate_times"], proc.sizes["hm_gate_times"]) == (27, 22)

    def test_the_sliced_data_sits_on_the_gates_its_system_kept(self, skytem_survey):
        """Both halves of the slice: the data is 27 and 22 gates wide, and the gate
        times it sits on are the ones the sliced system carries, not the raw ones.
        """
        proc = skytem_survey["data/processed_data"]
        assert proc["lm_data"].shape[1:] == (27,)
        assert proc["hm_data"].shape[1:] == (22,)

        raw = skytem_survey["data/raw_data"]
        for dim, dropped in (("lm_gate_times", 1), ("hm_gate_times", 10)):
            assert np.allclose(proc[dim].values, raw[dim].values[dropped:])

    def test_a_system_does_not_own_the_gates_of_the_data_it_hangs_off(self, skytem_survey):
        """A system attached to a dataset inherits that dataset's coordinates, so the
        magnetometer can see the AEM gate times - but it must not own them. If it did
        it would answer for them the next time the systems are handed to a dataset,
        and a sibling system sliced down to the gates that dataset kept would be
        overwritten by the raw ones.
        """
        magnetic = skytem_survey["data/raw_data/magnetic_system"]
        assert "lm_gate_times" in magnetic.coords
        assert not [dim for dim in magnetic.to_dataset(inherit=False).dims if "gate_times" in dim]

    def test_a_system_lifted_off_a_dataset_keeps_only_the_coordinates_it_uses(self, skytem_survey):
        """The two halves of what lifting a system has to get right.

        The magnetometer comes away with nothing of the AEM dataset it hung off - no
        index, no gate times. The AEM system comes away still holding the gate times
        it defines, even though the values themselves are stored on the host: xarray
        deletes a child's copy of any coordinate its parent indexes, so
        ``to_dataset(inherit=False)`` on that system would give dimensions with no
        values for them.
        """
        raw = skytem_survey["data/raw_data"]
        host = raw.to_dataset(inherit=False)

        magnetic = Container._lift_system(raw["magnetic_system"])
        assert not set(magnetic.coords) & set(host.coords)

        skytem = Container._lift_system(raw["skytem_system"])
        assert (skytem.sizes["lm_gate_times"], skytem.sizes["hm_gate_times"]) == (28, 32)
        assert np.allclose(skytem["lm_gate_times"].values, host["lm_gate_times"].values)
        assert "index" not in skytem.coords

    def test_two_dimensional_variables_use_their_system_dim(self, skytem_survey):
        """The [i]-suffixed CSV columns collapse onto the system's gate dimensions."""
        raw = skytem_survey["data/raw_data"]
        assert raw["hm_z"].dims == ("index", "hm_gate_times")
        assert raw["lm_z"].dims == ("index", "lm_gate_times")

    def test_every_center_lies_inside_its_own_bounds(self, survey):
        """The one invariant that holds for every coordinate here: depth layers tile,
        EM gate windows deliberately overlap, but a center is always within its own
        cell. Catches bounds that are correctly shaped but paired with the wrong cell,
        which is what a 2xN bounds array in a metadata file used to produce.
        """
        _, tree = survey
        checked = 0
        for leaf in gs_leaves(tree):
            for name, coord in leaf.coords.items():
                bnds = coord.attrs.get("bounds")
                if bnds is None or bnds not in leaf:
                    continue
                # min/max per row rather than columns 0 and 1: a descending
                # coordinate, e.g. a raster y, puts the larger edge first.
                edges = leaf[bnds].values
                assert np.all((edges.min(axis=1) <= coord.values) &
                              (coord.values <= edges.max(axis=1))), \
                    f"{leaf.path}:{name} has centers outside their own bounds"
                checked += 1
        assert checked > 0, "no bounded coordinates found, so this asserted nothing"

    def test_stacked_tifs_become_a_third_dimension(self, tifs_survey):
        """Five resistivity tifs stack along z into one 3D variable."""
        res = tifs_survey["derived_products/all_maps"]["resistivity"]
        assert res.sizes["z"] == 5
        assert set(res.dims) == {"z", "y", "x"}


@pytest.fixture(scope="module")
def resolve_systems():
    """Resolve's three systems as a tree, built from its own metadata file.

    Built here rather than lifted out of a survey so these tests do not depend on
    the integration builders.
    """
    md = Metadata.read(RESOLVE_MD)
    tree, _ = Container.Systems(**{k: v for k, v in md.items() if "system" in k})
    return tree


class TestSystemCouplets:
    """A variable naming a system couplet is checked against the attached systems.

    Driven through ``Tabular.read`` rather than a survey build, because what is
    under test is how a system arrives - or fails to.
    """

    def test_a_couplet_with_no_system_says_so(self):
        with pytest.raises(ValueError, match="no system is passed"):
            Tabular.read(RESOLVE_CSV, metadata_file=RESOLVE_MD_NO_SYSTEMS,
                         spatial_ref=SPATIAL_REF)

    def test_a_couplet_that_matches_nothing_lists_the_labels(self, resolve_systems):
        """Only the magnetic system is attached, so the frequency-domain couplets
        have nothing to match and the error shows what was available.
        """
        with pytest.raises(ValueError, match="does not match any couplet labels"):
            Tabular.read(RESOLVE_CSV, metadata_file=RESOLVE_MD_NO_SYSTEMS,
                         spatial_ref=SPATIAL_REF,
                         system=resolve_systems["magnetic_system"].to_dataset())

    @pytest.mark.parametrize("form", ["tree", "dict", "dataset"])
    def test_a_system_is_found_in_any_form_it_is_passed(self, resolve_systems, form):
        """The couplet check accepts the same forms as the rest of ``Tabular.read``:
        a tree of systems, a dict of them, or a lone dataset.
        """
        systems = {"tree": resolve_systems,
                   "dict": {k: resolve_systems[k].to_dataset() for k in resolve_systems.children},
                   "dataset": resolve_systems["magnetic_system"].to_dataset()}[form]
        labels = Tabular._couplet_labels(systems)

        assert "passive_scalar_magnetometer" in labels

    def test_no_system_at_all_yields_no_labels(self):
        """The empty dict is what Container.Data passes when a metadata file declares
        no systems, and None is what a direct call defaults to. Neither may explode.
        """
        assert Tabular._couplet_labels(None) == []
        assert Tabular._couplet_labels({}) == []


class TestRoundtrip:

    def test_reopens_with_the_same_paths(self, roundtrip):
        """Survey-level system nodes are the documented exception: to_netcdf drops them.

        Derived from EXPECTED_PATHS rather than from the written tree, because the
        write has already deleted those nodes by the time we could look.
        """
        name, _, back = roundtrip
        expected = {p for p in EXPECTED_PATHS[name]
                    if "/" in p or not p.endswith("_system")}
        assert relpaths(back) == expected

    def test_reopens_with_the_same_variables_and_dims(self, roundtrip):
        name, built, back = roundtrip
        for leaf in gs_leaves(back):
            path = leaf.path[len("/survey/"):]
            original = built[path].dataset
            assert set(leaf.dataset.data_vars) == set(original.data_vars), path
            assert dict(leaf.dataset.sizes) == dict(original.sizes), path

    def test_reopens_with_the_same_values(self, roundtrip):
        """Values survive, once the missing_value sentinel is accounted for.

        xarray masks missing_value on read, so a numeric sentinel written from the
        source file (-9999 in most of these) comes back as NaN. Masking the built
        tree the same way keeps this a test of data fidelity rather than of CF
        decoding.
        """
        _, built, back = roundtrip
        for leaf in gs_leaves(back):
            path = leaf.path[len("/survey/"):]
            for var in leaf.dataset.data_vars:
                got, original = leaf[var], built[path][var]
                if not np.issubdtype(got.dtype, np.number):
                    continue
                want = original.values
                sentinel = original.attrs.get("missing_value")
                if isinstance(sentinel, (int, float, np.number)):
                    want = np.where(want == sentinel, np.nan, want)
                np.testing.assert_allclose(got.values, want, rtol=1e-6,
                                           err_msg=f"{path}:{var}")

    def test_reopens_with_the_variable_attrs_intact(self, roundtrip):
        """missing_value is checked separately; it lands in .encoding, not .attrs.

        Bounds variables are skipped because xarray owns their units: it copies
        the parent coordinate's units onto them when writing and drops them again
        when reading.
        """
        _, built, back = roundtrip
        checked = [a for a in CF_VAR_ATTRS if a != "missing_value"]
        for leaf in gs_leaves(back):
            path = leaf.path[len("/survey/"):]
            for var in leaf.dataset.data_vars:
                if var.endswith("_bnds"):
                    continue
                for attr in checked:
                    if attr in built[path][var].attrs:
                        assert attr in leaf[var].attrs, f"{path}:{var} lost {attr}"

    def test_missing_value_comes_back_in_encoding_not_attrs(self, roundtrip):
        """Current behaviour, worth knowing about: the GS convention requires
        missing_value on every variable, and it is written to the file, but xarray
        consumes it while decoding. Code reading a GS file back through gspy has to
        look in ``.encoding`` for it.
        """
        _, built, back = roundtrip
        for leaf in gs_leaves(back):
            path = leaf.path[len("/survey/"):]
            for var in leaf.dataset.data_vars:
                if "missing_value" not in built[path][var].attrs:
                    continue
                assert "missing_value" not in leaf[var].attrs, f"{path}:{var}"
                assert "missing_value" in leaf[var].encoding, f"{path}:{var}"

    def test_write_stamps_version_and_conventions(self, roundtrip):
        _, _, back = roundtrip
        assert back.attrs["conventions"] == "GS-2.0, CF-1.13"
        assert back.attrs["gspy_version"]
        assert back.attrs["content"]

    def test_write_strips_survey_level_systems(self, tmp_path):
        """Documents current behaviour, not necessarily desired.

        A survey whose metadata names a system carries it as a child of the survey
        itself, and ``to_netcdf`` deletes those before writing, so the written file
        does not hold them. Nothing a dataset needs is lost - a dataset gets its own
        copy of whichever system recorded it - but a nominal system described once at
        survey level and never attached to anything does not survive a write.

        None of the examples put a system at survey level any more, so this one is put
        there on purpose: the skytem systems now live in their own file, and the survey
        metadata plus that file is what the skytem survey used to be.
        """
        survey = Survey.from_dict(dict(Metadata.read(SKYTEM_SURVEY_MD))
                                  | dict(Metadata.read(SKYTEM_SYSTEM_MD)))
        assert {"skytem_system", "magnetic_system"} <= set(survey.children)

        path = tmp_path / "skytem.nc"
        survey.gs.to_netcdf(path)

        back = gspy.open_datatree(path)["survey"]
        assert not set(back.children) & {"skytem_system", "magnetic_system"}

    def test_a_container_can_be_written_on_its_own(self, tmp_path):
        """The goal is one file per survey, but a branch can be written separately.

        The branch keeps its absolute path in the written file, so it reopens at
        /survey/magnetic_data rather than at the root.
        """
        survey = build_magnetics()
        path = tmp_path / "branch.nc"
        survey["magnetic_data"].gs.to_netcdf(path)

        back = gspy.open_datatree(path)["survey/magnetic_data"]
        assert set(back.children) == {"raw_data", "grids"}
