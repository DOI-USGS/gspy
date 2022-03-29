import os

from .Key_mapping import key_mapping
from ...utilities import flatten, unflatten
from ..survey.Spatial_ref import Spatial_ref
import matplotlib.pyplot as plt
import xarray as xr
import json

class Data(object):
    """Abstract Base Class """

    def __init__(self):
        raise NotImplementedError("Cannot instantiate ABC Data class")

    @property
    def attrs(self):
        return self.xarray.attrs

    @property
    def key_mapping(self):
        return self._key_mapping

    @key_mapping.setter
    def key_mapping(self, value):
        if value is None:

            print("\nGenerating an empty mapping file for {}.\n".format(self.data_filename))

            tmp = self.required_mapping
            with open('{}_key_mapping.txt'.format(self.data_filename), 'w') as f:
                json.dump(tmp, f, indent=4)

            # raise Exception("Must specify a mapping file.")

        else:
            self._key_mapping = key_mapping(value)

    @property
    def spatial_ref(self):
        return self._spatial_ref

    @spatial_ref.setter
    def spatial_ref(self, value):
        if isinstance(value, Spatial_ref):
            self._spatial_ref = value
        elif isinstance(value, dict):
            self._spatial_ref = Spatial_ref(**value)

    @property
    def json_metadata(self):
        return self._json_metadata

    @json_metadata.setter
    def json_metadata(self, value):
        assert isinstance(value, dict), TypeError('json_metadata must have type dict')
        self._json_metadata = value

    @property
    def xarray(self):
        return self._xarray

    def _add_general_metadata_to_xarray(self, kwargs):
        kwargs = flatten(kwargs, '', {})
        self.xarray.attrs.update(kwargs)

    def pcolor(self, variable, stack=None, **kwargs):
        if not stack is None:
            self.xarray[variable].sel(stack=stack).plot(**kwargs)
        else:
            self.xarray[variable].plot(**kwargs)

    def read_metadata(self, filename):
        """Read a json metadata file.

        Parses the dictionaries from the metadata and adds them to the appropriate classes.

        Parameters
        ----------
        filename : str
            Json file.

        """
        # reading the data from the file
        with open(filename) as f:
            s = f.read()

        dic = json.loads(s)

        assert 'key_mapping' in dic, ValueError('Need to define key_mapping for required keys {} in supplemental'.format(key_mapping.required_keys))

        self.key_mapping = key_mapping(dic.pop('key_mapping'))

        self.json_metadata = dic 

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
        self = cls(None, None)

        self.type = 'netcdf'
        self.filename = filename

        self.xarray = xr.load_dataset(filename, group=group.lower())

        self.key_mapping = unflatten(self.xarray.attrs)['key_mapping']

        self.spatial_ref = spatial_ref

        return self

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

        return ax, self.xarray.plot.scatter(x=self.key_mapping['x'].strip(), y=self.key_mapping['y'].strip(), hue=variable, **kwargs)

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
            for var in self.xarray.data_vars:
                if self.xarray[var].attrs['null_value'] != 'not_defined':
                    self.xarray[var].attrs['_FillValue'] = self.xarray[var].attrs['null_value']
                if 'grid_mapping' in self.xarray[var].attrs:
                    del self.xarray[var].attrs['grid_mapping']
                #self.xarray[var].attrs['grid_mapping'] = self.xarray.spatial_ref.attrs['grid_mapping_name']
        self.xarray.to_netcdf(filename, mode=mode, group=group, format='netcdf4', engine='netcdf4')
    
    def write_ncml(self, filename, group, index):
        """Write and NCML file

        Parameters
        ----------
        filename : str
            NCML filename
        group : str
            Group name in Netcdf file to generate NCML output for.
        index : str
            
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
        for dim in self.xarray.dims: 
            f.write('%s<dimension name="%s" length="%s"/>\n' % (sp2, dim, self.xarray.dims[dim]))
        f.write('\n')

        ### Global Attributes:
        for attr in self.xarray.attrs:
            att_val = self.xarray.attrs[attr]
            if '"' in str(att_val):
                att_val = att_val.replace('"',"'")
            f.write('%s<attribute name="%s" value="%s"/>\n' % (sp2, attr, att_val))
        f.write('\n')

        ### Variables:
        for var in self.xarray.variables:
            tmpvar = self.xarray.variables[var]
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