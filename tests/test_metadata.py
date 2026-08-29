"""Metadata: a dict subclass that reads yml/json/csv/xlsx and merges them.

Bound to behaviour, not to internals. A refactor of these classes is expected,
and reading a file into a nested dict, merging two of them, and dumping one back
out should keep working across it.
"""
import pytest
from gspy.metadata.Metadata import Metadata

from conftest import DATA

RESOLVE = DATA / "resolve"
SURVEY_YML = str(RESOLVE / "data" / "Resolve_survey_md.yml")
DATA_YML = str(RESOLVE / "data" / "Resolve_data_md_without_variables.yml")
VARIABLE_CSV = str(RESOLVE / "data" / "Resolve_variable_table_md.csv")


class TestRead:

    def test_yml_becomes_a_nested_dict(self):
        md = Metadata.read(SURVEY_YML)
        assert isinstance(md, Metadata)
        assert md["dataset_attrs"]["title"]
        assert md["spatial_ref"]

    def test_read_records_the_source_directory(self):
        """Downstream code resolves sibling files, e.g. a .prj, relative to this."""
        assert Metadata.read(SURVEY_YML)["directory"] == str(RESOLVE / "data")

    def test_none_reads_as_an_empty_dict(self):
        assert Metadata.read(None) == {}

    def test_a_dict_reads_straight_through(self):
        assert Metadata.read({"a": 1})["a"] == 1

    def test_lists_of_strings_are_joined_but_lists_of_numbers_are_not(self):
        """Netcdf attrs cannot hold a list of strings, so they are comma-joined."""
        md = Metadata.read({"words": ["a", "b"], "numbers": [1, 2]})
        assert md["words"] == "a,b"
        assert md["numbers"] == [1, 2]

    def test_xlsx_reads_the_same_shape_as_yml(self):
        pytest.importorskip("openpyxl")
        md = Metadata.read(str(RESOLVE / "model" / "Resolve_model_md.xlsx"))
        assert {"dataset_attrs", "coordinates", "dimensions", "variables"} <= set(md)

    @pytest.mark.xfail(strict=True,
                       reason="assert False, ValueError(...) raises AssertionError, "
                              "and vanishes entirely under python -O")
    def test_an_unsupported_extension_raises_value_error(self, tmp_path):
        path = tmp_path / "md.txt"
        path.write_text("nope\n")
        with pytest.raises(ValueError):
            Metadata.read(str(path))


class TestVariableTable:
    """``table=True`` reads a spreadsheet of one row per variable."""

    def test_rows_become_variables(self):
        md = Metadata.read(VARIABLE_CSV, table=True)
        assert set(md) == {"variables", "directory"}
        entry = md["variables"]["140k_hz_filtered"]
        assert entry["long_name"]
        assert entry["units"]

    def test_typed_cells_are_coerced(self):
        """A bracketed cell becomes a list, so dimensions arrive ready to use."""
        entry = Metadata.read(VARIABLE_CSV, table=True)["variables"]["140k_hz_filtered"]
        assert entry["dimensions"] == ["index", "channel"]

    def test_a_blank_cell_falls_back_to_not_defined(self, tmp_path):
        path = tmp_path / "vars.csv"
        path.write_text("variable_name,standard_name,long_name,units,missing_value\n"
                        "alt,,altitude,,\n")
        entry = Metadata.read(str(path), table=True)["variables"]["alt"]
        assert entry["standard_name"] == "alt", "blank standard_name defaults to the name"
        assert entry["units"] == "not_defined"
        assert entry["missing_value"] == "not_defined"

    def test_a_missing_required_column_raises(self, tmp_path):
        path = tmp_path / "vars.csv"
        path.write_text("variable_name,standard_name\nalt,altitude\n")
        with pytest.raises(ValueError, match="Missing column"):
            Metadata.read(str(path), table=True)


