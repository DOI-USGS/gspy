"""Reading a GA-AEM .stm system file into a GSPy system.

Two shapes of file answer to the same extension: the block format that
GALEISBSTDEM reads for a time domain system, and the csv table of coil pairs
that the frequency domain codes read. The parser sorts them out, and
``System.metadata_from_stm`` lays what it finds over a system template, leaving
placeholders wherever the .stm cannot say.

The .stm files and the _system.yml files in ``examples/data_files/systems`` are
unrelated instances of those systems, so nothing here checks one against the
other. The ymls only record conventions - how a label is spelled, how couplets
are ordered - and those are already pinned in test_system.
"""
import numpy as np
import pytest

from gspy import Metadata, System
from gspy.metadata._stm_md_handler import read_stm

from conftest import DATA

SYSTEMS = DATA / "systems"
SKYTEM_LM = str(SYSTEMS / "SkytemLM.stm")
SKYTEM_HM = str(SYSTEMS / "SkytemHM.stm")
TEMPEST = str(SYSTEMS / "Tempest.stm")
RESOLVE = str(SYSTEMS / "Resolve.stm")


def written(path, transmitter="", forward_modelling=""):
    """The smallest block .stm that reads, plus whatever else is under test."""
    path.write_text("System Begin\n\tName = Made up\n\tType = Time Domain\n"
                    f"\tTransmitter Begin\n\t\tBaseFrequency = 30\n{transmitter}"
                    "\t\tWaveFormCurrent Begin\n0.0 0.0\n1.0e-3 1.0\n\t\tWaveFormCurrent End\n"
                    "\tTransmitter End\n\tReceiver Begin\n\t\tNumberOfWindows = 1\n"
                    "\t\tWindowTimes Begin\n1.0e-5 2.0e-5\n\t\tWindowTimes End\n"
                    "\tReceiver End\n"
                    f"\tForwardModelling Begin\n\t\tOutputType = dB/dt\n{forward_modelling}"
                    "\tForwardModelling End\nSystem End\n")
    return str(path)


class TestParsingBlocks:
    """The ``System Begin`` ... ``System End`` format, as written."""

    def test_the_outer_system_block_is_unwrapped(self):
        """Every file is one system, so its block is the file."""
        stm = read_stm(SKYTEM_LM)

        assert stm["format"] == "block"
        assert stm["name"] == "SkyTEMLM_ElkHills"
        assert stm["type"] == "Time Domain"

    def test_a_key_becomes_snake_case(self):
        transmitter = read_stm(SKYTEM_LM)["transmitter"]

        assert transmitter["number_of_turns"] == 1
        assert transmitter["base_frequency"] == 210.0
        assert transmitter["waveform_digitising_frequency"] == 3440640

    def test_blocks_nest(self):
        """``LowPassFilter`` sits inside ``Receiver``, which sits inside ``System``."""
        filter = read_stm(SKYTEM_LM)["receiver"]["low_pass_filter"]

        assert filter["cut_off_frequency"] == [300000, 210000]
        assert filter["order"] == [1, 2]

    def test_a_block_of_numbers_is_a_table_of_rows(self):
        waveform = read_stm(SKYTEM_LM)["transmitter"]["waveform_current"]

        assert np.shape(waveform) == (21, 2)
        assert waveform[0] == [-8.00e-04, 0.0]
        assert waveform[-1] == [1.581e-03, 0.0]

    def test_a_table_is_read_whole_however_the_file_is_laid_out(self):
        """SkyTEM writes its rows hard against the margin, Tempest indents them."""
        assert np.shape(read_stm(TEMPEST)["transmitter"]["waveform_current"]) == (7, 2)
        assert np.shape(read_stm(SKYTEM_HM)["receiver"]["window_times"]) == (26, 2)

    def test_a_block_that_starts_in_column_one_still_nests(self):
        """SkytemHM.stm unindents ``Receiver Begin`` to the margin."""
        receiver = read_stm(SKYTEM_HM)["receiver"]

        assert receiver["number_of_windows"] == 26
        assert receiver["window_weighting_scheme"] == "AreaUnderCurve"

    def test_a_comment_is_dropped(self):
        """The loop radius in SkytemLM.stm is preceded by a // comment."""
        forward = read_stm(SKYTEM_LM)["forward_modelling"]

        assert forward["modelling_loop_radius"] == 10.416
        assert not any("TX loop area" in str(v) for v in forward.values())

    def test_a_value_that_is_not_a_number_stays_a_string(self):
        forward = read_stm(SKYTEM_LM)["forward_modelling"]

        assert forward["output_type"] == "dB/dt"
        assert forward["secondary_field_normalisation"] == "none"

    def test_the_component_scalings_are_read_as_numbers(self):
        """Which is how the receiver coils are worked out later."""
        forward = read_stm(TEMPEST)["forward_modelling"]

        assert (forward["x_output_scaling"], forward["y_output_scaling"],
                forward["z_output_scaling"]) == (1e15, 0.0, 1e15)


