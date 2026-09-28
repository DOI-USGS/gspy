"""How a written variable is stored: compressed, shuffled, and chunked.

The layout is chosen per variable from its shape, so the chunk tests are about
arithmetic. The writing tests open the file with h5py, since the filters and the
chunks are HDF5's and xarray does not report them faithfully on read.
"""
import h5py
import numpy as np
import pytest
import xarray as xr

import gspy
from gspy.utilities.encoding import CHUNK_BYTES, chunk_shape, dataset_encoding


def dataset():
    rng = np.random.default_rng(0)
    return xr.Dataset(
        {"emz": (("index", "gate"), rng.normal(size=(20000, 20))),
         "x": (("index",), np.linspace(0.0, 1.0, 20000)),
         "label": (("gate",), np.array([f"g{i}" for i in range(20)])),
         "base_frequency": ((), 30.0)},
        coords={"index": np.arange(20000), "gate": np.arange(20)})


class TestChunkShape:

    def test_something_that_fits_is_one_chunk(self):
        assert chunk_shape((6,), 8) == (6,)
        assert chunk_shape((100, 20), 8) == (100, 20)

    def test_a_chunk_is_no_bigger_than_the_target(self):
        shape = chunk_shape((200000, 20), 8)

        assert np.prod(shape) * 8 <= CHUNK_BYTES

    def test_a_transient_stays_whole(self):
        """Halving the largest dimension cuts along the soundings long before the
        gates, so a whole transient is read from one chunk.
        """
        assert chunk_shape((200000, 20), 8)[1] == 20

    def test_a_grid_is_tiled_rather_than_striped(self):
        rows, columns = chunk_shape((1155, 799), 8)

        assert np.prod((rows, columns)) * 8 <= CHUNK_BYTES
        assert 0.5 <= rows / columns <= 2

    def test_nothing_is_cut_finer_than_it_has_to_be(self):
        """One more doubling of any side would be over the target."""
        shape = chunk_shape((1155, 799), 8)

        for axis in range(2):
            bigger = list(shape)
            bigger[axis] *= 2
            assert np.prod(bigger) * 8 > CHUNK_BYTES

    def test_a_chunk_is_never_empty(self):
        shape = chunk_shape((1, 10**8), 8)

        assert shape[0] == 1 and 0 < shape[1] * 8 <= CHUNK_BYTES

    def test_an_empty_variable_is_not_chunked(self):
        """HDF5 has no chunk shape for a dimension of length zero."""
        assert chunk_shape((0, 20), 8) is None


