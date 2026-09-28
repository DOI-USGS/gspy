"""Comments in a yml metadata file: read with it, and written back out with it.

A template is filled in by hand, so what each field should hold is written as a
comment above it or beside it. These pin that the comments survive the round
trip, and survive a system template being reshaped to its transmitters.
"""
import textwrap

import pytest
from gspy import Dataset, Metadata, System

from conftest import DATA

RESOLVE_CSV = str(DATA / "resolve" / "data" / "Resolve.csv")
FAMILIES = ("fdem", "magnetic", "radiometric", "tdem")


def written(tmp_path, text):
    path = tmp_path / "md.yml"
    path.write_text(textwrap.dedent(text))
    return str(path)


SOURCE = """\
    # What this file is.
    # Two lines of it.

    # The survey as a whole.
    survey:
      # Who flew it.
      # Their full name.
      contractor: '?? name ??'  # a company
      year: 2024 # when
      note: 'one # two'
      loose: 1

    # Not attached to anything, a blank line follows.

    other:
      value: 3
    """


class TestReading:

    @pytest.fixture
    def md(self, tmp_path):
        return Metadata.read(written(tmp_path, SOURCE))

    def test_the_values_are_as_before(self, md):
        assert md["survey"]["contractor"] == "?? name ??"
        assert md["survey"]["year"] == 2024

    def test_a_comment_above_a_key(self, md):
        assert md.comments[("survey", "contractor")]["above"] == ["Who flew it.", "Their full name."]
        assert md.comments[("survey",)]["above"] == ["The survey as a whole."]

    def test_a_comment_beside_a_key(self, md):
        assert md.comments[("survey", "contractor")]["inline"] == "a company"
        assert md.comments[("survey", "year")]["inline"] == "when"

    def test_a_hash_inside_quotes_is_not_a_comment(self, md):
        assert md["survey"]["note"] == "one # two"
        assert ("survey", "note") not in md.comments

    def test_the_opening_block_is_the_header(self, md):
        assert md.comments[()]["above"] == ["What this file is.", "Two lines of it."]

    def test_a_comment_cut_off_by_a_blank_line_belongs_to_nothing(self, md):
        assert ("other",) not in md.comments


class TestWriting:

    def test_comments_are_written_back_where_they_were(self, tmp_path):
        md = Metadata.read(written(tmp_path, SOURCE))
        out = tmp_path / "out.yml"
        md.dump(str(out))

        lines = out.read_text().splitlines()
        assert lines[:2] == ["# What this file is.", "# Two lines of it."]
        at = lines.index("    contractor: ?? name ?? # a company")
        assert lines[at - 2:at] == ["    # Who flew it.", "    # Their full name."]

    def test_they_read_back_the_same(self, tmp_path):
        md = Metadata.read(written(tmp_path, SOURCE))
        out = tmp_path / "out.yml"
        md.dump(str(out))

        back = Metadata.read(str(out))
        assert back.comments == md.comments
        assert back["survey"] == md["survey"]

    def test_metadata_with_no_comments_is_written_as_before(self, tmp_path):
        out = tmp_path / "out.yml"
        Metadata(dict(a=dict(b=1))).dump(str(out))

        assert out.read_text() == "a:\n    b: 1\n"


def dumped(tmp_path, key, **shape):
    path = tmp_path / f"{key}.yml"
    System.metadata_template(key, **shape).dump(str(path))
    return path.read_text().splitlines()


def commented(lines, key):
    """The comment on ``key``: the block above it, and what is beside it."""
    at = next(i for i, line in enumerate(lines) if line.strip().startswith(f"{key}:"))
    above = []
    for line in reversed(lines[:at]):
        if not line.strip().startswith("#"):
            break
        above.insert(0, line.strip())
    return above, "#" in lines[at]


class TestSystemTemplates:

    @pytest.mark.parametrize("key", FAMILIES)
    def test_every_field_says_what_it_is(self, key):
        """The ask of a template: tell whoever fills it in what goes where."""
        spec = Metadata.read(str(System._template_directory() / f"{key}.yml"))

        fields = [("dimensions", name) for name in spec.get("dimensions", {})]
        for block, values in spec["variables"].items():
            fields += [("variables", block, name) for name in values]
        fields += [("attrs", name) for name in spec["attrs"] if name != "type"]

        bare = [path for path in fields if path not in spec.comments]
        assert not bare, f"{key}.yml has fields with no comment: {bare}"

    @pytest.mark.parametrize("key", FAMILIES)
    def test_a_dumped_template_opens_with_the_header(self, key, tmp_path):
        assert dumped(tmp_path, key)[0].startswith("#")

    def test_a_field_keeps_its_comment_when_repeated_per_transmitter(self, tmp_path):
        lines = dumped(tmp_path, "tdem", transmitters=["LM", "HM"])
        above, beside = commented(lines, "peak_current")

        assert above or beside

    def test_a_per_transmitter_dimension_keeps_its_comment_under_each_name(self, tmp_path):
        lines = dumped(tmp_path, "tdem", transmitters=["LM", "HM"])

        for name in ("lm_gate_times", "hm_gate_times"):
            above, beside = commented(lines, name)
            assert above or beside, name

    def test_a_system_attribute_keeps_its_comment(self, tmp_path):
        """``attrs`` is lifted to the top of the system, and its comments with it."""
        above, beside = commented(dumped(tmp_path, "tdem"), "instrument")

        assert above or beside

    def test_it_still_reads_back(self, tmp_path):
        path = tmp_path / "tdem.yml"
        template = System.metadata_template("tdem", transmitters=2, receivers=2)
        template.dump(str(path))

        back = Metadata.read(str(path))
        back.pop("directory", None)
        assert back == template

    def test_a_dataset_template_carries_its_systems_comments(self, tmp_path):
        path = tmp_path / "dataset.yml"
        Dataset.metadata_template(RESOLVE_CSV, systems="fdem").dump(str(path))

        lines = path.read_text().splitlines()
        above, beside = commented(lines[lines.index("fdem_system:"):], "instrument")
        assert above or beside
