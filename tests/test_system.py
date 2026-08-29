"""System metadata templates: the shape they come out in, and that they build.

A template is generated from how many transmitters and receivers a system has, so
these tests are mostly about counting - couplets, gate time dimensions, and which
fields are a list rather than a single value. Two of them check the generated
shape against the system definitions in the examples, which is the only place the
conventions are recorded in anger.
"""
import numpy as np
import pytest
from gspy import Dataset, Metadata, System

from conftest import DATA

RESOLVE_CSV = str(DATA / "resolve" / "data" / "Resolve.csv")
RESOLVE_MD = str(DATA / "resolve" / "data" / "Resolve_data_md.yml")
SKYTEM_MD = str(DATA / "skytem_csv" / "data" / "skytem_system.yml")

FAMILIES = ("fdem", "magnetic", "radiometric", "tdem")

# What a dimension needs before a system will build, by the name it goes by. A
# template cannot supply these: real gate times and frequencies are the survey's.
DIMENSION_SIZES = {
    "gate_times": dict(centers=[1.0e-5, 2.0e-5, 3.0e-5]),
    "frequency": dict(centers=[400, 1800, 3300]),
    "spectra": dict(length=8, increment=1, origin=0),
    "n_loop_vertices": dict(length=8),
    "base_mag_locations": dict(centers=[1]),
}

WAVEFORM = [0.0, 1.0e-3, 2.0e-3]


def answered(value):
    """Every placeholder answered with a value GSPy accepts as a real one."""
    if isinstance(value, dict):
        return {k: answered(v) for k, v in value.items()}
    if isinstance(value, list):
        return [answered(v) for v in value]
    return "not_defined" if isinstance(value, str) and "??" in value else value


def buildable(key, **shape):
    """A template filled in far enough to hand to ``System.from_dict``."""
    system = System.metadata_template(key, **shape)[f"{key}_system"]

    for name, dimension in system["dimensions"].items():
        sizes = next((v for k, v in DIMENSION_SIZES.items() if k in name), None)
        if sizes is None:
            continue
        for held in ("centers", "bounds", "length"):
            dimension.pop(held, None)
        dimension.update(sizes)

    # The waveform is a dimension declared among the variables, so it needs real
    # numbers as well: a time per vertex, and a current per vertex per transmitter.
    transmitter = system["variables"]["transmitter"]
    if "waveform_time" in transmitter:
        transmitter["waveform_time"]["values"] = WAVEFORM
        transmitter["waveform_current"]["values"] = \
            [WAVEFORM] * np.size(transmitter["label"])

    return answered(system)


class TestTemplates:

    def test_one_template_per_method_family(self):
        assert System.templates() == FAMILIES

    def test_an_unknown_family_says_what_there_is(self):
        with pytest.raises(ValueError, match="Choose one of"):
            System.metadata_template("tem")


class TestShape:

    def test_every_receiver_measures_every_transmitter(self):
        """Time domain: two moments read by two coils is four couplets."""
        couplet = System.metadata_template(
            "tdem", transmitters=["LM", "HM"], receivers=["z", "x"],
        )["tdem_system"]["variables"]["couplet"]

        assert couplet["transmitters"] == ["LM", "HM", "LM", "HM"]
        assert couplet["receivers"] == ["z", "z", "x", "x"]

    def test_a_paired_family_gives_one_couplet_per_pair(self):
        """Frequency domain: each transmitter coil has its own receiver coil."""
        couplet = System.metadata_template(
            "fdem", transmitters=["400Z", "1800Z"], receivers=["400Z", "1800Z"],
        )["fdem_system"]["variables"]["couplet"]

        assert couplet["transmitters"] == ["400Z", "1800Z"]
        assert couplet["receivers"] == ["400Z", "1800Z"]

    def test_a_paired_family_mirrors_the_side_you_leave_out(self):
        variables = System.metadata_template("fdem", transmitters=6)["fdem_system"]["variables"]

        assert variables["receiver"]["label"] == variables["transmitter"]["label"]
        assert len(variables["couplet"]["transmitters"]) == 6

    def test_a_paired_family_will_not_take_unequal_sides(self):
        with pytest.raises(ValueError, match="pair up one to one"):
            System.metadata_template("fdem", transmitters=2, receivers=3)

    def test_a_count_gives_indexed_labels(self):
        transmitter = System.metadata_template("tdem", transmitters=3)["tdem_system"]["variables"]["transmitter"]

        assert transmitter["label"] == ["transmitter_1", "transmitter_2", "transmitter_3"]

    def test_one_of_something_is_a_value_rather_than_a_list(self):
        """Which is how every single moment example writes it."""
        variables = System.metadata_template("tdem")["tdem_system"]["variables"]

        assert variables["transmitter"]["label"] == "transmitter_1"
        assert isinstance(variables["transmitter"]["area"], str)

    def test_a_couplet_pairing_stays_a_list_even_when_there_is_one(self):
        """The couplet labels are put together by zipping these two, and a lone
        string would be zipped a character at a time.
        """
        couplet = System.metadata_template("magnetic")["magnetic_system"]["variables"]["couplet"]

        assert couplet["transmitters"] == ["passive"]
        assert couplet["receivers"] == ["scalar_magnetometer"]

    def test_a_family_with_its_own_labels_uses_them(self):
        """Nothing transmits for a magnetometer, so the default is not an index."""
        variables = System.metadata_template("magnetic")["magnetic_system"]["variables"]

        assert variables["transmitter"]["label"] == "passive"
        assert variables["receiver"]["label"] == "scalar_magnetometer"

    def test_asking_for_more_than_a_family_names_falls_back_to_indexes(self):
        """A gradiometer has two sensors, and the family only names the one."""
        variables = System.metadata_template("magnetic", receivers=2)["magnetic_system"]["variables"]

        assert variables["receiver"]["label"] == ["receiver_1", "receiver_2"]
        assert variables["transmitter"]["label"] == "passive"
        assert variables["couplet"]["transmitters"] == ["passive", "passive"]

    def test_a_system_needs_at_least_one_of_everything(self):
        with pytest.raises(ValueError, match="at least one"):
            System.metadata_template("tdem", receivers=0)

    def test_a_field_carrying_its_own_dimensions_is_left_alone(self):
        """``coordinates`` is a vertex per loop corner per transmitter, so its
        dimensions say what shape it is and there is nothing to repeat.
        """
        transmitter = System.metadata_template(
            "tdem", transmitters=2)["tdem_system"]["variables"]["transmitter"]

        assert transmitter["coordinates"]["dimensions"] == ["n_transmitter", "n_loop_vertices", "xyz"]
        assert "??" in transmitter["coordinates"]["values"]