class TestParsingTables:
    """The frequency domain format: a header row, then a row per coil pair."""

    def test_the_header_names_the_columns(self):
        stm = read_stm(RESOLVE)

        assert stm["format"] == "table"
        assert stm["freq"] == [380.0, 1776.0, 3345.0, 8171.0, 41020.0, 129550.0]

    def test_a_column_of_words_stays_words(self):
        stm = read_stm(RESOLVE)

        assert stm["tor"] == ["z", "z", "x", "z", "z", "z"]
        assert stm["ror"] == ["z", "z", "x", "z", "z", "z"]

    def test_the_geometry_columns_are_all_there(self):
        stm = read_stm(RESOLVE)

        assert stm["rx"] == [7.93, 7.91, 9.03, 7.91, 7.91, 7.89]
        assert stm["tzoff"] == [0.0] * 6
        assert stm["rzoff"] == [0.0] * 6


class TestChoosingTheFamily:

    def test_a_block_file_is_templated_as_time_domain(self):
        assert list(System.metadata_from_stm(SKYTEM_LM)) == ["tdem_system"]

    def test_a_table_file_is_templated_as_frequency_domain(self):
        assert list(System.metadata_from_stm(RESOLVE)) == ["fdem_system"]

    def test_the_name_can_be_whatever_says_it_is_a_system(self):
        assert list(System.metadata_from_stm(SKYTEM_LM, name="skytem_system")) == ["skytem_system"]

    @pytest.mark.parametrize("domain", ["time", "tdem", "time domain"])
    def test_the_domain_can_be_said_outright(self, domain):
        assert list(System.metadata_from_stm(SKYTEM_LM, domain=domain)) == ["tdem_system"]

    def test_a_domain_the_file_cannot_be_read_as_is_refused(self):
        """The keyword settles what the file leaves open, it does not force nonsense."""
        with pytest.raises(ValueError, match="block"):
            System.metadata_from_stm(SKYTEM_LM, domain="frequency")

    def test_an_unknown_domain_says_what_there_is(self):
        with pytest.raises(ValueError, match="time"):
            System.metadata_from_stm(SKYTEM_LM, domain="spectral")


class TestTimeDomainShape:

    def test_one_file_is_a_one_transmitter_system(self):
        variables = System.metadata_from_stm(SKYTEM_LM)["tdem_system"]["variables"]

        assert variables["transmitter"]["label"] == "transmitter_1"
        assert variables["couplet"]["transmitters"] == ["transmitter_1"]

    def test_a_file_per_moment_is_one_system_with_a_transmitter_each(self):
        variables = System.metadata_from_stm({"LM": SKYTEM_LM, "HM": SKYTEM_HM})["tdem_system"]["variables"]

        assert variables["transmitter"]["label"] == ["LM", "HM"]
        assert variables["couplet"]["transmitters"] == ["LM", "HM"]

    def test_each_moment_gets_its_own_gate_times(self):
        system = System.metadata_from_stm({"LM": SKYTEM_LM, "HM": SKYTEM_HM})["tdem_system"]

        assert "lm_gate_times" in system["dimensions"]
        assert "hm_gate_times" in system["dimensions"]
        assert system["variables"]["couplet"]["gate_times"] == ["lm_gate_times", "hm_gate_times"]

    def test_the_receiver_coils_come_from_the_component_scalings(self):
        """Tempest outputs x and z, so it is read by two coils."""
        variables = System.metadata_from_stm(TEMPEST)["tdem_system"]["variables"]

        assert variables["receiver"]["label"] == ["x", "z"]
        assert variables["receiver"]["orientation"] == ["x", "z"]

    def test_a_single_component_system_has_the_one_coil(self):
        """SkyTEM scales z only."""
        variables = System.metadata_from_stm(SKYTEM_LM)["tdem_system"]["variables"]

        assert variables["receiver"]["label"] == "z"

    def test_the_receivers_can_be_given_instead(self):
        """The .stm says which components are modelled, not how many coils flew."""
        variables = System.metadata_from_stm(SKYTEM_LM, receivers=["z", "x"])["tdem_system"]["variables"]

        assert variables["receiver"]["label"] == ["z", "x"]
        assert variables["couplet"]["receivers"] == ["z", "x"]

    def test_a_system_read_from_a_dipole_file_has_no_loop_geometry(self):
        """The .stm is a dipole approximation, so there are no loop vertices to ask for."""
        system = System.metadata_from_stm(SKYTEM_LM)["tdem_system"]

        assert "n_loop_vertices" not in system["dimensions"]
        assert "xyz" not in system["dimensions"]
        assert "coordinates" not in system["variables"]["transmitter"]

    def test_a_system_read_from_a_stm_is_airborne(self):
        """GA-AEM only models airborne systems, so the mode is not left open."""
        assert System.metadata_from_stm(SKYTEM_LM)["tdem_system"]["mode"] == "airborne"


