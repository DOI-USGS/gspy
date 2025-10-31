
from os import path, sep
from copy import copy
from ..metadata.Metadata import Metadata
from ..gs_dataarray.Spatial_ref import Spatial_ref
from pprint import pprint
from ..gs_dataset.System import System
from ..gs_dataset.Tabular import Tabular
from ..gs_dataset.Raster import Raster

from xarray import DataArray as xr_DataArray
from xarray import DataTree, register_datatree_accessor

@register_datatree_accessor('gs')
class Container:
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

    Survey(metadata)

    Parameters
    ----------
    metadata : str or dict
        * If str, a metadata file
        * If dict, dictionary of survey metadata.

    Returns
    -------
    gspy.Survey

    See Also
    --------
    .Spatial_ref : For information on creating a spatial ref

    """
    def __init__(self, xarray_obj):
        self._obj = xarray_obj

    @property
    def tree(self):
        out = ''
        for node in self._obj.subtree:
            out += node.path + '\n'
        return out

    @staticmethod
    def metadata_template(metadata_filename=None, **kwargs):

        template = dict(content = "<Container content summary>",
                        comment = "<additional details or ancillary information>",
                        type = "container")

        out = Metadata(template)
        return out

    def set_spatial_ref(self, kwargs):
        """Set the spatial ref of the Dataset.

        Specifically adds an xarray coordinate called 'spatial_ref' which is required for GIS software and the CF convention.

        Important
        ---------
        Make sure you call this method into a return variable

                ``ds = ds.add_coordinate_from_dict``

        Otherwise, the spatial_ref will not be added correctly.

        Parameters
        ----------
        kwargs : dict, gspy.Spatial_ref, or xarray.DataArray
            * If dict: creates a Spatial_ref from a dict of metadata.
            * If an existing spatial ref, assign by reference

        Returns
        -------
        Dataset
            Dataset with spatial_ref added.

        See Also
        --------
        ...Survey.Spatial_ref : for more details of creating a Spatial_ref

        """
        if not ('spatial_ref' in self._obj):
            assert isinstance(kwargs, (dict, Spatial_ref, xr_DataArray)), TypeError("spatial_ref must have type (dict, gspy.Spatial_ref)")
            if isinstance(kwargs, dict):
                crs = Spatial_ref.from_dict(kwargs)
            else:
                crs = kwargs # This is a pre-existing Spatial_ref/DataArray

            self._obj['spatial_ref'] = crs
            self._obj = self._obj.assign_coords({'spatial_ref' : crs})

        return self._obj


    @classmethod
    def from_dict(cls, metadata={}):
        collection = {}

        metadata = cls.read_metadata(metadata) if isinstance(metadata, str) else metadata

        self = cls(DataTree.from_dict(collection))
        self._obj.attrs.update(metadata)

        self._obj.attrs['type'] = 'container'

        return self._obj

    @staticmethod
    def read_metadata(filename=None):
        """Read metadata for the survey

        Parameters
        ----------
        filename : str
            Metadata file.

        Returns
        -------
        dict

        See Also
        --------
        Survey.write_metadata_template : For more metadata data information

        """
        if filename is None:
            md_template = super.metadata_template()
            md_template.dump("survey_metadata_template.yml")
            raise Exception("Please re-run and specify the survey metadata when instantiating Survey()")

        # reading the data from the file
        return Metadata.read(filename)

    def add_container(self, key, **kwargs):
        """Add a container to the survey

        Parameters
        ----------
        key : str
            Name of the container.
        kwargs : dict
            Metadata for the container.

        Returns
        -------
        xarray.DataTree

        """
        if key in self._obj:
            return self._obj[key]

        container = Container.from_dict(kwargs)

        assert "spatial_ref" in self._obj, KeyError("spatial_ref not found. Make sure you are adding a container to the correct group.")

        container['spatial_ref'] = self._obj.spatial_ref
        container = container.assign({'spatial_ref' : self._obj.spatial_ref})

        self._obj[key] = container
        return self._obj[key]

    def add(self, key, *args, **kwargs):
        assert key not in self._obj, KeyError(f"{key} already exists in the container. Please use a different key.")
        self._obj[key] = Container.Data(*args, spatial_ref=self._obj['spatial_ref'], **kwargs)
        return self._obj[key]

    @classmethod
    def Data(cls, data_filename=None, metadata_file=None, spatial_ref=None, **kwargs):

        json_md = Metadata.read(metadata_file)

        system = kwargs.get('system', {})

        # No systems were passed through, try to read from metadata
        if len(system) == 0:
            for key in list(json_md.keys()):
                if "system" in key:
                    system[key] = json_md.pop(key)

            # Systems were found, create a System datatree/dataset
            if len(system) > 0:
                system, _ = Container.Systems(**system)

        # Attach apriori given system dict
        kwargs['system'] = system

        if data_filename is None:
            dataset = Raster.read(metadata_file=json_md, spatial_ref=spatial_ref, **kwargs)
        else:
            dataset = Tabular.read(data_filename, metadata_file=json_md, spatial_ref=spatial_ref, **kwargs)

        self = cls(DataTree(dataset))

        if isinstance(system, dict):
            if len(system) > 0:
                self._obj.update(system)
        else:
            if len(system.children) == 0:
                self._obj.update({system.name:system})
            else: # This is meant for DataTrees with multiple systems
                for key in system.children:
                    self._obj[key] = system[key]

        return self._obj

    @classmethod
    def Systems(cls, **kwargs):
        systems = {}
        for key in list(kwargs.keys()):
            if "system" in key:
                value = kwargs.pop(key)
                systems[key] = System.from_dict(name=key, **value)

        out = DataTree.from_dict(systems)

        return out, kwargs

    def to_netcdf(self, *args, **kwargs):
        """Write the survey to a netcdf file

        Parameters
        ----------
        args : list
            Arguments to pass to xarray.Dataset.to_netcdf
        kwargs : dict
            Keyword arguments to pass to xarray.Dataset.to_netcdf

        Returns
        -------
        None

        """
        kwargs["format"] = kwargs.get("format", "NETCDF4")
        kwargs["engine"] = kwargs.get("engine", "h5netcdf")
        # kwargs["invalid_netcdf"] = kwargs.get("invalid_netcdf", True)

        # If this container is a survey, write out the parent to maintain '/' in the netcdf file

        if self._obj.attrs['type'] == 'survey':
            for item in list(self._obj):
                if self._obj[item].attrs.get('type', '') == 'system':
                    del self._obj[item]
            out = self._obj.parent
        else:
            out = self._obj

        out.to_netcdf(*args, **kwargs)

    def plot(self, *args, **kwargs):
        self._obj.to_dataset().gs.plot(*args, **kwargs)

    def scatter(self, *args, **kwargs):
        self._obj.to_dataset().gs.scatter(*args, **kwargs)

    def subset(self, key, value):
        out = self._obj.to_dataset()
        return out.where(out[key]==value)

    def add_timestamp(self, *args, **kwargs):
        self._obj.to_dataset().gs.add_timestamp(*args, **kwargs)

    def plot_cross_section(self, *args, **kwargs):
        self._obj.to_dataset().gs.plot_cross_section(*args, **kwargs)

    def get_all_attr(self, attr, path=None, **kwargs):
        if path is None:
            path = self._obj.name
        if self._obj.attrs['type'] in ('survey', 'container'):
            for item in self._obj.children:
                kwargs = self._obj[item].gs.get_all_attr(attr, path=path+f"/{item}", **kwargs)
        else:
            kwargs = self._obj.to_dataset().gs.get_all_attr(attr, path=path, **kwargs)
        return kwargs

    def write_ncml(self, file, indent=0):
        """ Write an NcML (NetCDF XML) metadata file

        Parameters
        ----------
        filename : str
            Name of the NetCDF file to generate NcML for

        """

        si = "  "*indent

        if isinstance(file, str):
            base_name = file.split(sep)[-1]
            file = open(f"{'.'.join(file.split('.')[:-1])}.ncml", 'w')

            file.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            file.write(f'<netcdf xmlns="http://www.unidata.ucar.edu/namespaces/netcdf/ncml-2.2" location="{base_name}">\n\n')

        # First do my dataset if there is one.
        self._obj.to_dataset().gs.write_ncml(file, self._obj.name, indent, no_end=True)

        for child in self._obj.children:
            self._obj[child].gs.write_ncml(file, indent+1)
        file.write(f'{si}</group>\n')

        if indent == 0:
            file.write(f'</netcdf>')
            file.close()

    # System specific accessor
    def get_system_with_method(self, method):
        sys = None
        for this in self._obj:
            if self._obj[this].attrs['method'] == method:
                sys = self._obj[this].to_dataset()
        assert not sys is None, ValueError(f"Could not find system with method attrs '{method}'")
        return sys

