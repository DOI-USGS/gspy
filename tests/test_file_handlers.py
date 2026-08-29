"""File handlers: format detection, and the contract every handler honours.

Bound to the abc contract - a handler exposes ``df``, ``metadata``, ``columns``,
``nrecords``, ``type`` and ``file_metadata`` - rather than to how any one format
parses its file.
"""
import numpy as np
import pandas as pd
import pytest
import xarray as xr
from gspy import Metadata, Survey
from gspy.file_handlers import (InsufficientMetadataError, aseg_gdf2_handler,
                                csv_handler, dataframe_handler, file_handler,
                                handler_for, handlers, loupe_handler, open_datafile,
                                workbench_handler, workbench_model_handler,
                                xyz_handler)
from gspy.gs_datatree.Container import Container
from gspy.gs_dataset.Tabular import Tabular

from conftest import DATA, data_row_count

RESOLVE_CSV = str(DATA / "resolve" / "data" / "Resolve.csv")
TEMPEST_DAT = str(DATA / "tempest_aseg" / "data" / "Tempest.dat")
LOUPE_DAT = str(DATA / "loupe" / "data" / "Kankakee.dat")
WORKBENCH_XYZ = str(DATA / "workbench" / "data" / "prod_726_729raw_RAW_export.xyz")
WORKBENCH_MOD = str(DATA / "workbench" / "model" / "prod_726_729_LBv2_bky_MOD_dat.xyz")
WORKBENCH_MOD_MD = str(DATA / "workbench" / "model" / "models.yml")
SKYTEM_CSV = str(DATA / "skytem_csv" / "data" / "skytem_contractor_data.csv")
SKYTEM_MD = str(DATA / "skytem_csv" / "data" / "skytem_contractor_data.yml")
# The simplest complete example: one csv, one container, no sliced systems.
MAGNETICS_CSV = str(DATA / "magnetics" / "WI_Magnetics.csv")
MAGNETICS_MD = str(DATA / "magnetics" / "WI_Magnetics_raw_data_md.yml")
MAGNETICS_SURVEY_MD = str(DATA / "magnetics" / "WI_Magnetics_survey_md.yml")

# Metadata a handler will accept but Tabular.read will not: it says nothing about
# any of the columns, which is what makes it hand back a template.
NO_VARIABLES = {"dataset_attrs": {"content": "no variables described"}}
SPATIAL_REF = {"wkid": 3071, "authority": "EPSG", "vertical_crs": "NAVD88"}

# (file, file_type, handler). The .dat cases are resolved by the sidecar next to
# the data file: a .dfn means ASEG-GDF2, a .dat.desc means Loupe.
DISPATCH = [
    (RESOLVE_CSV, None, csv_handler),
    (str(DATA / "magnetics" / "WI_Magnetics.csv"), None, csv_handler),
    (TEMPEST_DAT, None, aseg_gdf2_handler),
    (LOUPE_DAT, None, loupe_handler),
    (WORKBENCH_XYZ, None, workbench_handler),
    (WORKBENCH_MOD, None, workbench_model_handler),
    (RESOLVE_CSV, "loupe", loupe_handler),
    (RESOLVE_CSV, "aseg", aseg_gdf2_handler),
    (TEMPEST_DAT, "csv", csv_handler),
]


@pytest.fixture(scope="module")
def resolve_csv():
    """One read of Resolve.csv shared by everything that only inspects it."""
    return open_datafile(RESOLVE_CSV)


@pytest.fixture(scope="module")
def workbench_system():
    """The system a Workbench read needs, built straight from its metadata file."""
    md = Metadata.read(WORKBENCH_MOD_MD)
    system, _ = Container.Systems(nominal_system=md['nominal_system'])
    return system


class TestDispatch:

    @pytest.mark.parametrize("filename, file_type, expected",
                             DISPATCH, ids=lambda v: getattr(v, "__name__", None))
    def test_the_expected_handler_is_chosen(self, filename, file_type, expected):
        assert handler_for(filename, file_type=file_type) is expected

    def test_an_explicit_file_type_beats_the_extension(self):
        """A Loupe .dat with no .desc sidecar still needs a way in."""
        assert handler_for(RESOLVE_CSV) is csv_handler
        assert handler_for(RESOLVE_CSV, file_type="loupe") is loupe_handler

    def test_an_unknown_file_type_says_what_is_available(self):
        with pytest.raises(ValueError, match="Unknown file_type"):
            handler_for(RESOLVE_CSV, file_type="nope")

    def test_an_unknown_extension_falls_back_to_csv(self, tmp_path):
        path = tmp_path / "data.txt"
        path.write_text("a,b\n1,2\n")
        assert handler_for(str(path)) is csv_handler

    def test_a_workbench_model_beats_plain_workbench(self):
        """Both claim the file; the model handler has the higher priority."""
        assert workbench_handler.can_read(WORKBENCH_MOD)
        assert workbench_model_handler.can_read(WORKBENCH_MOD)
        assert handler_for(WORKBENCH_MOD) is workbench_model_handler

    def test_workbench_is_told_apart_from_a_workbench_model(self):
        assert xyz_handler.is_workbench(WORKBENCH_XYZ)
        assert xyz_handler.is_workbench_model(WORKBENCH_MOD)