class TestPerTransmitterDimensions:

    def test_each_transmitter_gets_its_own_gate_times(self):
        system = System.metadata_template("tdem", transmitters=["LM", "HM"])["tdem_system"]

        assert list(system["dimensions"]) == ["lm_gate_times", "hm_gate_times",
                                              "n_loop_vertices", "xyz"]
        assert system["dimensions"]["lm_gate_times"]["standard_name"] == "lm_gate_times"

    def test_the_transmitter_it_belongs_to_is_named_in_its_placeholders(self):
        gates = System.metadata_template(
            "tdem", transmitters=["LM", "HM"])["tdem_system"]["dimensions"]["hm_gate_times"]

        assert "HM" in gates["centers"]

    def test_one_transmitter_keeps_the_bare_name(self):
        """There is nothing to tell apart, and no example writes it any other way."""
        system = System.metadata_template("tdem")["tdem_system"]

        assert "gate_times" in system["dimensions"]
        assert system["variables"]["couplet"]["gate_times"] == ["gate_times"]

    def test_each_couplet_points_at_its_own_transmitters_gate_times(self):
        couplet = System.metadata_template(
            "tdem", transmitters=["LM", "HM"], receivers=["z", "x"],
        )["tdem_system"]["variables"]["couplet"]

        assert couplet["gate_times"] == ["lm_gate_times", "hm_gate_times",
                                         "lm_gate_times", "hm_gate_times"]


class TestAgainstTheExamples:
    """The generated layout, against the system definitions in the examples.

    The couplet ordering and the gate time naming are conventions, and these two
    files are where they are actually recorded.
    """

    def test_a_dual_moment_system_comes_out_like_the_skytem_example(self):
        example = Metadata.read(SKYTEM_MD)["skytem_system"]["variables"]
        couplet = System.metadata_template(
            "tdem",
            transmitters=example["transmitter"]["label"],
            receivers=example["receiver"]["label"],
        )["tdem_system"]["variables"]["couplet"]

        # Lowercased on both sides: the example writes its transmitter labels
        # upper case and its couplets lower, and from_dict lowercases anyway.
        assert [t.lower() for t in couplet["transmitters"]] == \
            [t.lower() for t in example["couplet"]["transmitters"]]
        assert couplet["receivers"] == example["couplet"]["receivers"]
        assert [g.lower() for g in couplet["gate_times"]] == \
            [g.lower() for g in example["couplet"]["gate_times"]]

    def test_a_frequency_domain_system_comes_out_like_the_resolve_example(self):
        example = Metadata.read(RESOLVE_MD)["resolve_system"]["variables"]
        couplet = System.metadata_template(
            "fdem", transmitters=example["transmitter"]["label"],
        )["fdem_system"]["variables"]["couplet"]

        assert couplet["transmitters"] == example["couplet"]["transmitters"]
        assert couplet["receivers"] == example["couplet"]["receivers"]


