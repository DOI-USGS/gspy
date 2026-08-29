"""Coordinate, DataArray and Spatial_ref: the pieces that build a CF variable.

These are small enough to test directly, which is where the metadata rules that
the rest of gspy relies on actually live.
"""
import numpy as np
import pytest
from gspy.gs_dataarray.Coordinate import Coordinate
from gspy.gs_dataarray.DataArray import DataArray
from gspy.gs_dataarray.Spatial_ref import Spatial_ref

# the minimum GS/CF metadata for any variable
MD = {"standard_name": "depth", "long_name": "depth below surface",
      "units": "m", "missing_value": "not_defined"}


def coordinate(name="depth", **kwargs):
    md = {**MD, "standard_name": name}
    return Coordinate.from_dict(name, is_dimension=True, **{**md, **kwargs})


class TestCoordinateValues:

    def test_explicit_centers_are_used_as_given(self):
        assert np.allclose(coordinate(centers=[2.5, 7.5, 20.0]).values, [2.5, 7.5, 20.0])

    def test_origin_increment_length_generates_centers(self):
        assert np.allclose(coordinate(origin=-0.5, increment=1.0, length=4).values,
                           [-0.5, 0.5, 1.5, 2.5])

    def test_origin_and_increment_default_when_only_length_is_given(self):
        assert np.allclose(coordinate(length=3).values, [0, 1, 2])

    def test_without_centers_bounds_or_length_it_refuses(self):
        with pytest.raises(AssertionError):
            coordinate()

    def test_a_dimension_coordinate_is_its_own_dim(self):
        assert coordinate(length=3).dims == ("depth",)

    def test_centers_can_be_derived_from_bounds(self):
        """Bounds are 2xN — a row of lower edges then a row of upper edges — which is
        the layout the metadata files use and what Dataset.add_bounds_to_coordinate
        documents.
        """
        assert np.allclose(coordinate(bounds=[[0, 1, 2], [1, 2, 3]]).values,
                           [0.5, 1.5, 2.5])


class TestStandardCoordinates:
    """x, y, z and t carry extra CF requirements."""

    def test_a_projected_x_gets_the_cf_standard_name(self):
        x = Coordinate.from_dict("x", is_projected=True, is_dimension=True,
                                 centers=[1.0, 2.0], **{**MD, "standard_name": "x"})
        assert x.attrs["standard_name"] == "projection_x_coordinate"

    def test_an_unprojected_x_keeps_its_name(self):
        x = Coordinate.from_dict("x", is_dimension=True, centers=[1.0, 2.0],
                                 **{**MD, "standard_name": "x"})
        assert x.attrs["standard_name"] == "x"

    def test_metres_are_spelled_out_for_gis_readers(self):
        assert coordinate(length=3, units="m").attrs["units"] == "meters"

    def test_z_requires_positive_and_datum(self):
        with pytest.raises(AssertionError):
            Coordinate.from_dict("z", is_dimension=True, centers=[1.0, 2.0],
                                 **{**MD, "standard_name": "z"})

    def test_z_rejects_a_positive_that_is_not_up_or_down(self):
        with pytest.raises(AssertionError):
            Coordinate.from_dict("z", is_dimension=True, centers=[1.0, 2.0],
                                 positive="sideways", datum="ground surface",
                                 **{**MD, "standard_name": "z"})

    def test_t_requires_a_datum(self):
        with pytest.raises(AssertionError):
            Coordinate.from_dict("t", is_dimension=True, centers=[1.0, 2.0],
                                 **{**MD, "standard_name": "t"})

    def test_a_standard_coordinate_gets_its_axis_attribute(self):
        z = Coordinate.from_dict("z", is_dimension=True, centers=[1.0, 2.0],
                                 positive="up", datum="ground surface",
                                 **{**MD, "standard_name": "z"})
        assert z.attrs["axis"] == "Z"

    def test_an_explicit_axis_is_upper_cased(self):
        z = Coordinate.from_dict("z", is_dimension=True, centers=[1.0, 2.0], axis="z",
                                 positive="up", datum="ground surface",
                                 **{**MD, "standard_name": "z"})
        assert z.attrs["axis"] == "Z"


