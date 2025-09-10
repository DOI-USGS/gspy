import os
import json
from copy import deepcopy

import numpy as np
import xarray as xr
import rioxarray as rio

from pprint import pprint

from ..metadata.Metadata import Metadata
from ..metadata.Variable_metadata import Variable_metadata
from .Dataset import Dataset
import xarray as xr

class Raster(Dataset):
    """Class defining a set of gridded data (2D or 3D).

    The raster class allows for single 2D rasters, or 'stacks' of multiple 2D rasters into a 3D block.

    ``Raster.read(metadata_file, spatial_ref, **kwargs)``

    Parameters
    ----------
    metadata_file : str, optional
        Json file name, by default None
    spatial_ref : dict or gspy.Spatial_ref or xarray.DataArray, optional
        Spatial ref object, by default None

    Returns
    -------
    xarray.Dataset

    See Also
    --------
    Raster.read : Class method for reading file into class
    gspy.Spatial_ref : For co-ordinate reference instantiation requirements

    """
    def __init__(self, xarray_obj):
        self._obj = xarray_obj

    @property
    def bounds(self):
        """Spatial bounds of the raster

        Returns
        -------
        list

        """
        return [self[ax].attrs['bounds'] for ax in self.dims]

    @property
    def is_tif(self):
        return self.type == 'tif'

    @classmethod
    def read(cls, metadata_file, spatial_ref=None, **kwargs):
        """
        Instantiate a Raster class from metadata and data files.

        When reading the metadata and data file, the following are established in order
        * User defined dimensions
        * User defined coordinates
        * X and Y are automatically pulled from the first raster

        Read the metadata and data files and to Raster class

        Parameters
        ----------
        metadata_file : str, optional
            Json file name, by default None
        spatial_ref : dict, gspy.Spatial_ref, or xarray.DataArray, optional
            Spatial ref object, by default None

        """
        tmp = xr.Dataset(attrs={})
        self = cls(tmp)

        if isinstance(metadata_file, str):
            json_md = self.read_metadata(metadata_file)
        else:
            json_md = metadata_file

        if spatial_ref is None:
            spatial_ref = json_md.get('spatial_ref', None)
            assert spatial_ref is not None, Exception("Spatial reference not defined in metadata file")

        self._obj = self.set_spatial_ref(spatial_ref)

        dimensions = json_md['dimensions']
        coordinates = json_md['coordinates']
        reverse_coordinates = {v:k for k,v in coordinates.items()}

        # Add the user defined coordinates-dimensions from the json file
        for key in list(dimensions.keys()):
            b = reverse_coordinates.get(key, key)
            assert isinstance(dimensions[key], (str, dict)), Exception("NOT SURE WHAT TO DO HERE YET....")
            if isinstance(dimensions[key], dict):
                # dicts are defined explicitly in the json file.
                self._obj = self.add_coordinate_from_dict(b, is_dimension=True, **dimensions[key])

        var_meta = Variable_metadata(**json_md['variables'])

        for var in var_meta.keys():
            if 'files' in var_meta[var]:
                self._obj = self.read_raster_using_metadata(var, json_md, **var_meta[var])

        # add global attrs to tabular, skip variables and dimensions
        self.update_attrs(**json_md['dataset_attrs'])

        return self._obj

    def read_raster_using_metadata(self, name, json_metadata, **kwargs):

        files = kwargs.pop('files')
        n_files = len(files)
        values = None

        cached_transform = None

        # Read each file in the variables metadata
        for i, file in enumerate(files):
            ds = self.open_rasterio(file)
            if cached_transform is None:
                cached_transform = ds.rio.transform()
            else:
                assert ds.rio.transform() == cached_transform, ValueError(f"raster file {file} has a mismatching GeoTransform")

            shape = ds.shape
            if n_files > 1:
                shape = (n_files, *shape) # Create a 3D array instead for more than one file.

            if values is None:
                if n_files == 1:
                    values = ds.values

                else:
                    values = np.empty(shape)

            if n_files > 1:
                values[i, :, :] = ds.values

        # Add the tranform to the spatial ref
        self._obj.spatial_ref.attrs['GeoTransform'] = cached_transform.to_gdal()

        # Add GS metadata to each matching coordinate in the file.
        coordinates = json_metadata['coordinates']

        # For each coordinate defined in the Raster FILE.
        # Match that coordinate with our metadata.
        # If it exists, attach it to xarray

        for coord in ds.coords:
            if (coord in coordinates) & (not coord in self._obj.coords):
                # if not already in xarray, add
                self._obj = self.add_coordinate_from_values(coord,
                                                values=ds[coord].values,
                                                is_projected=self.is_projected,
                                                is_dimension=True,
                                                **json_metadata['variables'][coordinates[coord]])
                # If coord already exists, pass ...
                # Assumes existing coord matches!!!!!
                # Not Yet Implemented: reconciliation step for adding multiple x,y,z,t coords OR resampling / realigning
                # input tiffs onto existing x,y,z,t grids
                #else:
                #    print('coordinate already exists... ', coord)

        kwargs['dimensions'] = np.asarray(kwargs['dimensions'])[::-1]

        # If an axis is given in the meta data, swap the axes of the temporary 3D array to stack along the user's defined axis
        # if 'stack_axis' in kwargs:
            # Case. tifs are x, y. stack along z. z is the 1st dimension
            #[nz, ny, nx].  no swapping.
            # Case. tifs are x, z. stack along y. y is the 2nd dimension.
            # user dims = [x, y, z]
            #[ny, nz, nx]. swap_to = 1, swap 0 with 1. gives [nz, ny, nx]
            # Case. tifs are y, z. stack along x. x is the 3rd dimension
            # user dims = [x, y, z]
            #[nx, nz, ny]. swap_to = 2, swap 0 with 2. gives []

            # swap_to = np.squeeze(np.argwhere(variable_dimensions == kwargs['stack_axis']))
            # if swap_to > 0:
            #     values = np.swapaxes(values, 0, swap_to)

        # Add the variable to the dataset
        self._obj = self.add_variable_from_dict(name, values=values, **kwargs)

        # Now handle the spatial ref.  This should be done FIRST
        raster_spatial_reference = [coord for coord in ds.coords if coord not in ('x', 'y')][0]

        if 'grid_mapping_name' in ds[raster_spatial_reference].attrs.keys():
            raster_spatial_reference_name = ds[raster_spatial_reference].attrs['grid_mapping_name']
            if raster_spatial_reference_name != self.spatial_ref.attrs['grid_mapping_name']:
                raise NotImplementedError(f"Need to reproject input file to match survey spatial ref, for variable {name}")
        # elif 'crs_wkt' in ds[raster_spatial_reference].attrs.keys():
        #     raster_spatial_reference_name = ds[raster_spatial_reference].attrs['crs_wkt']
        #     if raster_spatial_reference_name != self.spatial_ref.attrs['crs_wkt']:
        #         raise NotImplementedError(f"Need to reproject input file to match survey spatial ref, for variable {name}")
        else:
            print(f'WARNING: cannot identify CRS for input [{name}] raster, will assume the data matches the survey spatial_ref!')

        # Reproject if input CRS does not match Survey
        # if raster_spatial_reference_name != self.spatial_ref.attrs['grid_mapping_name']:
        #     print('Grid CRS [{}] does not match Survey CRS [{}], reprojecting to Survey CRS'.format(raster_spatial_reference_name, self.spatial_ref.attrs['grid_mapping_name']))
        #     if self.spatial_ref.attrs['wkid'] != "None":
        #         target_crs = self.spatial_ref.attrs['wkid']
        #     else:
        #         target_crs = self.spatial_ref.attrs['crs_wkt']
        #     print('Reprojecting ...')

        #     # get fill value from file, if present
        #     if '_FillValue' in ds.attrs:
        #         nodata = ds.attrs['_FillValue']
        #     else:
        #         nodata = None

        #     # supersede fill value from file with variable metadata value, if present
        #     if 'null_value' in json_metadata['variables'][name]:
        #         if json_metadata['variables'][name]['null_value'] != 'not_defined':
        #             nodata = json_metadata['variables'][name]['null_value']

        #     # reproject, accounting for nodata value if present
        #     if nodata is None:
        #         ds = ds.rio.reproject(target_crs)
        #     else:
        #         ds = ds.rio.reproject(target_crs, nodata=nodata)

        return self._obj

    def open_rasterio(self, filename):
        """Reads GeoTIFF file

        Uses rioxarray to read GeoTIFF file as an xarray Dataset

        Parameters
        ----------
        filename : str
            Name of GeoTIFF file

        Returns
        -------
        ds : xarray.Dataset
            Dataset containing the GeoTIFF variable

        """
        if isinstance(filename, list):
            filename = filename[0]
        ds = rio.open_rasterio(filename)

        # clean up
        ds = ds.squeeze().drop('band')
        if '_FillValue' in ds.attrs:
            ds.values[ds.values == ds.attrs['_FillValue']] = np.nan
            #ds.attrs['null_value'] = ds.attrs['_FillValue']

        return ds

    def read_var_netcdf(self, filename, key, var_meta):
        """ Reads variable from NetCDF file and adds to Raster xarray

        Parameters
        ----------
        filename : str
            Name of NetCDF file to read
        key : str
            Variable name
        var_meta : dict
            Variable attributes

        Raises
        ------
        NotImplementedError
            Function is planned but not yet implemented
        """
        raise NotImplementedError('reading individual data variables from netcdf is not currently supported')

    def _reproject_xarray(self):
        """ Reprojects xarray coordinate reference system

        If the xarray object's coordinate reference system does not match that of the survey,
        it is reprojected using rioxarray's reproject function. A WKID or CRS_WKT must be present
        within the survey's spatial_ref to define the target coordinate system.

        If bound keys are present, they are are dropped before the reprojection. New bound keys are
        then added after reprojection using the new coordinates.

        Returns
        -------
        out : gspy.Raster
            Raster class

        """

        bnds_keys = list(self.data_vars.keys())
        check_keys = ['x_bnds', 'y_bnds', 'z_bnds']
        bnds_present = [k in bnds_keys for k in check_keys]

        for i in range(3):
            if bnds_present[i]:
                self._obj = self._obj.gs.drop_vars(check_keys[i])

        if self.spatial_ref['wkid'] != "None":
            target_crs = f"{self.spatial_ref['authority']}:{self.spatial_ref['wkid']}"
        else:
            target_crs = self.spatial_ref['crs_wkt']

        self._obj = self._obj.gs.rio.reproject(target_crs)
        self._compute_bounds()

        return self._obj

    def write_metadata_template(self, filename="raster_md.yml"):
        """Write JSON metadata template for a raster dataset

        Outputs a template JSON metadata file needed for adding Raster data. All required
        dictionaries are printed (dataset_attrs, key_mapping, raster_files, variables).
        Additional dictionaries can be optionally added to document more information or
        ancillary metadata relevant to the specific Raster data.

        Raises
        ------
        Exception
             Tells user to specify metadata file when instantiating Raster data

        """

        print("\nGenerating an empty metadata file template for the Raster data.\n")

        out = {}
        out["dataset_attrs"] = {
            "content": "<summary statement of what the dataset contains>",
            "comment": "<additional details or ancillary information>"
            }

        out["coordinates"] = {
            "x" : "lat",
            "y" : "lon",
            "z" : "depth"
            }

        out['dimensions'] = {
            "x" : "Easting_Albers",
            "y" : "Northing_Albers",
            "depth": {
                "standard_name": "depth",
                "long_name": "Depth below earth's surface DTM",
                "units": "m",
                "null_value": "not_defined",
                "length" : 3,
                "increment" : 5.0,
                "origin" : 0.0,
                "axis" : "Z",
                "positive" : "down",
                "datum" : "ground surface"
                }
        }

        out["variables"] = {
            "lat": {
                "standard_name": "",
                "long_name": "",
                "units": "",
                "null_value": "",
                "axis" : "x"
                },
            "lon": {
                "standard_name": "",
                "long_name": "",
                "units": "",
                "null_value": "",
                "axis" : "y"
                },
            "elev": {
                "standard_name": "",
                "long_name": "",
                "units": "",
                "null_value": "",
                "axis" : "z"
                },
            "map_in_xy": {
                "dimensions" : ["x", "y"],
                "standard_name": "",
                "long_name": "",
                "units": "",
                "null_value": "",
                "files" : "map.tif"
                },
            "depth_slice_maps": {
                "dimensions" : ["x", "y", "z"],
                "standard_name": "",
                "long_name": "",
                "units": "",
                "null_value": "",
                "files" : ["slice_0.tif", "slice_1.tif", "slice_2.tif"]
                }
            }

        dump_metadata_to_file(out, filename)

    def to_tif(self):
        """ Export GeoTIFF files from xarray

        2D variables are exported directly to GeoTIFF files, one for each variable, following
        the naming convention "{variable}.tif"

        3D variables are sliced along the right most dimension and exported to incremented GeoTIFF
        files following the naming convention "{variable}_{i}.tif".

        """
        raise Exception("Needs fixing")

        for var in self.data_vars:
            # skip bnds variables
            if 'bnds' not in var:
                ds = deepcopy(self[var])

                # remove grid_mapping
                if 'grid_mapping' in ds.attrs.keys():
                    del ds.attrs['grid_mapping']

                # set _FillValue
                ds.attrs['_FillValue'] = ds.attrs['null_value']

                # if 3D variable, slice along stack dimension
                if 'stack' in ds.dims:
                    for s in ds['stack'].values:
                        ds.sel(stack=s).rio.to_raster(f"{var}_{s}.tif")
                else:
                    ds.rio.to_raster(f"{var}.tif")