class TestTimeDomainValues:

    def test_the_gates_are_bounded_by_the_window_times(self):
        gates = System.metadata_from_stm(SKYTEM_LM)["tdem_system"]["dimensions"]["gate_times"]

        assert np.shape(gates["bounds"]) == (19, 2)
        assert gates["bounds"][0] == [1.828e-05, 2.285e-05]

    def test_a_gate_is_centred_between_its_bounds(self):
        gates = System.metadata_from_stm(SKYTEM_LM)["tdem_system"]["dimensions"]["gate_times"]

        assert len(gates["centers"]) == 19
        assert gates["centers"][0] == pytest.approx(0.5 * (1.828e-05 + 2.285e-05))

    def test_the_transmitter_values_the_file_states_are_taken(self):
        transmitter = System.metadata_from_stm(
            {"LM": SKYTEM_LM, "HM": SKYTEM_HM})["tdem_system"]["variables"]["transmitter"]

        assert transmitter["base_frequency"] == [210.0, 30.0]

    def test_the_loop_is_taken_as_the_file_states_it(self):
        """SkyTEM states a single turn of one square metre carrying one amp, which is
        a real loop scaled out of the forward model. Whether the data it is attached
        to was scaled the same way is not the .stm's to say, so the numbers are taken
        as written rather than second guessed.
        """
        transmitter = System.metadata_from_stm(
            {"LM": SKYTEM_LM, "HM": SKYTEM_HM})["tdem_system"]["variables"]["transmitter"]

        assert transmitter["number_of_turns"] == [1, 1]
        assert transmitter["peak_current"] == [1, 1]
        assert transmitter["area"] == [1, 1]

    def test_a_loop_of_real_dimensions_is_taken_the_same_way(self, tmp_path):
        transmitter = System.metadata_from_stm(written(
            tmp_path / "real.stm",
            transmitter="\t\tNumberOfTurns = 4\n\t\tPeakCurrent = 110\n\t\tLoopArea = 342\n",
        ))["tdem_system"]["variables"]["transmitter"]

        assert transmitter["number_of_turns"] == 4
        assert transmitter["peak_current"] == 110
        assert transmitter["area"] == 342

    def test_the_transmitting_dipole_is_vertical(self):
        """A block .stm models a horizontal loop, which is a vertical dipole. The file
        does not say so, the format does.
        """
        transmitter = System.metadata_from_stm(
            {"LM": SKYTEM_LM, "HM": SKYTEM_HM})["tdem_system"]["variables"]["transmitter"]

        assert transmitter["orientation"] == ["z", "z"]

    def test_the_output_type_is_spelled_the_way_gspy_spells_it(self):
        system = System.metadata_from_stm(SKYTEM_LM)["tdem_system"]

        assert system["variables"]["output_data_type"] == "dBdt"
        assert system["variables"]["couplet"]["data_type"] == ["dBdt"]

    def test_a_secondary_field_system_says_so(self):
        """Tempest delivers B, not dB/dt."""
        variables = System.metadata_from_stm(TEMPEST)["tdem_system"]["variables"]

        assert variables["output_data_type"] == "B"

    def test_the_digitising_frequency_is_a_property_of_the_system(self):
        variables = System.metadata_from_stm(SKYTEM_LM)["tdem_system"]["variables"]

        assert variables["digitization_frequency"] == 3440640