class TestMerge:

    def test_that_wins_on_conflict(self):
        assert Metadata.merge({"a": 1}, {"a": 2})["a"] == 2

    def test_nested_dicts_are_combined_not_replaced(self):
        out = Metadata.merge({"a": {"x": 1}}, {"a": {"y": 2}})
        assert out["a"] == {"x": 1, "y": 2}

    def test_new_keys_are_added(self):
        assert Metadata.merge({"a": 1}, {"b": 2})["b"] == 2

    def test_matched_keys_drops_keys_absent_from_the_first(self):
        """Used to fill in a template without letting a file invent new entries."""
        out = Metadata.merge({"a": 1}, {"b": 2}, matched_keys=True)
        assert set(out) == {"a"}

    def test_a_variable_table_fills_in_a_yml_without_variables(self):
        """The resolve example's pattern: prose in yml, per-variable rows in csv."""
        out = Metadata.merge(Metadata.read(DATA_YML),
                             Metadata.read(VARIABLE_CSV, table=True))
        assert out["dataset_attrs"]
        assert len(out["variables"]) > 10

    def test_merge_leaves_its_inputs_alone(self):
        base = {"a": {"x": 1}}
        Metadata.merge(base, {"a": {"y": 2}})
        assert base == {"a": {"x": 1}}


class TestDump:

    def test_json_roundtrips_exactly(self, tmp_path):
        src = Metadata.read(DATA_YML)
        path = tmp_path / "md.json"
        Metadata(dict(src)).dump(str(path))
        back = Metadata.read(str(path))
        assert _without_directory(back) == _without_directory(src)

    @pytest.mark.parametrize("ext", [".yml", ".csv"])
    def test_yml_and_csv_keep_the_structure(self, tmp_path, ext):
        """Every leaf comes back at the same key, though see the next test for types."""
        src = Metadata.read(DATA_YML)
        path = tmp_path / f"md{ext}"
        Metadata(dict(src)).dump(str(path))
        back = _read_as_nested(path)

        flat_src = Metadata(_without_directory(src)).flatten()
        flat_back = Metadata(_without_directory(back)).flatten()
        assert set(flat_back) == set(flat_src)
        assert {k: str(v) for k, v in flat_back.items()} == \
               {k: str(v) for k, v in flat_src.items()}

    @pytest.mark.parametrize("ext", [".yml", ".csv"])
    def test_yml_and_csv_lose_the_type_of_numeric_looking_strings(self, tmp_path, ext):
        """Current behaviour. Both writers stringify and the readers re-parse, so a
        deliberately quoted version or epoch comes back as a number. Only json is
        type-preserving. Matters for anything that later does string operations on
        such a value.
        """
        path = tmp_path / f"md{ext}"
        Metadata({"epoch": "2015.0"}).dump(str(path))
        assert _read_as_nested(path)["epoch"] == 2015.0

    def test_an_unsupported_extension_raises(self, tmp_path):
        with pytest.raises(Exception, match="Unknown extension"):
            Metadata({"a": 1}).dump(str(tmp_path / "md.txt"))


class TestHelpers:

    def test_flatten_joins_nested_keys_with_dots(self):
        assert Metadata({"a": {"b": {"c": 1}}, "d": 2}).flatten() == {"a.b.c": 1, "d": 2}

    def test_unflatten_splits_one_level(self):
        """Current behaviour: the depth beyond the first dot is dropped, so this is
        not the inverse of flatten. Nothing in gspy calls it.
        """
        assert Metadata({"a.b": 1}).unflatten() == {"a": {"b": 1}}

    def test_pop_and_split_returns_the_popped_keys_and_the_remainder(self):
        md = Metadata({"a": 1, "b": 2})
        popped, rest = md.pop_and_split(("a",))
        assert popped == {"a": 1}
        assert rest == {"b": 2}

    def test_check_keys_accepts_a_complete_dict(self):
        Metadata({"a": 1, "b": 2}).check_keys(("a", "b"))

    def test_check_key_whitespace_flags_a_bad_key(self):
        assert Metadata({"bad key": 1}).check_key_whitespace() is True
        assert Metadata({"good_key": 1}).check_key_whitespace() is False

    @pytest.mark.xfail(strict=True,
                       reason="assert x, ValueError(...) raises AssertionError; see "
                              "test_an_unsupported_extension_raises_value_error")
    def test_check_keys_raises_value_error_when_a_key_is_missing(self):
        with pytest.raises(ValueError):
            Metadata({"a": 1}).check_keys(("a", "z"))


def _without_directory(md):
    return {k: v for k, v in md.items() if k != "directory"}


def _read_as_nested(path):
    """``table`` only reaches the csv reader; read_yml and read_json take no kwargs."""
    kwargs = {"table": False} if path.suffix == ".csv" else {}
    return Metadata.read(str(path), **kwargs)