class TestDatasetEncoding:

    def test_numeric_arrays_are_compressed_shuffled_and_chunked(self):
        encoding = dataset_encoding(dataset())["emz"]

        assert {key: encoding[key] for key in ("zlib", "complevel", "shuffle", "chunksizes")} \
            == dict(zlib=True, complevel=4, shuffle=True, chunksizes=chunk_shape((20000, 20), 8))

    def test_coordinates_are_numeric_arrays_too(self):
        assert "index" in dataset_encoding(dataset())

    def test_strings_are_left_to_xarray(self):
        assert "label" not in dataset_encoding(dataset())

    def test_a_scalar_is_filled_but_not_compressed(self):
        assert set(dataset_encoding(dataset())["base_frequency"]) == {"_FillValue"}

    def test_an_empty_variable_is_filled_but_not_compressed(self):
        ds = xr.Dataset({"nothing": (("index",), np.zeros(0))})

        assert set(dataset_encoding(ds)["nothing"]) == {"_FillValue"}

    def test_a_value_encoding_already_on_a_variable_is_kept(self):
        """A variable read back from a file carries how its values were written,
        and replacing its encoding would write NaN where there was a fill value.
        """
        ds = dataset()
        ds["emz"].encoding = {"_FillValue": -9999.0, "dtype": "float32",
                              "missing_value": -9999.0, "source": "old.nc",
                              "chunksizes": (1, 1), "zlib": False}

        encoding = dataset_encoding(ds)["emz"]

        assert (encoding["_FillValue"], encoding["dtype"], encoding["missing_value"]) \
            == (-9999.0, "float32", -9999.0)
        assert "source" not in encoding
        assert encoding["chunksizes"] == chunk_shape((20000, 20), 4)
        assert encoding["zlib"] is True

    def test_a_chunk_is_sized_by_what_is_written_not_what_is_held(self):
        """float32 on disk is half the bytes of the float64 in memory."""
        ds = dataset()
        ds["emz"].encoding = {"dtype": "float32"}

        assert dataset_encoding(ds)["emz"]["chunksizes"] == chunk_shape((20000, 20), 4)

    def test_the_compression_can_be_changed(self):
        encoding = dataset_encoding(dataset(), compression=dict(complevel=9))["emz"]

        assert (encoding["complevel"], encoding["shuffle"]) == (9, True)

    def test_no_compression_is_only_the_fill_values(self):
        """The layout is left to xarray, which writes the variable contiguously."""
        encoding = dataset_encoding(dataset(), compression=False)

        assert encoding and all(set(stated) == {"_FillValue"} for stated in encoding.values())

    def test_no_compression_still_passes_on_what_was_given(self):
        given = {"emz": dict(chunksizes=(10, 20))}

        assert dataset_encoding(dataset(), compression=False, given=given)["emz"]["chunksizes"] \
            == (10, 20)

    def test_naming_a_compression_setting_replaces_the_compression(self):
        encoding = dataset_encoding(dataset(), given={"emz": dict(zlib=False)})["emz"]

        assert encoding["zlib"] is False
        assert "complevel" not in encoding and "shuffle" not in encoding
        assert "chunksizes" in encoding

    def test_naming_chunks_replaces_the_chunks(self):
        encoding = dataset_encoding(dataset(), given={"emz": dict(chunksizes=(10, 20))})["emz"]

        assert encoding["chunksizes"] == (10, 20)
        assert encoding["zlib"] is True

    def test_anything_else_given_is_added(self):
        encoding = dataset_encoding(dataset(), given={"emz": dict(dtype="float32")})["emz"]

        assert encoding["dtype"] == "float32"
        assert encoding["zlib"] is True

    def test_an_encoding_can_be_given_for_a_variable_it_would_not_touch(self):
        encoding = dataset_encoding(dataset(), given={"label": dict(dtype="S1")})

        assert encoding["label"] == dict(dtype="S1")


class TestMissingValues:
    """A missing value has to be the fill value too. Left to itself xarray fills a
    float with NaN, and a file stating two different missing values cannot be
    written back out once read.
    """

    def with_missing_value(self, missing_value):
        ds = dataset()
        ds["emz"].attrs["missing_value"] = missing_value
        return ds

    def test_a_missing_value_is_the_fill_value(self):
        encoding = dataset_encoding(self.with_missing_value(-9999.0))

        assert encoding["emz"]["_FillValue"] == -9999.0

    def test_even_without_compression(self):
        encoding = dataset_encoding(self.with_missing_value(-9999.0), compression=False)

        assert encoding["emz"] == {"_FillValue": -9999.0}

    def test_a_missing_value_read_from_a_file_is_the_fill_value(self):
        """Decoding moves both off the attributes and onto the encoding."""
        ds = dataset()
        ds["emz"].encoding = {"missing_value": -9999.0, "_FillValue": np.nan}

        assert dataset_encoding(ds)["emz"]["_FillValue"] == -9999.0

    def test_a_placeholder_is_not_a_fill_value(self):
        encoding = dataset_encoding(self.with_missing_value("not_defined"))

        assert np.isnan(encoding["emz"]["_FillValue"])

    def test_a_placeholder_reads_back_as_an_attribute(self, tmp_path):
        path = tmp_path / "one.nc"
        self.with_missing_value("not_defined").gs.to_netcdf(path)

        emz = gspy.open_dataset(path)["emz"]
        assert emz.attrs["missing_value"] == "not_defined"
        assert "missing_value" not in emz.encoding

    def test_a_placeholder_on_strings_reads_back_as_an_attribute(self, tmp_path):
        """Left on the encoding, xarray casts it to a numpy string h5py cannot store."""
        path = tmp_path / "one.nc"
        ds = dataset()
        ds["label"].attrs["missing_value"] = "not_defined"
        ds.gs.to_netcdf(path)

        label = gspy.open_dataset(path)["label"]
        assert label.attrs["missing_value"] == "not_defined"
        assert "missing_value" not in label.encoding

    def test_the_fill_value_is_written(self, tmp_path):
        path = tmp_path / "one.nc"
        self.with_missing_value(-9999.0).gs.to_netcdf(path)

        with h5py.File(path) as handle:
            assert handle["emz"].attrs["_FillValue"] == -9999.0