class TestTheWaveform:

    def test_the_waveform_is_taken_as_written(self):
        transmitter = System.metadata_from_stm(SKYTEM_LM)["tdem_system"]["variables"]["transmitter"]

        assert transmitter["waveform_time"]["values"][0] == -8.00e-04
        assert transmitter["waveform_current"]["values"] == [
            [row[1] for row in read_stm(SKYTEM_LM)["transmitter"]["waveform_current"]]]

    def test_transmitters_share_one_time_axis(self):
        """``waveform_current`` is declared over n_transmitter by waveform_time, so
        the two moments cannot each bring their own vertices.
        """
        transmitter = System.metadata_from_stm(
            {"LM": SKYTEM_LM, "HM": SKYTEM_HM})["tdem_system"]["variables"]["transmitter"]

        times = transmitter["waveform_time"]["values"]
        currents = transmitter["waveform_current"]["values"]

        assert sorted(set(times)) == times
        assert [len(c) for c in currents] == [len(times), len(times)]

    def test_sharing_the_axis_leaves_every_stated_current_untouched(self):
        """The waveform is straight between its vertices, so interpolating onto a
        superset of them puts back exactly what the file said.
        """
        transmitter = System.metadata_from_stm(
            {"LM": SKYTEM_LM, "HM": SKYTEM_HM})["tdem_system"]["variables"]["transmitter"]
        times = transmitter["waveform_time"]["values"]

        for moment, path in enumerate((SKYTEM_LM, SKYTEM_HM)):
            for time, current in read_stm(path)["transmitter"]["waveform_current"]:
                assert transmitter["waveform_current"]["values"][moment][times.index(time)] \
                    == pytest.approx(current)

    def test_a_transmitter_is_off_outside_its_own_waveform(self):
        """The high moment starts ramping long before the low moment does."""
        transmitter = System.metadata_from_stm(
            {"LM": SKYTEM_LM, "HM": SKYTEM_HM})["tdem_system"]["variables"]["transmitter"]
        times = transmitter["waveform_time"]["values"]

        assert transmitter["waveform_current"]["values"][0][times.index(-4.00e-03)] == 0.0


class TestNormalisation:
    """``SecondaryFieldNormalisation`` is the file's own say on the matter.

    GA-AEM normalises the secondary field by the primary one, which is what makes
    the delivered numbers ppm - a different question from whether the data was
    normalised by the transmitter moment, which the file never addresses.
    """

    def test_a_file_that_normalises_nothing_delivers_the_field_it_modelled(self):
        variables = System.metadata_from_stm(SKYTEM_LM)["tdem_system"]["variables"]

        assert variables["output_data_type"] == "dBdt"

    @pytest.mark.parametrize("stated", ["ppm", "PPM", "PPMPEAKTOPEAK"])
    def test_a_file_that_normalises_by_the_primary_field_delivers_ppm(self, stated, tmp_path):
        system = System.metadata_from_stm(written(
            tmp_path / f"{stated}.stm",
            forward_modelling=f"\t\tSecondaryFieldNormalisation = {stated}\n",
        ))["tdem_system"]

        assert system["variables"]["output_data_type"] == "ppm"
        assert system["variables"]["couplet"]["data_type"] == ["ppm"]

    def test_which_flavour_of_ppm_it_was_is_still_recorded(self, tmp_path):
        """``output_data_type`` says ppm; peak to peak is the file's own detail."""
        system = System.metadata_from_stm(written(
            tmp_path / "p2p.stm",
            forward_modelling="\t\tSecondaryFieldNormalisation = PPMPEAKTOPEAK\n",
        ))["tdem_system"]

        assert system["stm_forward_modelling_secondary_field_normalisation"] == "PPMPEAKTOPEAK"

    def test_a_normalisation_gspy_does_not_know_is_left_alone(self, tmp_path):
        """Better the output type the file modelled than a word GSPy cannot spell."""
        system = System.metadata_from_stm(written(
            tmp_path / "odd.stm",
            forward_modelling="\t\tSecondaryFieldNormalisation = something_else\n",
        ))["tdem_system"]

        assert system["variables"]["output_data_type"] == "dBdt"

    def test_a_frequency_domain_table_leaves_moment_normalisation_to_you(self):
        """Its table gives a signed moment per coil pair, not a loop to judge by."""
        variables = System.metadata_from_stm(RESOLVE)["fdem_system"]["variables"]

        assert "??" in variables["data_normalized"]