class TestRegistry:
    """Formats register themselves, so adding one needs no edit to the dispatcher."""

    def test_every_expected_format_is_registered(self):
        assert set(handlers()) == {"csv", "aseg", "loupe", "workbench",
                                   "workbench_model", "dataframe"}

    def test_the_dataframe_handler_never_claims_a_file(self):
        """It is registered so it can be named, but detection must never land on
        it - there is no file it could read.
        """
        assert not dataframe_handler.can_read(RESOLVE_CSV)
        assert handler_for(RESOLVE_CSV) is csv_handler

    def test_registered_handlers_are_concrete_subclasses(self):
        for key, handler in handlers().items():
            assert issubclass(handler, file_handler), key
            assert handler.key == key
            assert not getattr(handler, "__abstractmethods__", None), key

    def test_an_abstract_base_is_not_dispatchable(self):
        """xyz_handler is a shared base with no read, so it must not be registered."""
        assert xyz_handler not in handlers().values()

    def test_two_handlers_cannot_claim_one_key(self):
        with pytest.raises(ValueError, match="claim the key"):
            class duplicate_handler(csv_handler, key="csv"):
                pass


class TestRead:
    """open_datafile returns an instance with the file already read."""

    @pytest.mark.parametrize("filename, expected_handler, expected_type", [
        (RESOLVE_CSV, csv_handler, "csv"),
        (TEMPEST_DAT, aseg_gdf2_handler, "aseg"),
        (LOUPE_DAT, loupe_handler, "loupe"),
    ])
    def test_read_satisfies_the_contract(self, filename, expected_handler, expected_type):
        read = open_datafile(filename, metadata={})

        assert isinstance(read, expected_handler)
        assert isinstance(read.df, pd.DataFrame)
        assert isinstance(read.metadata, dict)
        assert isinstance(read.file_metadata, dict)
        assert read.type == expected_type
        assert read.filename == filename
        assert len(read.columns) > 0
        assert read.nrecords == read.df.shape[0] > 0

    def test_csv_row_count_matches_the_file(self, resolve_csv):
        assert resolve_csv.nrecords == data_row_count(RESOLVE_CSV)

    def test_aseg_takes_its_column_names_from_the_dfn(self):
        read = open_datafile(TEMPEST_DAT, metadata={})
        assert "Line" in read.metadata, "the .dfn definitions land in metadata"
        assert read.nrecords == 2001

    def test_metadata_passed_in_is_merged_with_what_the_file_knows(self):
        read = open_datafile(RESOLVE_CSV, metadata={"line": {"units": "-"}})
        assert read.metadata["line"]["units"] == "-"

    def test_read_without_metadata_works(self):
        """No metadata is a legitimate starting point - it is how a user gets to a
        template in the first place.
        """
        assert open_datafile(RESOLVE_CSV).metadata == {}

    def test_a_handler_can_be_constructed_directly(self):
        """Dispatch is a convenience; naming a format is always allowed."""
        assert csv_handler(RESOLVE_CSV).nrecords == data_row_count(RESOLVE_CSV)