class TestFillValues:
    """CF asks for a _FillValue, so every numeric variable is written with one.

    Where no missing value is stated it is NaN for a float and netCDF's own default
    for an integer. A dimension coordinate is written with none, since CF allows a
    coordinate variable no missing values.
    """

    def with_integers(self):
        ds = dataset()
        ds["line"] = (("index",), np.arange(20000, dtype="int32"))
        ds["count"] = (("index",), np.arange(20000, dtype="int64"))
        return ds

    def test_a_float_is_filled_with_nan(self):
        assert np.isnan(dataset_encoding(dataset())["x"]["_FillValue"])

    @pytest.mark.parametrize("name, fill", [("line", -2147483647),
                                            ("count", -9223372036854775806)])
    def test_an_integer_is_filled_with_the_netcdf_default(self, name, fill):
        assert dataset_encoding(self.with_integers())[name]["_FillValue"] == fill

    def test_the_default_is_for_the_type_written(self):
        ds = self.with_integers()
        ds["count"].encoding = {"dtype": "int16"}

        assert dataset_encoding(ds)["count"]["_FillValue"] == -32767

    def test_a_fill_value_read_from_a_file_is_kept(self):
        ds = dataset()
        ds["x"].encoding = {"_FillValue": -1.0}

        assert dataset_encoding(ds)["x"]["_FillValue"] == -1.0

    def test_a_dimension_coordinate_has_none(self):
        encoding = dataset_encoding(dataset())

        assert encoding["index"]["_FillValue"] is None
        assert encoding["gate"]["_FillValue"] is None

    def test_a_boolean_is_left_to_xarray(self):
        ds = dataset()
        ds["flag"] = (("index",), np.zeros(20000, dtype=bool))

        assert "_FillValue" not in dataset_encoding(ds)["flag"]

    def test_every_numeric_variable_is_written_with_one(self, tmp_path):
        path = tmp_path / "one.nc"
        self.with_integers().gs.to_netcdf(path, compression=False)

        with h5py.File(path) as handle:
            for name in ("emz", "x", "base_frequency", "line", "count"):
                assert "_FillValue" in handle[name].attrs, name
            assert "_FillValue" not in handle["index"].attrs

    def test_an_integer_filled_by_default_reads_back_as_an_integer(self, tmp_path):
        path = tmp_path / "one.nc"
        ds = self.with_integers()
        ds.gs.to_netcdf(path)

        back = gspy.open_dataset(path)
        for name in ("line", "count"):
            assert back[name].dtype == ds[name].dtype, name
            np.testing.assert_array_equal(back[name].values, ds[name].values)
            assert back[name].encoding["_FillValue"] == dataset_encoding(ds)[name]["_FillValue"]

    def test_an_integer_with_a_stated_missing_value_is_still_masked(self, tmp_path):
        path = tmp_path / "one.nc"
        ds = self.with_integers()
        ds["line"][0] = -1
        ds["line"].attrs["missing_value"] = -1
        ds.gs.to_netcdf(path)

        assert np.isnan(gspy.open_dataset(path)["line"].values[0])

    def test_a_default_filled_integer_survives_a_rewrite(self, tmp_path):
        self.with_integers().gs.to_netcdf(tmp_path / "a.nc")
        gspy.open_dataset(tmp_path / "a.nc").gs.to_netcdf(tmp_path / "b.nc")

        assert gspy.open_dataset(tmp_path / "b.nc")["line"].dtype == np.int32