def loop(turns=None, current=None, area=None):
    """The transmitter lines of a .stm stating whichever of these it is given."""
    stated = dict(NumberOfTurns=turns, PeakCurrent=current, LoopArea=area)
    return "".join(f"\t\t{key} = {value}\n" for key, value in stated.items() if value is not None)


def pair(tmp_path, lm, hm, lm_modelling="", hm_modelling=""):
    return {"LM": written(tmp_path / "lm.stm", transmitter=lm, forward_modelling=lm_modelling),
            "HM": written(tmp_path / "hm.stm", transmitter=hm, forward_modelling=hm_modelling)}


def transmitter_of(stm):
    return System.metadata_from_stm(stm)["tdem_system"]["variables"]["transmitter"]


class TestTheLoop:
    """GA-AEM scales every output by turns x area x peak current, and takes the
    three separately. A file that leaves one out has no value for it: GA-AEM
    reads an undefined value, it does not assume one.
    """

    def test_one_file_silent_on_turns_does_not_lose_the_others(self, tmp_path):
        transmitter = transmitter_of(pair(tmp_path, loop(current=9, area=340.82),
                                          loop(turns=4, current=110, area=340.82)))

        assert "??" in transmitter["number_of_turns"][0]
        assert transmitter["number_of_turns"][1] == 4

    def test_a_stated_value_is_not_filed_away_as_provenance(self, tmp_path):
        system = System.metadata_from_stm(pair(tmp_path, loop(current=9, area=340.82),
                                               loop(turns=4, current=110, area=340.82)))

        assert "stm_transmitter_number_of_turns" not in system["tdem_system"]

    @pytest.mark.parametrize("field, lm, hm", [
        ("peak_current", loop(turns=1, area=1), loop(turns=1, current=110, area=1)),
        ("area", loop(turns=1, current=1), loop(turns=1, current=1, area=342))])
    def test_the_same_goes_for_the_rest_of_the_loop(self, tmp_path, field, lm, hm):
        transmitter = transmitter_of(pair(tmp_path, lm, hm))

        assert "??" in transmitter[field][0]
        assert transmitter[field][1] in (110, 342)


class TestTheMoment:
    """The moment is worked out from the loop, never stated beside it."""

    def test_it_is_turns_by_area_by_current(self, tmp_path):
        transmitter = transmitter_of(written(tmp_path / "one.stm",
                                             transmitter=loop(turns=4, current=110, area=342)))

        assert transmitter["peak_moment"] == pytest.approx(4 * 342 * 110)

    def test_the_moment_is_the_peak_moment(self, tmp_path):
        """GA-AEM's waveform peaks at one, so the two are the same number."""
        transmitter = transmitter_of(written(tmp_path / "one.stm",
                                             transmitter=loop(turns=4, current=110, area=342)))

        assert transmitter["moment"] == transmitter["peak_moment"]

    def test_each_transmitter_has_its_own(self, tmp_path):
        transmitter = transmitter_of(pair(tmp_path, loop(turns=1, current=9, area=340.82),
                                          loop(turns=4, current=110, area=340.82)))

        assert transmitter["peak_moment"] == pytest.approx([9 * 340.82, 4 * 110 * 340.82])

    def test_a_transmitter_missing_part_of_its_loop_has_none(self, tmp_path):
        transmitter = transmitter_of(pair(tmp_path, loop(current=9, area=340.82),
                                          loop(turns=4, current=110, area=340.82)))

        assert "??" in transmitter["peak_moment"][0]
        assert transmitter["peak_moment"][1] == pytest.approx(4 * 110 * 340.82)


