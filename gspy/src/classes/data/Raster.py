import os
import json
from copy import deepcopy

import numpy as np
import xarray as xr
import rioxarray

from pprint import pprint

from .Variable_Metadata import variable_metadata
from .xarray_gs.DataArray_gs import DataArray_gs
from .Data import Data
# from .json_handler import attach_coordinate_to_xarray_from_dict

class Raster(Data):
    """Class defining a set of gridded data (2D or 3D).

    Examples of raster data include radiometric or magnetic grids, interpolated resistivity models, etc.

    ``Raster(metadata_file, spatial_ref, **kwargs)``

    Parameters
    ----------
    metadata_file : str
        Path to the JSON metadata file
    spatial_ref : gspy.Spatial_ref
        Coordinate reference system

    Returns
    -------
    out : gspy.Raster
        Raster Class

    See Also
    --------
    gspy.Spatial_ref : For co-ordinate reference instantiation requirements

    """
    __slots__ = ()
    # def __init__(self, metadata_file, spatial_ref, **kwargs):

    #     if metadata_file is None and spatial_ref is None:
    #         return

    #     super().__init__()

    @property
    def bounds(self):
        return [self[ax].attrs['bounds'] for ax in self.dims]

    @property
    def is_tif(self):
        return self.type == 'tif'

    @classmethod
    def read(cls, metadata_file, spatial_ref=None, netcdf_file=None, **kwargs):
        """Read the metadata and data files and to Raster class

        Parses the json metadata file and adds them to the appropriate locations.
        An xarray Dataset is created and the 'raster_files' dictionary in the metadata file
        is used to read raster data files into named variables.

        Parameters
        ----------
        metadata_file : str
            JSON metadata file
        spatial_ref : gspy.Spatial_ref
            Coordinate reference system

        """
        self = cls()
        self = self.set_spatial_ref(spatial_ref)

        if netcdf_file is not None:
            return Raster.read_netcdf(netcdf_file, spatial_ref=spatial_ref, **kwargs)
        else:
            # read the metadata file
            json_md = self.read_metadata(metadata_file)

            dimensions = json_md['dimensions']
            coordinates = json_md['coordinates']
            reverse_coordinates = {v:k for k,v in coordinates.items()}

            #
            for key in list(dimensions.keys()):
                b = reverse_coordinates.get(key, key)
                assert isinstance(dimensions[key], (str, dict)), Exception("NOT SURE WHAT TO DO HERE YET....")
                if isinstance(dimensions[key], dict):
                    # dicts are defined explicitly in the json file.
                    self = self.add_coordinate_from_dict(b, is_dimension=True, **dimensions[key])

            var_meta = variable_metadata(**json_md['variable_metadata'])

            for var in var_meta.keys():
                if 'files' in var_meta[var]:
                    self = self.read_raster_using_metadata(var, json_md, **var_meta[var])

            # path = Path(metadata_file).parent.absolute()
            # rfiles = json_md.pop('raster_files')
            # for variable, item in rfiles.items():
            #     if len(item) == 1:
            #         reader = self.read_raster
            #     else:
            #         reader = self.read_rasters

            #     # SOMETHING NEEDS TO HAPPEN HERE TO ADD DIMENSION TO THE XARRAY
            #     reader([os.path.join(path, x) for x in item], variable, var_meta, **json_md)

            # # add global attrs to tabular
            #self._add_general_metadata_to_xarray(json_md['dataset_attrs'])
            self.update_attrs(**json_md['dataset_attrs'])

        # Check for conforming spatial refs???

        # # add global attrs to linedata
        # self._add_general_metadata_to_xarray({x: dic[x] for x in dic if x not in ['units_and_nulls','variable_files']})
        return self

    def read_raster_using_metadata(self, name, json_metadata, **kwargs):
        """Read multiple raster files and stack into single variable

        Combines multiple 2D raster files into a 3D variable along a stacking dimension.
        Currently the stacking dimension defaults to "stack" and increments starting at 0. In future
        releases this dimension will be customizable and passed through the JSON metadata file.

        Parameters
        ----------
        filenames : list of str
            List of raster files to read and stack, in order of stacking dimension
        key : str
            Name of variable assigned to xarray
        var_meta : dict
            Dictionary of variable metadata

        Returns
        -------
        out : gspy.Raster
            Raster class

        """
        files = kwargs.pop('files')
        n_files = len(files)
        values = None
        # Read each file in the variables metadata
        for i, file in enumerate(files):
            ds = self.read_tif(file)

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


        # Add GS metadata to each matching coordinate in the file.
        coordinates = json_metadata['coordinates']

        # For each coordinate defined in the Raster FILE.
        # Match that coordinate with our metadata.
        # If it exists, attach it to xarray
        for coord in ds.coords:
            if (coord in coordinates) & (not coord in self.coords):
                # if not already in xarray, add
                self = self.add_coordinate_from_values(coord,
                                                       ds[coord].values,
                                                       is_projected=self.is_projected,
                                                       is_dimension=True,
                                                       **json_metadata['variable_metadata'][coordinates[coord]])
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
        self.add_variable_from_values(name, values, **kwargs)

        # Now handle the spatial ref.  This should be done FIRST
        raster_spatial_reference = [coord for coord in ds.coords if coord not in ('x', 'y')][0]

        if 'grid_mapping_name' in ds[raster_spatial_reference].attrs.keys():
            raster_spatial_reference_name = ds[raster_spatial_reference].attrs['grid_mapping_name']
            if raster_spatial_reference_name != self.spatial_ref.attrs['grid_mapping_name']:
                raise NotImplementedError("Need to reproject input file to match survey spatial ref, for variable {}".format(name))
        # elif 'crs_wkt' in ds[raster_spatial_reference].attrs.keys():
        #     raster_spatial_reference_name = ds[raster_spatial_reference].attrs['crs_wkt']
        #     if raster_spatial_reference_name != self.spatial_ref.attrs['crs_wkt']:
        #         raise NotImplementedError("Need to reproject input file to match survey spatial ref, for variable {}".format(name))
        else:
            print('WARNING: cannot identify CRS for input [{}] raster, will assume the data matches the survey spatial_ref!'.format(name))



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
        #     if 'null_value' in json_metadata['variable_metadata'][name]:
        #         if json_metadata['variable_metadata'][name]['null_value'] != 'not_defined':
        #             nodata = json_metadata['variable_metadata'][name]['null_value']

        #     # reproject, accounting for nodata value if present
        #     if nodata is None:
        #         ds = ds.rio.reproject(target_crs)
        #     else:
        #         ds = ds.rio.reproject(target_crs, nodata=nodata)

        return self

    # def read(self, type, data_filename, key, units, **kwargs):

    #     if type == 'tif':
    #         return self.read_tif(data_filename, key, units, **kwargs)

    #     elif type == 'tifs':
    #         return self.read_tifs(data_filename, key, units, **kwargs)

    #     elif type == 'netcdf':
    #         return self.read_var_netcdf(data_filename, key, units, **kwargs)

    @classmethod
    def read_netcdf(cls, filename, group='raster', spatial_ref=None, **kwargs):
        """Read a netcdf file

        Parameters
        ----------
        filename : str
            Path to the netcdf file
        group : str, optional. Defaults to 'raster'
            Netcdf group name to read

        """
        return super(Raster, cls).read_netcdf(filename, group, spatial_ref=spatial_ref, **kwargs)

    # def read_raster(self, filename, key, var_meta):
    #     """Read raster file

    #     Adds a 2D raster file directly to the xarray as a single variable

    #     Parameters
    #     ----------
    #     filename : str
    #         Name of file to read
    #     key : str
    #         Name in xarray to assign
    #     var_meta : dict
    #         Dictionary of variable metadata

    #     Returns
    #     -------
    #     out : gspy.Raster
    #         Raster class

    #     """
    #     if isinstance(filename, list):
    #         filename = filename[0]

    #     extension = (filename.split(os.sep)[-1].split('.')[-1]).lower()

    #     if extension == 'tif':
    #         ds = self.read_tif(filename)
    #     elif extension == 'asc':
    #         ds = self.read_asc(filename)

    #     # Reproject if CRS doesn't match Survey
    #     if ds.spatial_ref.attrs['grid_mapping_name'] != self.spatial_ref['grid_mapping_name']:
    #         print('Grid CRS [{}] does not match Survey CRS [{}], reprojecting to Survey CRS'.format(ds.spatial_ref.attrs['grid_mapping_name'], self.spatial_ref['grid_mapping_name']))
    #         if self.spatial_ref['wkid'] != "None":
    #             target_crs = "{}:{}".format(self.spatial_ref['authority'], self.spatial_ref['wkid'])
    #         else:
    #             target_crs = self.spatial_ref['crs_wkt']
    #         print('Reprojecting ...')

    #         # get fill value from file, if present
    #         if '_FillValue' in ds.attrs:
    #             nodata = ds.attrs['_FillValue']
    #         else:
    #             nodata=None

    #         # supersede fill value from file with variable metadata value, if present
    #         if 'null_value' in var_meta[key].keys():
    #             if var_meta[key]['null_value'] != 'not_defined':
    #                 nodata = var_meta[key]['null_value']

    #         # reproject, accounting for nodata value if present
    #         if nodata is None:
    #             ds = ds.rio.reproject(target_crs)
    #         else:
    #             ds = ds.rio.reproject(target_crs, nodata=nodata)
    #     else:
    #         # update x and y attributes based on JSON metadata
    #         ds.x.attrs = var_meta[self.key_mapping['x']]
    #         ds.y.attrs = var_meta[self.key_mapping['y']]

    #     # update attributes based on JSON metadata for variable
    #     ds.attrs = var_meta[key]

    #     # add to xarray
    #     self[key] = ds

    #     # add bounding variables
    #     self._compute_bounds()

    #     return self

    def read_tif(self, filename):
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
        ds = rioxarray.open_rasterio(filename)

        # clean up
        ds = ds.squeeze().drop('band')
        if '_FillValue' in ds.attrs:
            ds.values[ds.values == ds.attrs['_FillValue']] = np.nan
            #ds.attrs['null_value'] = ds.attrs['_FillValue']

        return ds

    # def read_rasters(self, filenames, key, var_meta, **kwargs): # stacking_dimension
    #     """Read multiple raster files and stack into single variable

    #     Combines multiple 2D raster files into a 3D variable along a stacking dimension.
    #     Currently the stacking dimension defaults to "stack" and increments starting at 0. In future
    #     releases this dimension will be customizable and passed through the JSON metadata file.

    #     Parameters
    #     ----------
    #     filenames : list of str
    #         List of raster files to read and stack, in order of stacking dimension
    #     key : str
    #         Name of variable assigned to xarray
    #     var_meta : dict
    #         Dictionary of variable metadata

    #     Returns
    #     -------
    #     out : gspy.Raster
    #         Raster class

    #     """
    #     #self = xr.Dataset()

    #     # read files one at a time, storing values to 3D array
    #     values = None
    #     for i, filename in enumerate(filenames):
    #         ds = self.read_tif(filename)

    #         if values is None:
    #             values = np.empty((len(filenames), *ds.shape))

    #         values[i, :, :] = ds.values

    #     # Assign common x, y dims from last raster to the stack
    #     stacking_dimension = np.arange(len(filenames))
    #     ds = xr.DataArray(values,
    #                         dims={'stack':stacking_dimension, 'y':ds.x.values, 'x':ds.x.values},
    #                         coords={'stack':xr.DataArray(stacking_dimension, dims={'stack':stacking_dimension}),
    #                                 'y':ds.y,
    #                                 'x':ds.x,
    #                                 'spatial_ref':ds.spatial_ref},
    #                         attrs=ds.attrs)

    #     # default stack dimension, will be changed in future versions
    #     ds['stack'].attrs = {'standard_name' : 'stack_dim',
    #                         'long_name' : 'Dimension along which rasters were stacked',
    #                         'units' : 'not_defined',
    #                         'null_value' : 'not_defined'}


    #     if self['spatial_ref'].attrs['grid_mapping_name'] != 'latitude_longitude':
    #         self['x'].attrs['standard_name'] = 'projection_x_coordinate'
    #         self['y'].attrs['standard_name'] = 'projection_y_coordinate'

    #     # Reproject if input CRS does not match Survey
    #     if ds.spatial_ref.attrs['grid_mapping_name'] != self.spatial_ref['grid_mapping_name']:
    #         print('Grid CRS [{}] does not match Survey CRS [{}], reprojecting to Survey CRS'.format(ds.spatial_ref.attrs['grid_mapping_name'], self.spatial_ref['grid_mapping_name']))
    #         if self.spatial_ref['wkid'] != "None":
    #             target_crs = self.spatial_ref['wkid']
    #         else:
    #             target_crs = self.spatial_ref['crs_wkt']
    #         print('Reprojecting ...')

    #         # get fill value from file, if present
    #         if '_FillValue' in ds.attrs:
    #             nodata = ds.attrs['_FillValue']
    #         else:
    #             nodata=None

    #         # supersede fill value from file with variable metadata value, if present
    #         if 'null_value' in var_meta[key].keys():
    #             if var_meta[key]['null_value'] != 'not_defined':
    #                 nodata = var_meta[key]['null_value']

    #         # reproject, accounting for nodata value if present
    #         if nodata is None:
    #             ds = ds.rio.reproject(target_crs)
    #         else:
    #             ds = ds.rio.reproject(target_crs, nodata=nodata)
    #     else:
    #         # update x and y attributes based on JSON metadata
    #         ds.x.attrs = var_meta[self.key_mapping['x']]
    #         ds.y.attrs = var_meta[self.key_mapping['y']]

    #     # update attributes based on JSON metadata
    #     ds.attrs = var_meta[key]

    #     # add to xarray
    #     self[key] = ds

    #     # add bounding variables
    #     self._compute_bounds()

    #     return self

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

    # def _reconcile_crs(self):
    #     grid_crs = self.spatial_ref.attrs
    #     if 'grid_mapping_name' in list(grid_crs.keys()):

    #         #assert grid_crs['grid_mapping_name'] == self.spatial_ref['grid_mapping_name'], ValueError('Grid CRS [{}] does not match Survey [{}]'.format(grid_crs['grid_mapping_name'], self.spatial_ref['grid_mapping_name']))

    #         if grid_crs['grid_mapping_name'] != self.spatial_ref['grid_mapping_name']:
    #             print('Grid CRS [{}] does not match Survey CRS [{}], reprojecting to Survey CRS'.format(grid_crs['grid_mapping_name'], self.spatial_ref['grid_mapping_name']))
    #             self._reproject_xarray()
    #         else:
    #             print('congrats! CRS matches')

    #     else:
    #         print('no grid_mapping_name found in input grid CRS, setting as survey CRS')
    #         # raise NotImplementedError('no grid_mapping_name found in input grid CRS')
    #         self.set_spatial_ref()
    #         self._compute_bounds()

    # def set_spatial_ref(self):

    #     if 'spatial_ref' in self.coords.keys():
    #         self = self.drop('spatial_ref')

    #     s = [self.key_mapping['easting'], self.key_mapping['northing']]

    #     #x = self[self.key_mapping['easting']]
    #     #y = self[self.key_mapping['northing']]
    #     if '_CoordinateTransformType' in self.spatial_ref:
    #         self.x.attrs['standard_name'] = 'projection_x_coordinate'
    #         self.x.attrs['_CoordinateAxisType'] = 'GeoX'
    #         self.y.attrs['standard_name'] = 'projection_y_coordinate'
    #         self.y.attrs['_CoordinateAxisType'] = 'GeoY'

    #     # if units are abbreviated need to spell it out otherwise isn't recognized by Arc
    #     if self.x.attrs['units'] == 'm':
    #         self.x.attrs['units'] = 'meters'
    #     if self.y.attrs['units'] == 'm':
    #         self.y.attrs['units'] = 'meters'

    #     xy = xr.DataArray(0.0, attrs=self.spatial_ref)

    #     coords = {'y': self.y, 'x': self.x, 'spatial_ref': xy}

    #     for var in self.data_vars:
    #         da = self[var]
    #         if not var in s:
    #             da = da.assign_coords(coords)
    #             #da.attrs['grid_mapping'] = self.spatial_ref['grid_mapping_name']
    #         self[var] = da

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
                self = self.drop_vars(check_keys[i])

        if self.spatial_ref['wkid'] != "None":
            target_crs = "{}:{}".format(self.spatial_ref['authority'], self.spatial_ref['wkid'])
        else:
            target_crs = self.spatial_ref['crs_wkt']

        self = self.rio.reproject(target_crs)
        self._compute_bounds()

        return self

    def write_netcdf(self, filename, group='raster'):
        """Write to netcdf file

        Parameters
        ----------
        filename : str
            Path to the file
        group : str
            Name of group within netcdf file

        """
        super().write_netcdf(filename, group)

    def write_metadata_template(self):
        """Write JSON metadata template

        Outputs a template JSON metadata file needed for adding Raster data. All required
        dictionaries are printed (dataset_attrs, key_mapping, raster_files, variable_metadata).
        Additional dictionaries can be optionally added to document more information or
        ancillary metadata relevant to the specific Raster data.

        Raises
        ------
        Exception
             Tells user to specify supplemental information when instantiating Raster data

        """

        print("\nGenerating an empty supplemental information file template for the Raster data.\n")

        out = {}
        out["dataset_attrs"] = {
            "content": "<summary statement of what the dataset contains>",
            "comment": "<additional details or ancillary information>"
            }

        out["key_mapping"] =   {
            "x" : "lat",
            "y" : "lon",
            "z" : "elev"
            }

        out["raster_files"] = {
            "variable_1" : ["file_name"],
            "variable_2" : ["file_name"],
            "variable_3" : ["file_name_1","file_name_2","file_name_3"]
            }

        out["variable_metadata"] = {
            "variable_1": {
            "standard_name": "",
            "long_name": "",
            "units": "",
            "null_value": ""
            },
            "variable_2": {
            "standard_name": "",
            "long_name": "",
            "units": "",
            "null_value": ""
            },
            "variable_3": {
            "standard_name": "",
            "long_name": "",
            "units": "",
            "null_value": ""
            },
            "lat": {
            "standard_name": "",
            "long_name": "",
            "units": "",
            "null_value": ""
            },
            "lon": {
            "standard_name": "",
            "long_name": "",
            "units": "",
            "null_value": ""
            },
            "elev": {
            "standard_name": "",
            "long_name": "",
            "units": "",
            "null_value": ""
            }
            }

        with open("raster_supplemental_information.json", "w") as f:
            json.dump(out, f, indent=4)

    def to_tif(self):
        """ Export GeoTIFF files from xarray

        2D variables are exported directly to GeoTIFF files, one for each variable, following
        the naming convention "{variable}.tif"

        3D variables are sliced along the stacking direction and exported to incremented GeoTIFF
        files following the naming convention "{variable}_{i}.tif". In the current version the
        stacking dimension is defaulted to "stack", future versions will allow for more customized
        dimension names.
        """

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
                        ds.sel(stack=s).rio.to_raster("{}_{}.tif".format(var, s))
                else:
                    ds.rio.to_raster("{}.tif".format(var))