class TestFillValueOnceBuilt:
    """A variable GSPy builds carries its fill value before it is written."""

    def build(self, values, **attrs):
        from gspy.gs_dataarray.DataArray import DataArray
        attrs = {"standard_name": "x", "long_name": "x", "units": "m",
                 "missing_value": "not_defined", **attrs}
        return DataArray.from_values("x", values=values, dimensions=["index"], **attrs)

    def test_a_float(self):
        assert np.isnan(self.build(np.zeros(3)).encoding["_FillValue"])

    def test_an_integer(self):
        assert self.build(np.zeros(3, dtype="int32")).encoding["_FillValue"] == -2147483647

    def test_a_stated_missing_value(self):
        assert self.build(np.zeros(3), missing_value=-9999.0).encoding["_FillValue"] == -9999.0

    def test_strings_have_none(self):
        assert "_FillValue" not in self.build(np.array(["a", "b", "c"])).encoding


class TestRewriting:
    """What was read can be written again."""

    @pytest.mark.parametrize("compression", [True, False])
    def test_a_placeholder_missing_value(self, tmp_path, compression):
        ds = dataset()
        ds["emz"].attrs["missing_value"] = "not_defined"
        ds.gs.to_netcdf(tmp_path / "a.nc")

        gspy.open_dataset(tmp_path / "a.nc").gs.to_netcdf(tmp_path / "b.nc",
                                                          compression=compression)

        back = gspy.open_dataset(tmp_path / "b.nc")
        np.testing.assert_array_equal(back["emz"].values, ds["emz"].values)
        assert back["emz"].attrs["missing_value"] == "not_defined"

    @pytest.mark.parametrize("compression", [True, False])
    def test_a_file_stating_two_missing_values(self, tmp_path, compression):
        """As written before the missing value was made the fill value."""
        ds = dataset()
        ds["emz"][0, 0] = -9999.0
        ds["emz"].attrs["missing_value"] = -9999.0
        ds.to_netcdf(tmp_path / "a.nc", engine="h5netcdf")

        gspy.open_dataset(tmp_path / "a.nc").gs.to_netcdf(tmp_path / "b.nc",
                                                          compression=compression)

        back = gspy.open_dataset(tmp_path / "b.nc", mask_and_scale=False)["emz"].values
        np.testing.assert_array_equal(back, ds["emz"].values)


class TestWritingADataset:

    def test_a_dataset_written_on_its_own_is_compressed_and_chunked(self, tmp_path):
        path = tmp_path / "one.nc"
        dataset().gs.to_netcdf(path)

        with h5py.File(path) as handle:
            emz = handle["emz"]
            assert (emz.compression, emz.compression_opts, emz.shuffle) == ("gzip", 4, True)
            assert emz.chunks == chunk_shape((20000, 20), 8)

    def test_compression_can_be_turned_off(self, tmp_path):
        path = tmp_path / "one.nc"
        dataset().gs.to_netcdf(path, compression=False)

        with h5py.File(path) as handle:
            assert handle["emz"].compression is None
            assert handle["emz"].chunks is None

    def test_the_values_survive(self, tmp_path):
        path = tmp_path / "one.nc"
        ds = dataset()
        ds.gs.to_netcdf(path)

        back = gspy.open_dataset(path)
        np.testing.assert_array_equal(back["emz"].values, ds["emz"].values)