class TestNormalisedByMoment:
    """GA-AEM predicts the field of the moment the file states, and its predictions
    are compared with the data, so the data are in the same units. A unit moment
    means the data were divided by theirs; ppm is free of the moment altogether.
    """

    def test_a_unit_loop_means_normalised(self, tmp_path):
        stm = written(tmp_path / "one.stm", transmitter=loop(turns=1, current=1, area=1))

        assert System.metadata_from_stm(stm)["tdem_system"]["variables"]["data_normalized"] is True

    def test_a_real_loop_means_not(self, tmp_path):
        stm = written(tmp_path / "one.stm", transmitter=loop(turns=4, current=110, area=342))

        assert System.metadata_from_stm(stm)["tdem_system"]["variables"]["data_normalized"] is False

    def test_ppm_means_normalised(self, tmp_path):
        stm = written(tmp_path / "one.stm", transmitter=loop(turns=4, current=110, area=342),
                      forward_modelling="\t\tSecondaryFieldNormalisation = PPM\n")

        assert System.metadata_from_stm(stm)["tdem_system"]["variables"]["data_normalized"] is True

    @pytest.mark.parametrize("lm", [loop(turns=1, current=1, area=1), loop(current=1, area=1)],
                             ids=["one_unit_one_real", "one_moment_unknown"])
    def test_it_is_left_to_you_unless_every_transmitter_agrees(self, tmp_path, lm):
        stm = pair(tmp_path, lm, loop(turns=4, current=110, area=342))
        variables = System.metadata_from_stm(stm)["tdem_system"]["variables"]

        assert "??" in variables["data_normalized"]


class TestTheMomentAfterMerging:
    """A yml that puts back the real loop gets the real loop's moment."""

    def test_it_is_the_loop_the_system_ends_up_with(self):
        transmitter = System.metadata_from_stm(
            TEMPEST, metadata=dict(variables=dict(transmitter=dict(
                area=155, number_of_turns=1, peak_current=560))))["tdem_system"]["variables"]["transmitter"]

        assert transmitter["moment"] == transmitter["peak_moment"] == pytest.approx(155 * 560)

    def test_normalisation_is_still_judged_by_the_file(self):
        """The forward model scales by the file's loop, not the one put back."""
        variables = System.metadata_from_stm(
            str(SYSTEMS / "SkytemLM.stm"), metadata=dict(variables=dict(transmitter=dict(
                area=340.82, number_of_turns=1, peak_current=9))))["tdem_system"]["variables"]

        assert variables["data_normalized"] is True

    def test_a_moment_the_yml_states_is_kept(self):
        transmitter = System.metadata_from_stm(
            TEMPEST, metadata=dict(variables=dict(transmitter=dict(peak_moment=86800))))[
                "tdem_system"]["variables"]["transmitter"]

        assert transmitter["peak_moment"] == 86800


class TestTheMomentIsChecked:
    """A moment stated beside its loop must agree with it, or the system will not build."""

    def build(self, **transmitter):
        from test_system import buildable
        system = buildable("tdem", transmitters=["LM", "HM"])
        system["variables"]["transmitter"].update(
            number_of_turns=[1, 4], area=[340.82, 340.82], peak_current=[9, 110], **transmitter)
        return System.from_dict(**system)

    def test_one_that_agrees_builds(self):
        moment = [9 * 340.82, 4 * 110 * 340.82]

        assert list(self.build(peak_moment=moment, moment=moment)["transmitter_peak_moment"].values) \
            == pytest.approx(moment)

    @pytest.mark.parametrize("field", ["peak_moment", "moment"])
    def test_one_that_disagrees_is_refused(self, field):
        with pytest.raises(ValueError, match="turns x area x peak current"):
            self.build(**{field: [9 * 340.82, 110 * 340.82]})

    def test_one_not_yet_known_is_not_checked(self):
        self.build(peak_moment=["not_defined", "not_defined"])


class TestWhatTheFileCannotSay:

    def test_the_on_and_off_times_are_left_open(self):
        """Reading them off the waveform needs a convention the file does not carry."""
        transmitter = System.metadata_from_stm(SKYTEM_LM)["tdem_system"]["variables"]["transmitter"]

        assert "??" in transmitter["on_time"]
        assert "??" in transmitter["off_time"]

    def test_the_instrument_is_left_open(self):
        """A .stm names a forward model, not a make and model."""
        assert "??" in System.metadata_from_stm(SKYTEM_LM)["tdem_system"]["instrument"]

    def test_a_field_the_file_never_mentions_keeps_its_placeholder(self):
        receiver = System.metadata_from_stm(SKYTEM_LM)["tdem_system"]["variables"]["receiver"]

        assert "??" in receiver["gain"]
        assert "??" in receiver["area"]["values"]