class TestBounds:

    def test_explicit_edges_become_pairs(self):
        depth = coordinate(centers=[2.5, 7.5, 20.0])
        bounds = DataArray.add_bounds_to_coordinate_dimension(
            depth, "depth", bounds=[0.0, 5.0, 10.0, 25.0],
            dims=("depth", "nv"), coords={"depth": depth.values})
        assert bounds.values.tolist() == [[0.0, 5.0], [5.0, 10.0], [10.0, 25.0]]

    def test_lower_and_upper_edge_rows_pair_up_per_cell(self):
        """The 2xN layout the metadata files use. Reshaping instead of transposing
        pairs lower edges with lower edges and gives cell j the bounds of cell 2j.
        """
        depth = coordinate(centers=[1.0, 3.1, 5.405])
        bounds = DataArray.add_bounds_to_coordinate_dimension(
            depth, "depth", bounds=[[0.0, 2.0, 4.2], [2.0, 4.2, 6.61]],
            dims=("depth", "nv"), coords={"depth": depth.values})
        assert bounds.values.tolist() == [[0.0, 2.0], [2.0, 4.2], [4.2, 6.61]]

    def test_explicit_pairs_are_taken_as_given(self):
        depth = coordinate(centers=[2.5, 7.5, 20.0])
        bounds = DataArray.add_bounds_to_coordinate_dimension(
            depth, "depth", bounds=[[0.0, 5.0], [5.0, 10.0], [10.0, 25.0]],
            dims=("depth", "nv"), coords={"depth": depth.values})
        assert bounds.values.tolist() == [[0.0, 5.0], [5.0, 10.0], [10.0, 25.0]]

    def test_bounds_metadata_is_derived_from_the_coordinate(self):
        depth = coordinate(centers=[2.5, 7.5, 20.0])
        bounds = DataArray.add_bounds_to_coordinate_dimension(
            depth, "depth", bounds=[0.0, 5.0, 10.0, 25.0],
            dims=("depth", "nv"), coords={"depth": depth.values})
        assert bounds.attrs["standard_name"] == "depth_bounds"
        assert bounds.attrs["long_name"].endswith("cell boundaries")
        assert bounds.attrs["units"] == depth.attrs["units"]

    def test_the_wrong_number_of_edges_is_rejected(self):
        depth = coordinate(centers=[2.5, 7.5, 20.0])
        with pytest.raises(AssertionError):
            DataArray.add_bounds_to_coordinate_dimension(
                depth, "depth", bounds=[0.0, 5.0], dims=("depth", "nv"),
                coords={"depth": depth.values})

    def test_computed_bounds_use_one_median_width_for_every_cell(self):
        """Current behaviour, and not CF-clean for an irregular coordinate: every
        cell gets the median spacing (8.75 here), so the cells overlap instead of
        tiling and the first one starts below zero. Regular coordinates are fine.
        """
        depth = coordinate(centers=[2.5, 7.5, 20.0])
        bounds = DataArray.add_bounds_to_coordinate_dimension(
            depth, "depth", dims=("depth", "nv"), coords={"depth": depth.values})
        assert np.allclose(bounds.values,
                           [[-1.875, 6.875], [3.125, 11.875], [15.625, 24.375]])

    def test_a_coordinate_that_already_has_bounds_is_left_alone(self):
        depth = coordinate(centers=[2.5, 7.5, 20.0])
        depth.attrs["bounds"] = "depth_bnds"
        assert DataArray.add_bounds_to_coordinate_dimension(depth, "depth") is None


