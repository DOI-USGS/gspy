import os
import json
from copy import deepcopy

import xarray as xr
from netCDF4 import Dataset
import h5py

from ..data.Tabular import Tabular
from ..data.Raster import Raster
from .Spatial_ref import Spatial_ref
from ...utilities import flatten

class Survey(object):
    """Class defining a survey or dataset collection

    The Survey group contains general metadata about the survey or data colleciton as a whole.
    Information about where the data was collected, acquisition start and end dates, who collected the data,
    any clients or contractors involved, system specifications, equipment details, and so on are documented
    within the Survey as data variables and attributes.

    Users are allowed to add as much or little information to data variables as they choose. However, following the CF
    convention, a set of global dataset attributes are required:
    * title
    * institution
    * source
    * history
    * references

    A “coordinate_information” variable is also required within Survey and should contain all relevant information about the
    coordinate reference system. This is used to instantiate a gspy.Spatial_ref class.

    Survey(metadata_file)

    Parameters
    ----------
    metadata_file : str
        Json file containing survey metadata.

    Returns
    -------
    out : gspy.Survey
        Survey class.

    See Also
    --------
    gspy.Spatial_ref : For co-ordinate information requirements.

    """

    def __init__(self, metadata_file=None, netcdf_file=None):

        self._tabular = []
        self._raster = []
        self._attrs = {}
        self._spatial_ref = {}

        if metadata_file is not None:
            # read survey metadata file
            self.read_metadata(metadata_file)

            # make xarray
            self._make_survey_xarray()

        #elif netcdf_file is not None:
        #    # read netcdf file (assumes GS format)
        #    self.read_netcdf(netcdf_file)

    @property
    def attrs(self):
        return self._attrs

    @attrs.setter
    def attrs(self, value):
        assert isinstance(value, dict), TypeError('attrs must have type dict')
        self._attrs = value

    @property
    def xarray(self):
        return self._xarray

    @xarray.setter
    def xarray(self, value):
        assert isinstance(value, xr.Dataset), TypeError("xarray must have type xarray.Dataset")
        self._xarray = value

    @property
    def tabular(self):
        if len(self._tabular) == 1:
            return self._tabular[0]
        return self._tabular

    @property
    def raster(self):
        if len(self._raster) == 1:
            return self._raster[0]
        return self._raster

    @property
    def spatial_ref(self):
        return self._spatial_ref

    @spatial_ref.setter
    def spatial_ref(self, value):
        if isinstance(value, Spatial_ref):
            self._spatial_ref = value
        else:
            self._spatial_ref = Spatial_ref(**value)

    @property
    def json_metadata(self):
        return self._json_metadata

    @json_metadata.setter
    def json_metadata(self, value):
        assert isinstance(value, dict), TypeError('json_metadata must have type dict')
        self._json_metadata = value

    def add_raster(self, *args, **kwargs):
        """Add Raster data to the survey

        See Also
        --------
        gspy.Raster : For instantiation/reading requirements

        """
        self._raster.append(Raster(*args, spatial_ref=self.spatial_ref, **kwargs))

    def add_tabular(self, *args, **kwargs):
        """Add Tabular data to the survey

        See Also
        --------
        gspy.Tabular : For instantiation/reading requirements

        """
        self._tabular.append(Tabular.read(*args, spatial_ref=self.spatial_ref, **kwargs))

    def read_metadata(self, filename=None):
        """Read metadata for the survey

        Parameters
        ----------
        filename : str
            Json file.

        Raises
        ------
        Exception : When metadata file is not provided.

        """

        if filename is None:
            self.write_metadata_template()
            raise Exception("Please re-run and specify supplemental information when instantiating Survey()")

        # reading the data from the file
        with open(filename) as f:
            s = f.read()

        dic = json.loads(s)

        self.json_metadata = dic

        self.spatial_ref = self.json_metadata['coordinate_information']

    def _add_general_metadata_to_xarray(self, kwargs):
        """ Attaches "dataset_attrs" values as general attributes in xarray DataSets

        Parameters
        ----------
        kwargs : dict
            metadata dictionary containing "dataset_attrs"
        """
        self.xarray.attrs.update(kwargs['dataset_attrs'])

    def _make_survey_xarray(self):
        """ Create Survey xarray

        Generate an xarray DataSet, attach Survey metadata as variables,
        and assign global attributes for the survey
        """
        self.xarray = xr.Dataset()

        dic = deepcopy(self.json_metadata)
        ds_attrs = {}
        ds_attrs["dataset_attrs"] = dic.pop("dataset_attrs", None)

        self._add_general_metadata_to_xarray(ds_attrs)

        for key in dic:
            tmpdict2 = {k: v for k, v in dic[key].items() if v}
            tmpdict2 = flatten(tmpdict2, '', {})

            for k,v in tmpdict2.items():
                if isinstance(v,list):

                    if isinstance(v[0],list):
                        tmpdict2[k] = str(v)
            #tmpdict[key] = xr.DataArray(attrs=tmpdict2)
            self.xarray[key] = xr.DataArray(attrs=tmpdict2)

        #assert not ds_attrs is None, Exception("Supplemental information must contain 'dataset_attrs' entry")

        #ds = xr.Dataset(tmpdict, attrs=ds_attrs)

    def write_metadata_template(self):
        """Creates a metadata template for a Survey

        If a Survey metadata file is not found or passed, an empty template file is generated and
        an Exception is raised.

        Raises
        ------
        Exception
            "Please re-run and specify supplemental information when instantiating Survey()"
        """

        print("\nGenerating an empty supplemental information file for the survey.\n")

        out = {}
        out["dataset_attrs"] = {
            "title": "",
            "institution": "",
            "source":  "",
            "history": "",
            "references": "",
            "comment": "",
            "conventions": "CF-1.8"
            }
        out["survey_information"] =   {
            "contractor_project_number" : "",
            "contractor" : "",
            "client" : "",
            "survey_type" : "",
            "survey_area_name" : "",
            "state" : "",
            "country" : "",
            "acquisition_start" : "yyyymmdd",
            "acquisition_end" : "yyyymmdd",
            "dataset_created" : "yyyymmdd"
            }

        out["coordinate_information"] = {
            "datum" : "",
            "projection" : "",
            "utm_zone" : "",
            "epsg": ""
            }

        out["flightline_information"] = {
            "traverse_line_spacing" : "",
            "traverse_line_direction" : "",
            "tie_line_spacing" : "",
            "tie_line_direction" : "",
            "nominal_line_spacing" : "",
            "nominal_terrain_clearance" : "",
            "final_line_kilometers" : "",
            "traverse_line_numbers" : "",
            "tie_line_numbers": ""
            }

        out["survey_equipment"] = {
            "aircraft" : "",
            "magnetometer" : "",
            "spectrometer_system" : "",
            "radar_altimeter_system" : "",
            "radar_altimeter_sample_rat" : "",
            "laser_altimeter_system" : "",
            "navigation_system" : "",
            "acquisition_system" : ""
            }

        out["system_information"] = {
            "instrument_type" : ""
            }

        with open("survey_supplemental_information.json", "w") as f:
            json.dump(out, f, indent=4)

    @classmethod
    def read_netcdf(cls, filename, **kwargs):
        """Read a survey from a netcdf file

        Parameters
        ----------
        filename : str
            Netcdf file name

        Returns
        -------
        out : gspy.Survey

        """

        self = cls()

        self.xarray = xr.load_dataset(filename, group='survey')
        si = self.xarray.to_dict()
        self.json_metadata = {key:value['attrs'] for key, value in si['data_vars'].items()}
        self.spatial_ref = self.json_metadata['coordinate_information']

        with h5py.File(filename, 'r') as f:
            groups = list(f['survey'].keys())

        if 'tabular' in groups:
            rootgrp = Dataset(filename)
            for i in rootgrp.groups['survey'].groups['tabular'].groups:
                self._tabular.append(Tabular.read(type='netcdf', data_filename=filename, metadata_file=None, spatial_ref=self.spatial_ref, group='survey/tabular/{}'.format(int(i)), **kwargs))
            rootgrp.close()

        if 'raster' in groups:
            rootgrp = Dataset(filename)
            for i in rootgrp.groups['survey'].groups['raster'].groups:
                self._raster.append(Raster.read_netcdf(filename=filename, group='survey/raster/{}'.format(int(i))))
            rootgrp.close()

        return self

    def reproject():
        """ Reprojects Survey

        The Survey and all dependent datasets are reprojected into a new CRS

        Raises
        ------
        NotImplementedError
            Function planned but not currently implemented
        """
        raise NotImplementedError()


    def write_netcdf(self, filename):
        """Write a survey to a netcdf file

        Parameters
        ----------
        filename : str
            Netcdf file name

        """

        # Survey
        self.xarray.to_netcdf(filename, mode='w', group='survey', format='netcdf4', engine='netcdf4')

        # Tabular
        for i, m in enumerate(self._tabular):
            m.write_netcdf(filename, group="survey/tabular/{}".format(i))

        # Raster
        for i, m in enumerate(self._raster):
            m.write_netcdf(filename, group='survey/raster/{}'.format(i))

    def write_ncml(self, filename):
        """ Write a NcML (NetCDF XML) metadata file

        Exports a NcML

        Parameters
        ----------
        filename : str
            Name of the NetCDF file to generate NcML for
        """

        infile = '{}.ncml'.format('.'.join(filename.split('.')[:-1]))
        f = open(infile, 'w')

        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<netcdf xmlns="http://www.unidata.ucar.edu/namespaces/netcdf/ncml-2.2" location="{}">\n\n'.format(filename.split(os.sep)[-1]))
        f.write('<group name="/survey">\n\n')

        ### Survey Dimensions:
        for dim in self.xarray.dims:
            f.write('  <dimension name="%s" length="%s"/>\n' % (dim, self.xarray.dims[dim]))
        if len(self.xarray.dims) > 0:
            f.write('\n')

        ### Survey Attributes:
        for attr in self.xarray.attrs:
            att_val = self.xarray.attrs[attr]
            if '"' in str(att_val):
                att_val = att_val.replace('"',"'")
            f.write('  <attribute name="%s" value="%s"/>\n' % (attr, att_val))
        f.write('\n')

        ### Survey Variables:
        for var in self.xarray.variables:
            tmpvar = self.xarray.variables[var]
            dtype = str(tmpvar.dtype).title()[:-2]
            if var == 'crs' or dtype == 'object':
                f.write('  <variable name="%s" shape="%s" type="String">\n' % (var, " ".join(tmpvar.dims)))
            else:
                f.write('  <variable name="%s" shape="%s" type="%s">\n' % (var, " ".join(tmpvar.dims), dtype))
            for attr in tmpvar.attrs:
                att_val = tmpvar.attrs[attr]
                if '"' in str(att_val):
                    att_val = att_val.replace('"',"'")
                f.write('    <attribute name="%s" type="String" value="%s"/>\n' % (attr, att_val))
            f.write('  </variable>\n\n')
        f.close()

        # Tabular
        for i, m in enumerate(self._tabular):
            f = open(infile, 'a')
            if i == 0:
                f.write('  <group name="/tabular">\n\n')
            f.write('    <group name="/{}">\n\n'.format(i))
            f.close()
            m.write_ncml(filename, group="tabular", index=i)
            f = open(infile, 'a')
            f.write('    </group>\n\n')
            if i == len(self._tabular)-1:
                f.write('  </group>\n\n')
            f.close()

        # Raster
        for i, m in enumerate(self._raster):
            f = open(infile, 'a')
            if i == 0:
                f.write('  <group name="/raster">\n\n')
            f.write('    <group name="/{}">\n\n'.format(i))
            f.close()
            m.write_ncml(filename, group="raster", index=i)
            f = open(infile, 'a')
            f.write('    </group>\n\n')
            if i == len(self._raster)-1:
                f.write('  </group>\n\n')
            f.close()


        f = open(infile, 'a')
        f.write('</group>\n\n')
        f.write('</netcdf>')
        f.close()
