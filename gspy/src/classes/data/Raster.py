import os
from pathlib import Path
import json
from copy import deepcopy

import numpy as np
import xarray as xr
import rioxarray

from .Key_mapping import key_mapping
from .Variable_Metadata import variable_metadata
from .Data import Data

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
    def __init__(self, metadata_file, spatial_ref, **kwargs):
        self._type = None
        self._key_mapping = None

        if metadata_file is None and spatial_ref is None:
            return

        self.read(metadata_file, spatial_ref, **kwargs)

    @property
    def bounds(self):
        return [self.xarray[ax].attrs['bounds'] for ax in self.xarray.dims]

    @property
    def is_tif(self):
        return self.type == 'tif'

    @Data.xarray.setter
    def xarray(self, value):
        assert isinstance(value, xr.Dataset), TypeError("xarray must have type xarray.Dataset")
        self._xarray = value

    def read(self, metadata_file, spatial_ref=None, netcdf_file=None, **kwargs):
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

        # attach or create a spatial ref
        self.spatial_ref = kwargs if spatial_ref is None else spatial_ref

        if netcdf_file is not None:
            return Raster.read_netcdf(netcdf_file, spatial_ref=spatial_ref, **kwargs)
        else:
            # read the metadata file
            dic = self.read_metadata(metadata_file)

            path = Path(metadata_file).parent.absolute()

            var_meta = variable_metadata(**dic.pop('variable_metadata'))
            self.xarray = xr.Dataset()

            rfiles = dic.pop('raster_files')
            for variable, item in rfiles.items():
                if len(item) == 1:
                    reader = self.read_raster
                else:
                    reader = self.read_rasters

                reader([os.path.join(path, x) for x in item], variable, var_meta)

            # add global attrs to tabular
            self._add_general_metadata_to_xarray(dic)

        # Check for conforming spatial refs???

        # # add global attrs to linedata
        # self._add_general_metadata_to_xarray({x: dic[x] for x in dic if x not in ['units_and_nulls','variable_files']})

    def read_metadata(self, filename):
        """Read metadata file

        Loads the metadata file and adds key_mapping values to property. If required dictionaries
        'raster_files' and/or 'variable_metadata' are missing, then a metadata template file is written
        and an error is triggered.

        Parameters
        ----------
        filename : str
            Json file

        Returns
        -------
        dic : dict
            Dictionary of JSON metadata

        """
        if filename == 'None':
            return

        if filename is None:
            self.write_metadata_template()
            raise Exception("Please re-run and specify supplemental information when instantiating Raster")

        # reading the data from the file
        with open(filename) as f:
            s = f.read()

        dic = json.loads(s)

        #assert 'key_mapping' in dic, ValueError('Need to define key_mapping for required keys {} in supplemental'.format(key_mapping.required_keys))
        if "key_mapping" in dic.keys():
            self.key_mapping = key_mapping(dic.get('key_mapping'))

        if not 'raster_files' in dic or not 'variable_metadata' in dic:
            self.write_metadata_template()
            raise Exception("Please re-run and specify supplemental information when instantiating Raster")

        return dic

    def _compute_bounds(self):
        """ Add bounding variables to xarray for gridded dimension coordinates
        """
        for axis in self.xarray.dims:
            if axis not in ['index','nv']:
                bnds = np.zeros((self.xarray[axis].size,2))
                centre = np.median(np.diff(self.xarray[axis].values))*0.5
                bnds[:, 0] = self.xarray[axis].values - centre
                bnds[:, 1] = self.xarray[axis].values + centre
                bkey = axis+'_bnds'
                attrs = self.xarray[axis].attrs
                attrs['standard_name'] = self.xarray[axis].attrs['standard_name']+'_bounds'
                attrs['long_name'] = self.xarray[axis].attrs['long_name']+' cell boundaries'
                self.xarray[bkey] = xr.DataArray(bnds, dims=[axis, 'nv'],
                                        coords={axis: self.xarray[axis], 'nv': np.array([0, 1])},
                                        attrs=attrs
                                        )
                self.xarray[axis].attrs['bounds'] = bkey

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

    def read_raster(self, filename, key, var_meta):
        """Read raster file

        Adds a 2D raster file directly to the xarray as a single variable

        Parameters
        ----------
        filename : str
            Name of file to read
        key : str
            Name in xarray to assign
        var_meta : dict
            Dictionary of variable metadata

        Returns
        -------
        out : gspy.Raster
            Raster class

        """
        if isinstance(filename, list):
            filename = filename[0]

        extension = (filename.split(os.sep)[-1].split('.')[-1]).lower()

        if extension == 'tif':
            ds = self.read_tif(filename)
        elif extension == 'asc':
            ds = self.read_asc(filename)

        # Reproject if CRS doesn't match Survey
        if ds.spatial_ref.attrs['grid_mapping_name'] != self.spatial_ref['grid_mapping_name']:
            print('Grid CRS [{}] does not match Survey CRS [{}], reprojecting to Survey CRS'.format(ds.spatial_ref.attrs['grid_mapping_name'], self.spatial_ref['grid_mapping_name']))
            if self.spatial_ref['wkid'] != "None":
                target_crs = "{}:{}".format(self.spatial_ref['authority'], self.spatial_ref['wkid'])
            else:
                target_crs = self.spatial_ref['crs_wkt']
            print('Reprojecting ...')

            # get fill value from file, if present
            if '_FillValue' in ds.attrs:
                nodata = ds.attrs['_FillValue']
            else:
                nodata=None

            # supersede fill value from file with variable metadata value, if present
            if 'null_value' in var_meta[key].keys():
                if var_meta[key]['null_value'] != 'not_defined':
                    nodata = var_meta[key]['null_value']

            # reproject, accounting for nodata value if present
            if nodata is None:
                ds = ds.rio.reproject(target_crs)
            else:
                ds = ds.rio.reproject(target_crs, nodata=nodata)
        else:
            # update x and y attributes based on JSON metadata
            ds.x.attrs = var_meta[self.key_mapping['x']]
            ds.y.attrs = var_meta[self.key_mapping['y']]

        # update attributes based on JSON metadata for variable
        ds.attrs = var_meta[key]

        # add to xarray
        self.xarray[key] = ds

        # add bounding variables
        self._compute_bounds()

        return self

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

    def read_rasters(self, filenames, key, var_meta): # stacking_dimension
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
        #self.xarray = xr.Dataset()

        # read files one at a time, storing values to 3D array
        values = None
        for i, filename in enumerate(filenames):
            ds = self.read_tif(filename)

            if values is None:
                values = np.empty((len(filenames), *ds.shape))

            values[i, :, :] = ds.values

        # Assign common x, y dims from last raster to the stack
        stacking_dimension = np.arange(len(filenames))
        ds = xr.DataArray(values,
                            dims={'stack':stacking_dimension, 'y':ds.x.values, 'x':ds.x.values},
                            coords={'stack':xr.DataArray(stacking_dimension, dims={'stack':stacking_dimension}),
                                    'y':ds.y,
                                    'x':ds.x,
                                    'spatial_ref':ds.spatial_ref},
                            attrs=ds.attrs)

        # default stack dimension, will be changed in future versions
        ds['stack'].attrs = {'standard_name' : 'stack_dim',
                            'long_name' : 'Dimension along which rasters were stacked',
                            'units' : 'not_defined',
                            'null_value' : 'not_defined'}

        # Reproject if input CRS does not match Survey
        if ds.spatial_ref.attrs['grid_mapping_name'] != self.spatial_ref['grid_mapping_name']:
            print('Grid CRS [{}] does not match Survey CRS [{}], reprojecting to Survey CRS'.format(ds.spatial_ref.attrs['grid_mapping_name'], self.spatial_ref['grid_mapping_name']))
            if self.spatial_ref['wkid'] != "None":
                target_crs = self.spatial_ref['wkid']
            else:
                target_crs = self.spatial_ref['crs_wkt']
            print('Reprojecting ...')

            # get fill value from file, if present
            if '_FillValue' in ds.attrs:
                nodata = ds.attrs['_FillValue']
            else:
                nodata=None

            # supersede fill value from file with variable metadata value, if present
            if 'null_value' in var_meta[key].keys():
                if var_meta[key]['null_value'] != 'not_defined':
                    nodata = var_meta[key]['null_value']

            # reproject, accounting for nodata value if present
            if nodata is None:
                ds = ds.rio.reproject(target_crs)
            else:
                ds = ds.rio.reproject(target_crs, nodata=nodata)
        else:
            # update x and y attributes based on JSON metadata
            ds.x.attrs = var_meta[self.key_mapping['x']]
            ds.y.attrs = var_meta[self.key_mapping['y']]

        # update attributes based on JSON metadata
        ds.attrs = var_meta[key]

        # add to xarray
        self.xarray[key] = ds

        # add bounding variables
        self._compute_bounds()

        return self

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
    #     grid_crs = self.xarray.spatial_ref.attrs
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

    #     if 'spatial_ref' in self.xarray.coords.keys():
    #         self.xarray = self.xarray.drop('spatial_ref')

    #     s = [self.key_mapping['easting'], self.key_mapping['northing']]

    #     #x = self.xarray[self.key_mapping['easting']]
    #     #y = self.xarray[self.key_mapping['northing']]
    #     if '_CoordinateTransformType' in self.spatial_ref:
    #         self.xarray.x.attrs['standard_name'] = 'projection_x_coordinate'
    #         self.xarray.x.attrs['_CoordinateAxisType'] = 'GeoX'
    #         self.xarray.y.attrs['standard_name'] = 'projection_y_coordinate'
    #         self.xarray.y.attrs['_CoordinateAxisType'] = 'GeoY'

    #     # if units are abbreviated need to spell it out otherwise isn't recognized by Arc
    #     if self.xarray.x.attrs['units'] == 'm':
    #         self.xarray.x.attrs['units'] = 'meters'
    #     if self.xarray.y.attrs['units'] == 'm':
    #         self.xarray.y.attrs['units'] = 'meters'

    #     xy = xr.DataArray(0.0, attrs=self.spatial_ref)

    #     coords = {'y': self.xarray.y, 'x': self.xarray.x, 'spatial_ref': xy}

    #     for var in self.xarray.data_vars:
    #         da = self.xarray[var]
    #         if not var in s:
    #             da = da.assign_coords(coords)
    #             #da.attrs['grid_mapping'] = self.spatial_ref['grid_mapping_name']
    #         self.xarray[var] = da

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

        bnds_keys = list(self.xarray.data_vars.keys())
        check_keys = ['x_bnds', 'y_bnds', 'z_bnds']
        bnds_present = [k in bnds_keys for k in check_keys]

        for i in range(3):
            if bnds_present[i]:
                self.xarray = self.xarray.drop_vars(check_keys[i])

        if self.spatial_ref['wkid'] != "None":
            target_crs = "{}:{}".format(self.spatial_ref['authority'], self.spatial_ref['wkid'])
        else:
            target_crs = self.spatial_ref['crs_wkt']

        self.xarray = self.xarray.rio.reproject(target_crs)
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

        for var in self.xarray.data_vars:
            # skip bnds variables
            if 'bnds' not in var:
                ds = deepcopy(self.xarray[var])

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