class TestProvenance:
    """Everything read that has no typed home is still recorded."""

    def test_the_file_it_came_from_is_recorded(self):
        system = System.metadata_from_stm(SKYTEM_LM)["tdem_system"]

        assert system["stm_file"] == "SkytemLM.stm"
        assert system["stm_name"] == "SkyTEMLM_ElkHills"

    def test_a_file_per_transmitter_is_recorded_in_order(self):
        system = System.metadata_from_stm({"LM": SKYTEM_LM, "HM": SKYTEM_HM})["tdem_system"]

        assert system["stm_file"] == "SkytemLM.stm, SkytemHM.stm"

    def test_a_forward_modelling_setting_is_recorded_as_one(self):
        """Not a property of the system, but the file said it."""
        system = System.metadata_from_stm(SKYTEM_LM)["tdem_system"]

        assert system["stm_forward_modelling_modelling_loop_radius"] == 10.416
        assert system["stm_forward_modelling_frequencies_per_decade"] == 5

    def test_a_filter_gspy_has_no_field_for_is_recorded(self):
        """Two stages with two orders, and nothing saying which coil they are on."""
        system = System.metadata_from_stm(SKYTEM_LM)["tdem_system"]

        assert system["stm_receiver_low_pass_filter_cut_off_frequency"] == [300000, 210000]
        assert system["stm_receiver_window_weighting_scheme"] == "AreaUnderCurve"

    def test_transmitters_that_disagree_are_both_recorded(self):
        system = System.metadata_from_stm({"LM": SKYTEM_LM, "HM": SKYTEM_HM})["tdem_system"]

        assert system["stm_transmitter_waveform_digitising_frequency"] == "3440640, 491520"


class TestFrequencyDomain:

    def test_a_coil_pair_is_labelled_by_its_frequency_and_orientation(self):
        variables = System.metadata_from_stm(RESOLVE)["fdem_system"]["variables"]

        assert variables["transmitter"]["label"] == ["380Z", "1776Z", "3345X", "8171Z",
                                                    "41020Z", "129550Z"]
        assert variables["receiver"]["label"] == variables["transmitter"]["label"]

    def test_the_frequencies_are_the_frequency_dimension(self):
        dimensions = System.metadata_from_stm(RESOLVE)["fdem_system"]["dimensions"]

        assert dimensions["frequency"]["centers"] == [380.0, 1776.0, 3345.0, 8171.0,
                                                     41020.0, 129550.0]

    def test_each_coil_keeps_its_orientation(self):
        variables = System.metadata_from_stm(RESOLVE)["fdem_system"]["variables"]

        assert variables["transmitter"]["orientation"] == ["z", "z", "x", "z", "z", "z"]
        assert variables["receiver"]["orientation"] == ["z", "z", "x", "z", "z", "z"]

    def test_the_separation_is_the_receiver_relative_to_the_transmitter(self):
        couplet = System.metadata_from_stm(RESOLVE)["fdem_system"]["variables"]["couplet"]

        assert couplet["txrx_dx"] == [7.93, 7.91, 9.03, 7.91, 7.91, 7.89]
        assert couplet["txrx_dy"] == [0.0] * 6
        assert couplet["txrx_dz"] == [0.0] * 6

    def test_a_pair_of_vertical_dipoles_is_coplanar_and_a_pair_of_horizontal_ones_coaxial(self):
        couplet = System.metadata_from_stm(RESOLVE)["fdem_system"]["variables"]["couplet"]

        assert couplet["orientation"] == ["coplanar", "coplanar", "coaxial", "coplanar",
                                          "coplanar", "coplanar"]

    def test_the_moment_is_taken_as_the_file_states_it(self):
        """Resolve states a unit moment per coil, negative where the coil is wound
        the other way up. Both the size and the sign are the file's to state.
        """
        variables = System.metadata_from_stm(RESOLVE)["fdem_system"]["variables"]

        assert variables["transmitter"]["moment"] == [1, 1, -1, 1, 1, 1]

    def test_a_table_file_has_no_moments_to_split_between_files(self):
        with pytest.raises(ValueError, match="one file"):
            System.metadata_from_stm({"a": RESOLVE, "b": RESOLVE})