class TestInMemoryData:
    """Data can arrive already read, as a DataFrame or as a handler that has read
    its file. Both skip the disk, which is the whole point of allowing them.
    """

    def test_a_dataframe_satisfies_the_same_contract(self):
        read = open_datafile(pd.DataFrame({"line": [1, 2], "alt": [30.0, 31.0]}))

        assert isinstance(read, dataframe_handler)
        assert read.type == "dataframe"
        assert list(read.columns) == ["line", "alt"]
        assert read.nrecords == 2
        assert read.file_metadata == {}, "a frame declares nothing about itself"

    def test_the_frame_is_adopted_not_copied(self):
        df = pd.DataFrame({"line": [1, 2]})
        assert open_datafile(df).df is df

    def test_a_frame_takes_the_metadata_it_is_given(self):
        read = open_datafile(pd.DataFrame({"line": [1, 2]}),
                             metadata={"line": {"units": "-"}})
        assert read.metadata == {"line": {"units": "-"}}

    def test_wide_columns_collapse_the_same_as_they_would_in_a_file(self):
        df = pd.DataFrame({"alt": [1.0], "dbdt[0]": [1.0], "dbdt[1]": [2.0]})
        assert open_datafile(df).column_header_counts == {"alt": 1, "dbdt": 2}

    def test_a_frame_gets_a_template_like_any_other_source(self):
        df = pd.DataFrame({"line": [1, 2], "dbdt[0]": [1.0, 2.0], "dbdt[1]": [3.0, 4.0]})
        template = open_datafile(df).metadata_template()

        assert set(template["variables"]) == {"line", "dbdt"}
        assert template["variables"]["dbdt"]["dimensions"] == ["index", "??"], \
            "a wide column still asks for its second dimension"

    def test_a_frame_can_be_named_in_place_of_a_filename(self, tmp_path, monkeypatch):
        """Used wherever a filename would appear, e.g. an error message or the
        default name of a written template. chdir because that default writes to
        the working directory.
        """
        monkeypatch.chdir(tmp_path)
        handler = dataframe_handler(pd.DataFrame({"line": [1]}), name="processed_lines")

        assert handler.filename == "processed_lines"
        assert handler.write_metadata_template().name == \
               "processed_lines_metadata_template.yml"

    def test_reader_options_and_a_system_are_tolerated_and_ignored(self):
        """A call that passed pandas options or a system with a filename should
        not have to be stripped down to hand over a frame instead.
        """
        read = open_datafile(pd.DataFrame({"line": [1]}), sep=",", system={})
        assert read.nrecords == 1

    def test_something_that_is_not_a_frame_is_rejected(self):
        with pytest.raises(TypeError, match="pandas.DataFrame"):
            dataframe_handler({"line": [1, 2]})

    def test_a_handler_passes_straight_through(self):
        handler = open_datafile(RESOLVE_CSV)
        assert open_datafile(handler) is handler

    def test_metadata_is_merged_into_a_passed_handler_rather_than_replacing_it(self):
        """The reason to hand back a handler: it has already gleaned what it can
        from its own file, and the caller only overrides what it wants to.
        """
        handler = open_datafile(TEMPEST_DAT, metadata={})
        before = dict(handler.metadata["Line"])

        open_datafile(handler, metadata={"Line": {"long_name": "flight line number"}})
        after = handler.metadata["Line"]

        assert after["long_name"] == "flight line number"
        assert {k: v for k, v in after.items() if k != "long_name"} == \
               {k: v for k, v in before.items() if k != "long_name"}


def magnetics_raw_data(data):
    """The magnetics raw_data leaf, built from whatever ``data`` is.

    Goes through ``container.gs.add`` rather than ``Tabular.read`` because that is
    the path a user takes, and because Container.Data is what lifts the system
    definitions out of the metadata file before the tabular read needs them.
    """
    survey = Survey.from_dict(MAGNETICS_SURVEY_MD)
    container = survey.gs.add_container("magnetic_data", **dict(content="raw flightlines"))
    container.gs.add(key="raw_data", data=data, metadata_file=MAGNETICS_MD)

    return survey["magnetic_data/raw_data"].to_dataset()


@pytest.fixture(scope="module")
def magnetics_from_file():
    """The reference build, straight from the csv on disk."""
    return magnetics_raw_data(MAGNETICS_CSV)