class TestNaming:

    def test_the_default_name_is_the_family(self):
        assert list(System.metadata_template("tdem")) == ["tdem_system"]

    def test_a_name_can_be_whatever_says_it_is_a_system(self):
        assert list(System.metadata_template("tdem", name="skytem_system")) == ["skytem_system"]

    def test_a_name_that_does_not_say_system_is_refused(self):
        """A container lifts systems out of a dataset's metadata by looking for
        "system" in the key, so a system named anything else is not one.
        """
        with pytest.raises(ValueError, match="named with 'system' in it"):
            System.metadata_template("tdem", name="skytem")


class TestMerging:

    def test_what_you_already_know_wins_over_the_placeholders(self):
        system = System.metadata_template(
            "tdem", metadata=dict(mode="airborne", instrument="SkyTEM 304M"),
        )["tdem_system"]

        assert system["mode"] == "airborne"
        assert system["instrument"] == "SkyTEM 304M"
        assert "??" in system["variables"]["transmitter"]["area"]


class TestItBuilds:
    """A filled in template is a system GSPy can build.

    The strongest thing to say about a template: not just well formed, but the
    right shape. Placeholders are answered with ``not_defined``, which is a real
    value here, and the dimensions get real numbers - see ``buildable``.
    """

    @pytest.mark.parametrize("key", FAMILIES)
    def test_every_family_builds_once_it_is_filled_in(self, key):
        system = System.from_dict(**buildable(key))

        assert system.attrs["type"] == "system"
        assert system.sizes["n_couplet"] == 1

    def test_the_shape_asked_for_is_the_shape_that_is_built(self):
        system = System.from_dict(**buildable("tdem", transmitters=["LM", "HM"],
                                              receivers=["z", "x"]))

        assert (system.sizes["n_transmitter"], system.sizes["n_receiver"]) == (2, 2)
        assert system.sizes["n_couplet"] == 4
        assert list(system["couplet_label"].values) == ["LM_z", "HM_z", "LM_x", "HM_x"]

    def test_the_couplet_labels_a_dataset_is_checked_against_are_there(self):
        """``Tabular.read`` matches a variable's ``system_couplet`` against these,
        so a system built from a template has to carry them.
        """
        system = System.from_dict(**buildable("magnetic"))

        assert list(system["couplet_label"].values) == ["passive_scalar_magnetometer"]

    def test_the_gate_times_a_couplet_names_are_dimensions_of_the_system(self):
        system = System.from_dict(**buildable("tdem", transmitters=["LM", "HM"],
                                              receivers=["z", "x"]))

        assert set(np.unique(system["couplet_gate_times"].values)) <= set(system.sizes)

    def test_an_untouched_template_does_not_build(self):
        """The caveat, pinned: a template is a skeleton. Its dimensions hold
        placeholders where the survey's own gate times go, the same way
        ``Survey.metadata_template`` does not yield a CRS from ``wkid: '??'``.
        """
        with pytest.raises(ValueError):
            System.from_dict(**System.metadata_template("tdem")["tdem_system"])


class TestDumping:

    @pytest.mark.parametrize("key", FAMILIES)
    def test_a_dumped_template_reads_back(self, key, tmp_path):
        """Which is the whole point of one: dump it, fill it in, hand it back.

        Also guards the placeholder wording. GSPy writes yml itself and quotes
        nothing, so a placeholder holding ": " would dump to a file that no
        longer parses.
        """
        path = tmp_path / f"{key}.yml"
        template = System.metadata_template(key, transmitters=2, receivers=2)
        template.dump(str(path))

        back = Metadata.read(str(path))
        back.pop("directory", None)

        assert list(back) == list(template)
        assert list(back[f"{key}_system"]["variables"]) == list(template[f"{key}_system"]["variables"])


class TestDatasetSystems:
    """Systems are asked for alongside the dataset they recorded."""

    def test_a_family_key_on_its_own(self):
        template = Dataset.metadata_template(RESOLVE_CSV, systems="magnetic")

        assert "magnetic_system" in template
        assert "variables" in template

    def test_a_list_of_families(self):
        template = Dataset.metadata_template(RESOLVE_CSV, systems=["fdem", "magnetic"])

        assert {"fdem_system", "magnetic_system"} <= set(template)

    def test_a_mapping_names_each_one_and_shapes_it(self):
        template = Dataset.metadata_template(
            RESOLVE_CSV,
            systems={"skytem_system": dict(key="tdem", transmitters=["LM", "HM"],
                                           receivers=["z", "x"]),
                     "magnetic_system": "magnetic"})

        assert len(template["skytem_system"]["variables"]["couplet"]["transmitters"]) == 4
        assert template["magnetic_system"]["variables"]["transmitter"]["label"] == "passive"

    def test_the_dataset_variables_are_still_templated(self):
        """The systems are an addition, not a replacement."""
        template = Dataset.metadata_template(RESOLVE_CSV, systems="fdem")

        assert set(template) >= {"dataset_attrs", "coordinates", "variables", "fdem_system"}
