import os
import json
from copy import deepcopy
from pprint import pprint
import xarray as xr
from netCDF4 import Dataset as ncdf4_Dataset
import h5py

from ..data.xarray_gs.Dataset import Dataset
from ..data.Tabular import Tabular
from ..data.Raster import Raster
from ...utilities import flatten

import xarray as xr

class Survey(object):
    """Class defining a survey or dataset

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

    A “spatial_ref” variable is also required within Survey and should contain all relevant information about the
    coordinate reference system.

    Once instantiated, tabular and raster classes can be added to the survey. Each tabular or raster dataset is a separate xarray.Dataset.

    ``Survey(metadata)``

    Parameters
    ----------
    metadata : str or dict
        * If str, a json metadata file
        * If dict, dictionary of survey metadata.

    Returns
    -------
    gspy.Survey

    See Also
    --------
    .Spatial_ref : For information on creating a spatial ref

    """

    def __init__(self, metadata=None):
        self._tabular = []
        self._raster = []

        if metadata is not None:
            if isinstance(metadata, str):
                # read survey metadata file
                metadata = self.read_metadata(metadata)

            # make xarray
            self.xarray = metadata

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
        return self.xarray.spatial_ref

    @spatial_ref.setter
    def spatial_ref(self, kwargs):
        self.xarray.spatial_ref = kwargs

    @property
    def xarray(self):
        return self._xarray

    @xarray.setter
    def xarray(self, kwargs):
        """Attach an xarray.Dataset containing GS metadata or create one from a dict

        Parameters
        ----------
        kwargs : xarray.Dataset or dict
            * If xarray.Dataset checks for required metadata and spatial_ref
            * If dict, checks for required metadata and a spatial_ref definition

        See Also
        --------
        ...Survey.Spatial_ref : for more details of creating a Spatial_ref

        """

        required = ("title", "institution", "source", "history", "references")
        if isinstance(kwargs, xr.Dataset):
            assert all([x in kwargs.attrs for x in required]), ValueError("Dataset.attrs must contain at least {}".format(required))
            self._xarray = kwargs
        else:

            assert isinstance(kwargs, dict), TypeError('json_metadata must have type dict')
            assert "dataset_attrs" in kwargs, ValueError("Survey metadata must contain entry 'dataset_attrs")
            assert "spatial_ref" in kwargs, ValueError("Survey metadata must contain entry 'spatial_ref")
            assert all([x in kwargs["dataset_attrs"] for x in required]), ValueError("dataset_attrs must contain at least {}".format(required))

            ds = Dataset(xr.Dataset(attrs = {}))

            ds.update_attrs(**kwargs["dataset_attrs"])

            for key in kwargs:
                if key not in ('spatial_ref', 'dataset_attrs'):
                    tmpdict2 = {k: v for k, v in kwargs[key].items() if v}
                    tmpdict2 = flatten(tmpdict2, '', {})

                    for k,v in tmpdict2.items():
                        if isinstance(v,list):

                            if isinstance(v[0],list):
                                tmpdict2[k] = str(v)
                    ds._obj[key] = xr.DataArray(attrs=tmpdict2)

            ds = ds.set_spatial_ref(kwargs['spatial_ref'])

            self._xarray = ds._obj

    def add_raster(self, *args, **kwargs):
        """Add Raster data to the survey.

        See Also
        --------
        gspy.Raster : For instantiation/reading requirements

        """
        self._raster.append(Raster.read(*args, spatial_ref=self.spatial_ref, **kwargs))

    def add_tabular(self, type, data_filename, metadata_file=None, **kwargs):
        """Add Tabular data to the survey

        Parameters
        ----------
        data_filename : str
            File to read data from
        metadata_file : str, optional
            Metadata file for the tabular data

        See Also
        --------
        gspy.Tabular : For instantiation/reading requirements

        """
        from ..data import tabular_aseg
        from ..data import tabular_csv

        if type == 'aseg':
            out = tabular_aseg.Tabular_aseg.read(data_filename, metadata_file=metadata_file, spatial_ref=self.spatial_ref, **kwargs)

        elif type == 'csv':
            out = tabular_csv.Tabular_csv.read(data_filename, metadata_file=metadata_file, spatial_ref=self.spatial_ref, **kwargs)

        elif type == 'netcdf':
            out = Tabular.open_netcdf(data_filename, **kwargs)

        self._tabular.append(out)

    def read_metadata(self, filename=None):
        """Read json metadata for the survey

        Parameters
        ----------
        filename : str
            Json file.

        Returns
        -------
        dict

        See Also
        --------
        Survey.write_metadata_template : For more metadata data information

        """

        if filename is None:
            self.write_metadata_template()
            raise Exception("Please re-run and specify the survey metadata when instantiating Survey()")

        # reading the data from the file
        with open(filename) as f:
            s = f.read()

        return json.loads(s)

    @staticmethod
    def write_metadata_template():
        """Creates a metadata template for a Survey

        If a Survey metadata file is not found or passed, an empty template file is generated and
        an Exception is raised.

        Raises
        ------
        Exception
            "Please re-run and specify metadata when instantiating Survey()"
        """

        print("\nGenerating an empty metadata file for the survey.\n")

        out = {
            "dataset_attrs" : {
                "title": "",
                "institution": "",
                "source":  "",
                "history": "",
                "references": "",
                "comment": "",
                "conventions": "CF-1.8"
                },
            "survey_information" : {
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
                },
            "spatial_ref" : {
                "datum" : "",
                "projection" : "",
                "utm_zone" : "",
                "epsg": ""
                },
            "flightline_information" : {
                "traverse_line_spacing" : "",
                "traverse_line_direction" : "",
                "tie_line_spacing" : "",
                "tie_line_direction" : "",
                "nominal_line_spacing" : "",
                "nominal_terrain_clearance" : "",
                "final_line_kilometers" : "",
                "traverse_line_numbers" : "",
                "tie_line_numbers": ""
                },
            "survey_equipment" : {
                "aircraft" : "",
                "magnetometer" : "",
                "spectrometer_system" : "",
                "radar_altimeter_system" : "",
                "radar_altimeter_sample_rat" : "",
                "laser_altimeter_system" : "",
                "navigation_system" : "",
                "acquisition_system" : ""
                },
            "system_information" : {
                "instrument_type" : ""
                }
        }

        with open("survey_md.json", "w") as f:
            json.dump(out, f, indent=4)

    @classmethod
    def open_netcdf(cls, filename, **kwargs):
        """Read a survey from a netcdf file with lazy loading

        Parameters
        ----------
        filename : str
            Netcdf file name

        Returns
        -------
        out : gspy.Survey

        """

        self = cls()

        self.xarray = Dataset.open_dataset(filename, group='survey')

        with h5py.File(filename, 'r') as f:
            groups = list(f['survey'].keys())

        rootgrp = ncdf4_Dataset(filename)

        if 'tabular' in groups:
            for i in rootgrp.groups['survey'].groups['tabular'].groups:
                self.add_tabular(type='netcdf', data_filename=filename, metadata_file=None, group='survey/tabular/{}'.format(int(i)), **kwargs)

        if 'raster' in groups:
            for i in rootgrp.groups['survey'].groups['raster'].groups:
                self._raster.append(Raster.open_netcdf(filename=filename, group='survey/raster/{}'.format(int(i))))

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
        """Write a survey to a netcdf file as well as any attached datasets.

        Parameters
        ----------
        filename : str
            Netcdf file name

        """

        # Survey
        self.xarray.to_netcdf(filename, mode='w', group='survey', format='netcdf4', engine='netcdf4')

        # Tabular
        for i, m in enumerate(self._tabular):
            Tabular(m).write_netcdf(filename, group="survey/tabular/{}".format(i))

        # Raster
        for i, m in enumerate(self._raster):
            Raster(m).write_netcdf(filename, group='survey/raster/{}'.format(i))

    def write_ncml(self, filename):
        """ Write an NcML (NetCDF XML) metadata file

        TODO: Re-write this.

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
            m.gs_dataset.write_ncml(filename, group="tabular", index=i)
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
            m.gs_dataset.write_ncml(filename, group="raster", index=i)
            f = open(infile, 'a')
            f.write('    </group>\n\n')
            if i == len(self._raster)-1:
                f.write('  </group>\n\n')
            f.close()

        f = open(infile, 'a')
        f.write('</group>\n\n')
        f.write('</netcdf>')
        f.close()

    @property
    def contents(self):
        """print out the contents of the survey"""

        out = ""
        # tabular
        if len(self.tabular) > 0:
            out += 'tabular:\n'
            if isinstance(self.tabular, list):
                for t, tab in enumerate(self.tabular):
                    out += '    [%i] %s\n' % (t, tab.attrs['content'])
            else:
                out += '    [0] %s\n' % (self.tabular.attrs['content'])

        # raster
        if len(self.raster) > 0:
            out += 'raster:\n'
            if isinstance(self.raster, list):
                for r, rast in enumerate(self.raster):
                    out += '    [%i] %s\n' % (r, rast.attrs['content'])
            else:
                out += '    [0] %s\n' % (self.raster.attrs['content'])

        return out