class TestTabularFromMemory:
    """Ingesting the same table from a file and from memory must agree."""

    def test_a_frame_builds_the_same_dataset_as_its_file(self, magnetics_from_file):
        """The frame comes from the handler, so this pins the ingest path rather
        than how pandas happens to parse a csv.
        """
        xr.testing.assert_identical(magnetics_raw_data(open_datafile(MAGNETICS_CSV).df),
                                    magnetics_from_file)

    def test_a_handler_builds_the_same_dataset_as_its_file(self, magnetics_from_file):
        xr.testing.assert_identical(magnetics_raw_data(open_datafile(MAGNETICS_CSV)),
                                    magnetics_from_file)

    def test_a_plain_pandas_read_works_end_to_end(self):
        """The call a user would actually make, rather than one routed through gspy."""
        ds = magnetics_raw_data(pd.read_csv(MAGNETICS_CSV))
        assert ds.sizes["index"] == data_row_count(MAGNETICS_CSV)

    def test_rows_filtered_before_ingest_stay_filtered(self):
        """The reason to reach for a frame instead of a filename."""
        df = open_datafile(MAGNETICS_CSV).df
        # A line that recorded some Base_Mag. Most lines recorded none, and a
        # column of nothing but missing values cannot be ingested yet - see
        # test_a_column_a_filter_empties_completely_cannot_be_ingested.
        line = df.loc[df["Base_Mag"] != -9999.99, "Line"].iloc[0]

        ds = magnetics_raw_data(df[df["Line"] == line])

        assert 0 < ds.sizes["index"] < data_row_count(MAGNETICS_CSV)
        assert np.unique(ds["line"].values).tolist() == [line]

    @pytest.mark.xfail(strict=True, raises=ValueError,
                       reason="valid_range has no all-missing case: gspy finding")
    def test_a_column_a_filter_empties_completely_cannot_be_ingested(self):
        """Filtering rows can leave a column holding only its missing_value, and
        gspy derives valid_range by reducing over the values that are not missing.

        Pins a pre-existing defect that filtering before ingest makes easy to hit:
        the first magnetics flight line recorded no Base_Mag at all.
        """
        df = open_datafile(MAGNETICS_CSV).df

        magnetics_raw_data(df[df["Line"] == df["Line"].iloc[0]])

    def test_a_frame_with_no_metadata_still_offers_a_template(self):
        """The no-metadata escape hatch has to work for in-memory data too, and it
        has no filename to name in the error.
        """
        df = pd.DataFrame({"line": [1, 2], "alt": [30.0, 31.0]})
        with pytest.raises(InsufficientMetadataError) as raised:
            Tabular.read(df, metadata_file=NO_VARIABLES, spatial_ref=SPATIAL_REF)

        assert set(raised.value.template["variables"]) == {"line", "alt"}
        assert raised.value.filename == "dataframe"


class TestFileMetadata:
    """The one slot for anything a format knows that a DataFrame cannot hold."""

    @pytest.mark.parametrize("filename", [RESOLVE_CSV, TEMPEST_DAT, LOUPE_DAT])
    def test_a_format_that_only_describes_columns_declares_nothing(self, filename):
        assert open_datafile(filename, metadata={}).file_metadata == {}

    def test_a_workbench_model_declares_its_gate_times_as_dimensions(self, workbench_system):
        read = open_datafile(WORKBENCH_MOD, metadata={}, system=workbench_system)

        dimensions = read.file_metadata["dimensions"]
        assert set(dimensions) == {"lm_gate_times", "hm_gate_times"}
        for gates in dimensions.values():
            assert len(gates["centers"]) > 0

    def test_workbench_will_not_read_without_a_system(self):
        """Its channels are named after the system's couplet labels."""
        with pytest.raises(ValueError, match="system"):
            open_datafile(WORKBENCH_XYZ, metadata={})


class TestColumnHeaderCounts:
    """Repeated columns are what become a second dimension on a variable."""

    @staticmethod
    def _handler_for(header, tmp_path):
        path = tmp_path / "d.csv"
        path.write_text(",".join(header) + "\n" + ",".join("1" * len(header)) + "\n")
        return open_datafile(str(path), metadata={})

    def test_bracketed_columns_collapse(self, tmp_path):
        read = self._handler_for(["alt", "dbdt[0]", "dbdt[1]", "dbdt[2]"], tmp_path)
        assert read.column_header_counts == {"alt": 1, "dbdt": 3}

    def test_trailing_integer_suffixes_collapse(self, tmp_path):
        read = self._handler_for(["alt", "gate_1", "gate_2"], tmp_path)
        assert read.column_header_counts == {"alt": 1, "gate": 2}

    def test_a_non_numeric_suffix_is_left_alone(self, tmp_path):
        """dbdt_lm_z must not collapse to dbdt_lm."""
        read = self._handler_for(["dbdt_lm_z", "dbdt_hm_z"], tmp_path)
        assert read.column_header_counts == {"dbdt_lm_z": 1, "dbdt_hm_z": 1}

    def test_the_real_resolve_header_finds_its_wide_columns(self, resolve_csv):
        counts = resolve_csv.column_header_counts
        assert counts["spec256_down"] == 256
        assert counts["dres_150_by5m"] == 31


class TestAbcValidation:

    def test_df_must_be_a_dataframe(self, resolve_csv):
        with pytest.raises(TypeError):
            resolve_csv.df = [1, 2, 3]

    def test_metadata_must_be_a_dict(self, resolve_csv):
        with pytest.raises(TypeError):
            resolve_csv.metadata = "nope"

    def test_filename_must_be_a_string_or_path(self, resolve_csv):
        with pytest.raises(TypeError):
            resolve_csv.filename = 3