class TestMergingWithYml:

    def test_what_you_already_know_wins_over_the_file(self):
        system = System.metadata_from_stm(
            SKYTEM_LM, metadata=dict(instrument="SkyTEM 304M",
                                     variables=dict(transmitter=dict(peak_current=9.0))),
        )["tdem_system"]

        assert system["instrument"] == "SkyTEM 304M"
        assert system["variables"]["transmitter"]["peak_current"] == 9.0

    def test_answering_one_field_leaves_the_rest_of_its_block_alone(self):
        """A shallow merge would replace the whole transmitter block."""
        transmitter = System.metadata_from_stm(
            SKYTEM_LM, metadata=dict(variables=dict(transmitter=dict(peak_current=9.0))),
        )["tdem_system"]["variables"]["transmitter"]

        assert transmitter["base_frequency"] == 210.0
        assert "??" in transmitter["on_time"]

    def test_a_yml_file_can_be_given_instead_of_a_dict(self, tmp_path):
        path = tmp_path / "extra.yml"
        path.write_text("instrument: SkyTEM 304M\nmode: ground\n")

        system = System.metadata_from_stm(SKYTEM_LM, metadata=str(path))["tdem_system"]

        assert system["instrument"] == "SkyTEM 304M"
        assert system["mode"] == "ground"

    def test_a_system_yml_is_unwrapped_and_names_the_system(self):
        """A system definition is filed under its own name, and that name carries over."""
        system = System.metadata_from_stm(
            SKYTEM_LM, metadata={"skytem_system": dict(instrument="SkyTEM 304M")})

        assert list(system) == ["skytem_system"]
        assert system["skytem_system"]["instrument"] == "SkyTEM 304M"


class TestItBuilds:

    def test_a_time_domain_system_builds_straight_from_the_file(self):
        system = System.from_stm({"LM": SKYTEM_LM, "HM": SKYTEM_HM}, receivers=["z", "x"])

        assert system.attrs["type"] == "system"
        assert (system.sizes["n_transmitter"], system.sizes["n_receiver"]) == (2, 2)
        assert system.sizes["n_couplet"] == 4
        assert list(system["couplet_label"].values) == ["LM_z", "HM_z", "LM_x", "HM_x"]

    def test_the_gates_it_builds_are_the_gates_in_the_file(self):
        system = System.from_stm({"LM": SKYTEM_LM, "HM": SKYTEM_HM})

        assert (system.sizes["lm_gate_times"], system.sizes["hm_gate_times"]) == (19, 26)

    def test_the_gate_times_a_couplet_names_are_dimensions_of_the_system(self):
        system = System.from_stm({"LM": SKYTEM_LM, "HM": SKYTEM_HM})

        assert set(np.unique(system["couplet_gate_times"].values)) <= set(system.sizes)

    def test_a_frequency_domain_system_builds_straight_from_the_file(self):
        system = System.from_stm(RESOLVE)

        assert system.sizes["frequency"] == 6
        assert system.sizes["n_couplet"] == 6

    def test_a_system_read_from_a_file_and_a_yml_builds(self):
        system = System.from_stm(SKYTEM_LM, name="skytem_system",
                                 metadata=dict(instrument="SkyTEM 304M"))

        assert system.attrs["instrument"] == "SkyTEM 304M"


class TestDumping:

    def test_a_dumped_system_reads_back_and_builds(self, tmp_path):
        """Which is the workflow: read the file, dump what it knows, fill in the rest."""
        path = tmp_path / "skytem_system.yml"
        System.metadata_from_stm({"LM": SKYTEM_LM, "HM": SKYTEM_HM},
                                 name="skytem_system").dump(str(path))

        back = Metadata.read(str(path))
        back.pop("directory", None)

        assert list(back) == ["skytem_system"]
        assert System.from_dict(**back["skytem_system"]).sizes["lm_gate_times"] == 19


class TestUnreadableFiles:

    def test_a_file_that_is_neither_shape_says_so(self, tmp_path):
        path = tmp_path / "nonsense.stm"
        path.write_text("this is not a system file\n")

        with pytest.raises(ValueError, match="not a GA-AEM"):
            read_stm(str(path))

    def test_a_block_left_open_says_which_one(self, tmp_path):
        path = tmp_path / "truncated.stm"
        path.write_text("System Begin\n\tTransmitter Begin\n\t\tPeakCurrent = 1\n"
                        "\tTransmitter End\n")

        with pytest.raises(ValueError, match="System"):
            read_stm(str(path))
