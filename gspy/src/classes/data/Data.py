import os
from pathlib import Path
import json
import matplotlib.pyplot as plt

from pprint import pprint

import xarray as xr

from .xarray_gs.Dataset_gs import Dataset_gs
from .Key_mapping import key_mapping
from ...utilities import flatten, unflatten
from ..survey.Spatial_ref import Spatial_ref

import xarray as xr
@xr.register_dataset_accessor("data")
class Data(Dataset_gs):
    """Abstract Base Class """
    # def __init__(self):
    #     raise NotImplementedError("Cannot instantiate ABC Data class")

    # @property
    # def attrs(self):
    #     return self.xarray.attrs

    # @property
    # def key_mapping(self):
    #     return self._key_mapping

    # @key_mapping.setter
    # def key_mapping(self, value):
    #     if value is None:

    #         print("\nGenerating an empty mapping file for {}.\n".format(self.data_filename))

    #         tmp = self.required_mapping
    #         with open('{}_key_mapping.txt'.format(self.data_filename), 'w') as f:
    #             json.dump(tmp, f, indent=4)

    #         # raise Exception("Must specify a mapping file.")

    #     else:
    #         self._key_mapping = key_mapping(value)

    def __init__(self, xarray_obj):
        self._obj = xarray_obj

    @property
    def json_metadata(self):
        return self._json_metadata

    @json_metadata.setter
    def json_metadata(self, value):
        assert isinstance(value, dict), TypeError('json_metadata must have type dict')
        self._json_metadata = value

    # @property
    # def xarray(self):
    #     return self._xarray

    def pcolor(self, variable, stack=None, **kwargs):

        # print(self.xarray)

        # if not stack is None:
        #     self.xarray[variable].sel(stack=stack).plot(**kwargs)
        # else:
        self._obj[variable].plot(**kwargs)

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

        def check_key_whitespace(this, flag=False):
            if not isinstance(this, dict):
                return flag
            for key, item in this.items():
                if ' ' in key:
                    print('key "{}" contains whitespace. Please remove!'.format(key))
                    flag = True
                flag = check_key_whitespace(item, flag)
            return flag

        flag = check_key_whitespace(dic)
        assert not flag, Exception("Metadata file {} has keys with whitespace.  Please remove spaces")

        if 'coordinates' in dic:
            for key, value in dic['coordinates'].items():
                dic['coordinates'][key] = value.strip()

        return dic

    @classmethod
    def read_netcdf(cls, filename, group, spatial_ref=None, **kwargs):
        """Read Data from a netcdf file

        Parameters
        ----------
        filename : str
            Path to the netcdf file
        group : str
            Netcdf group name containing data.

        Returns
        -------
        out : gspy.Data

        """
        return super(Data, cls).open_dataset(filename, group=group.lower())

    def scatter(self, variable, **kwargs):
        """Scatter plot of variable against x, y co-ordinates

        Parameters
        ----------
        variable : str
            Xarray Dataset variable name

        Returns
        -------
        ax : matplotlib.Axes
            Figure handle
        sc : xarray.plot.scatter
            Plotting handle

        """
        ax = kwargs.pop('ax', plt.gca())
        return ax, plt.scatter(self._obj['x'].values, self._obj['y'].values, c=self._obj[variable].values, **kwargs)

    def write_netcdf(self, filename, group):
        """Write to netcdf file

        Parameters
        ----------
        filename : str
            Path to the file
        group : str
            Netcdf group name to write to

        """
        mode = 'a' if os.path.isfile(filename) else 'w'
        if 'raster' in group:
            for var in self._obj.data_vars:
                if self._obj[var].attrs['null_value'] != 'not_defined':
                    self._obj[var].attrs['_FillValue'] = self._obj[var].attrs['null_value']
                if 'grid_mapping' in self._obj[var].attrs:
                    del self._obj[var].attrs['grid_mapping']
                #self.xarray[var].attrs['grid_mapping'] = self.xarray.spatial_ref.attrs['grid_mapping_name']
        self._obj.to_netcdf(filename, mode=mode, group=group, format='netcdf4', engine='netcdf4')

    def write_ncml(self, filename, group, index):
        """Write and NCML file

        Parameters
        ----------
        filename : str
            NCML filename
        group : str
            Group name in Netcdf file to generate NCML output for.
        index : str
            todo
        """

        infile = '{}.ncml'.format('.'.join(filename.split('.')[:-1]))
        if not os.path.isfile(infile):
            print('original file not found!')
            singleflag=True
            sp1, sp2 = '', '  '
            f = open(infile, 'w')
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            f.write('<netcdf xmlns="http://www.unidata.ucar.edu/namespaces/netcdf/ncml-2.2" location="{}.nc">\n\n'.format(filename.split(os.sep)[-1]))
            f.write('{}<group name="/{}">\n\n'.format(sp1, group))
            f.write('{}<group name="/{}">\n\n'.format(sp2, index))
            f.close()
        else:
            singleflag=False
            sp1, sp2 = '  ', '    '

        f = open(infile, 'a')
        ### Dimensions:
        for dim in self._obj.dims:
            f.write('%s<dimension name="%s" length="%s"/>\n' % (sp2, dim, self._obj.dims[dim]))
        f.write('\n')

        ### Global Attributes:
        for attr in self._obj.attrs:
            att_val = self._obj.attrs[attr]
            if '"' in str(att_val):
                att_val = att_val.replace('"',"'")
            f.write('%s<attribute name="%s" value="%s"/>\n' % (sp2, attr, att_val))
        f.write('\n')

        ### Variables:
        for var in self._obj.variables:
            tmpvar = self._obj.variables[var]
            dtype = str(tmpvar.dtype).title()[:-2]
            if var == 'crs' or dtype == 'object':
                f.write('%s<variable name="%s" shape="%s" type="String">\n' % (sp2, var, " ".join(tmpvar.dims)))
            else:
                f.write('%s<variable name="%s" shape="%s" type="%s">\n' % (sp2, var, " ".join(tmpvar.dims), dtype))
            for attr in tmpvar.attrs:
                att_val = tmpvar.attrs[attr]
                if '"' in str(att_val):
                    att_val = att_val.replace('"',"'")
                f.write('%s%s<attribute name="%s" type="String" value="%s"/>\n' % (sp1, sp2, attr, att_val))
            f.write('%s</variable>\n\n' % sp2)

        if singleflag:
            f.write('{}</group>\n\n'.format(sp2))
            f.write('{}</group>\n\n'.format(sp1))
            f.write('</netcdf>')

        f.close()