class TestVariableMetadata:

    def test_all_four_gs_entries_are_required(self):
        with pytest.raises(AssertionError, match="missing entries"):
            DataArray.check_metadata("v", standard_name="v")

    def test_a_complete_set_passes(self):
        DataArray.check_metadata("v", **MD)

    def test_the_template_offers_the_four_entries(self):
        assert DataArray.metadata_template() == {k: "not_defined" for k in
                                                 ("standard_name", "long_name",
                                                  "units", "missing_value")}

    def test_from_values_needs_dimensions_for_an_array(self):
        with pytest.raises(AssertionError, match="dimensions must be specified"):
            DataArray.from_values("v", values=np.r_[1.0, 2.0], **MD)

    def test_from_values_attaches_grid_mapping_and_valid_range(self):
        v = DataArray.from_values("v", values=np.r_[1.0, 5.0, 3.0],
                                  dimensions=["index"], **MD)
        assert v.attrs["grid_mapping"] == "spatial_ref"
        assert np.allclose(v.attrs["valid_range"], [1.0, 5.0])

    def test_a_dimension_count_mismatch_is_rejected(self):
        with pytest.raises(AssertionError, match="Mismatching dims"):
            DataArray.from_values("v", values=np.r_[1.0, 2.0],
                                  dimensions=["index", "channel"], **MD)


class TestMissingValues:

    def test_nans_become_the_declared_missing_value(self):
        out = DataArray.catch_nan(np.r_[1.0, np.nan], "v", missing_value=-9999.0)
        assert np.allclose(out, [1.0, -9999.0])

    def test_nans_without_a_declared_missing_value_are_an_error(self):
        with pytest.raises(AssertionError, match="no defined missing value"):
            DataArray.catch_nan(np.r_[1.0, np.nan], "v")

    def test_strings_pass_straight_through(self):
        assert DataArray.catch_nan(np.array(["a", "b"]), "v").tolist() == ["a", "b"]

    def test_valid_range_ignores_nans(self):
        assert np.allclose(DataArray.valid_range(np.r_[1.0, np.nan, 5.0], "v"), [1.0, 5.0])

    def test_valid_range_excludes_the_missing_value(self):
        assert np.allclose(
            DataArray.valid_range(np.r_[1.0, -9999.0, 5.0], "v", missing_value=-9999.0),
            [1.0, 5.0])


class TestSpatialRef:

    def test_an_epsg_prefixed_wkid_is_recognised(self):
        sr = Spatial_ref.from_dict({"wkid": "EPSG:26915"})
        assert sr.attrs["authority"] == "EPSG"
        assert sr.attrs["wkid"] == "26915"
        assert sr.attrs["grid_mapping_name"] == "transverse_mercator"

    def test_an_explicit_authority_is_honoured(self):
        sr = Spatial_ref.from_dict({"wkid": "26915", "authority": "EPSG"})
        assert sr.attrs["wkid"] == "26915"

    def test_wkt_is_accepted(self):
        wkt = Spatial_ref.from_dict({"wkid": "EPSG:26915"}).attrs["crs_wkt"]
        assert Spatial_ref.from_dict({"crs_wkt": wkt}).attrs["wkid"] == "26915"

    def test_a_proj_string_is_accepted(self):
        sr = Spatial_ref.from_dict({"proj_string": "+proj=utm +zone=15 +datum=NAD83"})
        assert sr.attrs["grid_mapping_name"] == "transverse_mercator"

    def test_nothing_at_all_defaults_to_wgs84(self):
        assert Spatial_ref.from_dict({}).attrs["wkid"] == "4326"

    def test_the_template_lists_every_way_in(self):
        assert set(Spatial_ref.metadata_template()) == {"wkid", "crs_wkt",
                                                        "proj_string", "prj_file"}

    def test_a_bare_wkid_defaults_to_epsg(self):
        assert Spatial_ref.from_dict({"wkid": "26915"}).attrs["wkid"] == "26915"
