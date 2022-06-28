import warnings

import pyproj
import xarray as xr

class Spatial_ref(dict):
    """Class to handle spatial reference formats

    Allows instantiation by any of the following; wkid, EPSG, well known text or proj4 strings.

    Spatial_ref(**kwargs)

    Other Parameters
    ----------------
    wkid : str

    EPSG : int

    crs_wkt : str

    proj_string : str


    Returns
    -------
    out : gspy.Spatial_ref
        Spatial reference handler.
    """

    def __init__(self, **kwargs):

        if ("wkid" in kwargs) and (kwargs.get("wkid", "None") != "None" and (kwargs.get("wkid", "None")) != ""):
            val = kwargs["wkid"]
            if 'EPSG' in val:
                val = val.split(':')[1]
                auth = 'EPSG'
            elif ("authority" in kwargs) and (kwargs.get("authority", "None") != "None" and (kwargs.get("authority", "None")) != ""):
                auth = kwargs["authority"]
            else:
                print('WARNING! No authority passed for WKID, DEFAULTING to EPSG')

            if auth == 'EPSG':
                crs = pyproj.CRS.from_epsg(val)

        elif ("crs_wkt" in kwargs.keys()) and (kwargs.get("crs_wkt", "None") != "None"):
            crs = pyproj.CRS.from_wkt(kwargs["crs_wkt"].replace("'",'"'))

        elif("proj_string" in kwargs.keys()) and (kwargs.get("proj_string", "None") != "None"):
            crs = pyproj.CRS.from_proj4(kwargs["proj_string"])
        else:
            print('WARNING! No coordinate information imported, DEFAULTING to EPSG:4326')
            crs = pyproj.CRS.from_epsg('4326')

        self['wkid'] = ':'.join(crs.to_authority()) if crs.to_authority() else "None"
        self['crs_wkt'] = crs.to_wkt()
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            self['proj_string'] = crs.to_proj4()
        self['geographic_crs_name'] = crs.geodetic_crs.name

        gname = crs.name.replace(' ','_').replace('-','_').replace('/','_').replace('___','_').replace('__','_').lower()
        if 'conic' in gname.split('_'):
            gname = gname.replace('conic','conical')
        self['grid_mapping_name'] = gname

        if crs.is_projected:
            self['_CoordinateTransformType'] = 'Projection'
            self['_CoordinateAxisTypes'] = 'GeoX GeoY'

        if not crs.ellipsoid is None:
            self['reference_ellipsoid_name'] = crs.ellipsoid.name
            self['inverse_flattening'] = crs.ellipsoid.inverse_flattening
            self['semi_major_axis'] = crs.ellipsoid.semi_major_metre
            self['semi_minor_axis'] = crs.ellipsoid.semi_minor_metre

        if not crs.prime_meridian is None:
            self['prime_meridian_name'] = crs.prime_meridian.name
            self['longitude_of_prime_meridian'] = crs.prime_meridian.longitude

        if not crs.coordinate_operation is None:
            for param in crs.coordinate_operation.params:
                self[param.name.replace(' ','_').lower()] = param.value

        # self._spatial_ref = self
        # for key,item in self.items():
        #     self.attrs['coordinate_information'][key] = item


    def reconcile_with_xarray(self, xarray, key_mapping):
        """Reconciles a spatial reference with an existing xarray DataArray

        Checks co-ordinate projections and renames attribute names.

        Parameters
        ----------
        xarray : xarray.DataArray
            Existing xarray object
        key_mapping : dict
            Mapping of gspy standard co-ordinate names to IRL column names (e.g. csv).

        """

        s = [key_mapping['x'], key_mapping['y']]

        x = xarray[key_mapping['x']]
        y = xarray[key_mapping['y']]
        if '_CoordinateTransformType' in self:
            x.attrs['standard_name'] = 'projection_x_coordinate'
            x.attrs['_CoordinateAxisType'] = 'GeoX'
            y.attrs['standard_name'] = 'projection_y_coordinate'
            y.attrs['_CoordinateAxisType'] = 'GeoY'

        # if units are abbreviated need to spell it out otherwise isn't recognized by Arc
        if x.attrs['units'] == 'm':
            x.attrs['units'] = 'meters'
        if y.attrs['units'] == 'm':
            y.attrs['units'] = 'meters'

        xy = xr.DataArray(0.0, attrs=self)

        coords = {'y': y, 'x': x, 'spatial_ref': xy}

        for var in xarray.data_vars:
            da = xarray[var]
            if not var in s:
                da = da.assign_coords(coords)
                da.attrs['grid_mapping'] = self['grid_mapping_name']
            xarray[var] = da
