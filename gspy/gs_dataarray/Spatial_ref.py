import warnings

from ..utilities.CRS import CRS
from xarray import DataArray, register_dataarray_accessor
from ..metadata.Metadata import Metadata

@register_dataarray_accessor("spatial_ref")
class Spatial_ref:
    """Class to handle spatial reference formats

    Allows instantiation by any of the following; wkid, EPSG, crs_wkt or proj4 strings.
    Handles non standard and custom spatial references that may not be defined by a single EPSG.
    Regardless of input option, the spatial ref contains a CF convention set of metadata.

    Spatial_ref(**kwargs)

    Parameters
    ----------
    wkid : str, optional
        wkid string
    EPSG : int, optional
        Integer identifier for CRS
    crs_wkt : str, optional
        Well known text
    proj_string : str, optional
        Proj 4 string

    Returns
    -------
    gspy.Spatial_ref
        Spatial reference
    """
    def __init__(self, xarray_obj):
        self._obj = xarray_obj

    @classmethod
    def from_dict(cls, kwargs):
        if ("wkid" in kwargs) and (kwargs.get("wkid", "None") != "None" and (kwargs.get("wkid", "None")) != ""):
            val = kwargs["wkid"]
            if 'EPSG' in str(val):
                val = val.split(':')[1]
                auth = 'EPSG'
            elif ("authority" in kwargs) and (kwargs.get("authority", "None") != "None" and (kwargs.get("authority", "None")) != ""):
                auth = kwargs["authority"]
            else:
                print('WARNING! No authority passed for WKID, DEFAULTING to EPSG')

            if auth == 'EPSG':
                crs = CRS.from_epsg(val)

        elif ("crs_wkt" in kwargs.keys()) and (kwargs.get("crs_wkt", "None") != "None"):
            crs = CRS.from_wkt(kwargs["crs_wkt"].replace("'",'"'))

        elif("proj_string" in kwargs.keys()) and (kwargs.get("proj_string", "None") != "None"):
            crs = CRS.from_proj4(kwargs["proj_string"])

        elif ("prj_file" in kwargs.keys()) and (kwargs.get("prj_file", "None") != "None"):
            prj_text = open(kwargs['prj_file'], 'r').read()
            crs = CRS.from_wkt(prj_text)
        else:
            print('WARNING! No coordinate information imported, DEFAULTING to EPSG:4326')
            crs = CRS.from_epsg('4326')

        out = DataArray(0.0)

        out.attrs = crs.to_cf()

        if crs.to_authority():
            out.attrs['authority'] = crs.to_authority()[0]
            out.attrs['wkid'] = crs.to_authority()[1]

        return out

    @staticmethod
    def metadata_template(**kwargs):
        return Metadata.merge({"wkid":"??",
                               "crs_wkt":"??",
                               "proj_string":"??",
                               "prj_file":"??"}, kwargs)

        # self['crs_wkt'] = crs.to_wkt()
        # with warnings.catch_warnings():
        #     warnings.simplefilter('ignore')
        #     self['proj_string'] = crs.to_proj4()
        # self['geographic_crs_name'] = crs.geodetic_crs.name

        # gname = crs.name.replace(' ','_').replace('-','_').replace('/','_').replace('___','_').replace('__','_').lower()
        # if 'conic' in gname.split('_'):
        #     gname = gname.replace('conic','conical')
        # self['grid_mapping_name'] = gname

        # if crs.is_projected:
        #     self['_CoordinateTransformType'] = 'Projection'
        #     self['_CoordinateAxisTypes'] = 'GeoX GeoY'

        # if not crs.ellipsoid is None:
        #     self['reference_ellipsoid_name'] = crs.ellipsoid.name
        #     self['inverse_flattening'] = crs.ellipsoid.inverse_flattening
        #     self['semi_major_axis'] = crs.ellipsoid.semi_major_metre
        #     self['semi_minor_axis'] = crs.ellipsoid.semi_minor_metre

        # if not crs.prime_meridian is None:
        #     self['prime_meridian_name'] = crs.prime_meridian.name
        #     self['longitude_of_prime_meridian'] = crs.prime_meridian.longitude

        # if not crs.coordinate_operation is None:
        #     for param in crs.coordinate_operation.params:
        #         self[param.name.replace(' ','_').lower()] = param.value

        #self._spatial_ref = self
        #for key,item in self.items():
        #    self.attrs['spatial_ref'][key] = item