class TestMetadataTemplate:
    """The escape hatch for a user with data and no metadata."""

    def test_the_template_has_an_entry_per_collapsed_column(self, resolve_csv):
        template = resolve_csv.metadata_template()

        assert set(template["variables"]) == set(resolve_csv.column_header_counts)
        assert template["variables"]["line"] == {"standard_name": "not_defined",
                                                "long_name": "not_defined",
                                                "missing_value": "not_defined",
                                                "units": "not_defined"}

    def test_a_wide_column_gets_a_dimensions_entry_to_fill_in(self, resolve_csv):
        assert resolve_csv.metadata_template()["variables"]["spec256_down"]["dimensions"] == \
               ["index", "??"]

    def test_existing_variable_metadata_wins_over_the_placeholders(self, resolve_csv):
        template = resolve_csv.metadata_template(variables={"line": {"units": "-"}})

        assert template["variables"]["line"]["units"] == "-"
        assert template["variables"]["line"]["long_name"] == "not_defined"

    def test_aseg_seeds_the_template_from_the_dfn(self):
        """The DFN already names and units every column, so a template should not
        throw that away and ask for it again.
        """
        read = open_datafile(TEMPEST_DAT, metadata={})
        entry = read.metadata_template()["variables"]["Line"]

        assert entry["standard_name"] == "line"
        assert entry["long_name"] != "not_defined"
        assert "format" not in entry, "the fortran format is ours, not the user's"

    def test_write_metadata_template_returns_the_path_it_wrote(self, resolve_csv, tmp_path):
        path = resolve_csv.write_metadata_template(tmp_path / "template.yml")

        assert path.exists()
        assert "??" in path.read_text()


class TestMissingMetadata:
    """A handler reports what a user still owes it, rather than raising."""

    def test_every_column_is_missing_when_nothing_is_described(self, resolve_csv):
        assert resolve_csv.missing_metadata({}) == \
               tuple(f"variables.{var}" for var in resolve_csv.column_header_counts)

    def test_a_described_column_drops_off_the_list(self, resolve_csv):
        described = {"standard_name": "line", "long_name": "flight line",
                     "units": "-", "missing_value": -9999}
        missing = resolve_csv.missing_metadata({"variables": {"line": described}})

        assert "variables.line" not in missing
        assert "variables.spec256_down" in missing

    def test_a_partly_described_column_reports_the_attrs_it_lacks(self, resolve_csv):
        missing = resolve_csv.missing_metadata({"variables": {"line": {"standard_name": "line"}}})

        assert {"variables.line.long_name", "variables.line.units",
                "variables.line.missing_value"} <= set(missing)

    def test_placeholders_anywhere_in_the_metadata_are_reported(self, resolve_csv):
        missing = resolve_csv.missing_metadata({"dataset_attrs": {"content": "?? what ??"}})
        assert "dataset_attrs.content" in missing

    def test_a_metadata_file_that_works_leaves_nothing_missing(self):
        """The metadata behind a working example must describe every column, since
        Tabular.read needs an entry for each one.
        """
        md = Metadata.read(SKYTEM_MD)
        read = open_datafile(SKYTEM_CSV, metadata=md.get("variables", {}))

        assert read.missing_metadata(md) == ()


class TestInsufficientMetadata:
    """The template comes back attached to an exception, not as a message plus a
    file written somewhere the caller did not ask for.
    """

    @pytest.fixture
    def raised(self):
        with pytest.raises(InsufficientMetadataError) as raised:
            Tabular.read(SKYTEM_CSV, metadata_file=NO_VARIABLES, spatial_ref=SPATIAL_REF)
        return raised.value

    def test_the_error_names_the_file_it_could_not_read(self, raised):
        assert raised.filename == SKYTEM_CSV
        assert SKYTEM_CSV in str(raised)

    def test_the_error_carries_a_template_covering_every_column(self, raised):
        assert set(raised.template["variables"]) == \
               set(open_datafile(SKYTEM_CSV).column_header_counts)

    def test_the_error_lists_what_is_missing(self, raised):
        assert raised.missing
        assert all(entry.startswith("variables.") for entry in raised.missing)

    def test_the_template_can_be_written_and_read_back(self, raised, tmp_path):
        path = tmp_path / "template.yml"
        raised.template.dump(str(path))

        assert set(Metadata.read(str(path))["variables"]) == set(raised.template["variables"])

    def test_nothing_is_written_to_the_working_directory(self, tmp_path, monkeypatch):
        """Raising is the whole side effect; dumping the template is the caller's call."""
        monkeypatch.chdir(tmp_path)
        with pytest.raises(InsufficientMetadataError):
            Tabular.read(SKYTEM_CSV, metadata_file=NO_VARIABLES, spatial_ref=SPATIAL_REF)

        assert list(tmp_path.iterdir()) == []
