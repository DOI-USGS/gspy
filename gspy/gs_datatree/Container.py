import numpy as np
from os import path, sep
from pathlib import Path
from copy import copy
from ..metadata.Metadata import Metadata
from ..gs_dataarray.Spatial_ref import Spatial_ref
from pprint import pprint
from ..gs_dataset.System import System
from ..gs_dataset.Parameters import Parameters
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
        out = Metadata.read(filename)
        out.pop('directory', None)

        return out

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

        #--------
        parameters = kwargs.get('parameters', {})
        # No parameters were passed through, see if any present in metadata
        if len(parameters) == 0:
            # loop over metadata keys
            for key in list(json_md.keys()):
                # if any metadata key names contain "parameters", grab them
                if "parameters" in key:
                    parameters[key] = json_md.pop(key)
            # parameters were found, create a parameters datatree/dataset
            if len(parameters) > 0:
                # TODO test this
                parameters, _ = Container.Parameters(**parameters)
        else:
            # if parameters is a file path, read contents into dictionary
            if isinstance(parameters, str):
                parameters = Metadata.read(parameters)    
            parameters, _ = Container.Parameters(**parameters)

        if isinstance(parameters, dict):
            if len(parameters) > 0:
                self._obj.update(parameters)
        else:
            if len(parameters.children) == 0:
                self._obj.update({parameters.name:parameters})
            else: # This is meant for DataTrees with multiple parameters
                for key in parameters.children:
                    self._obj[key] = parameters[key]
        return self._obj

    @classmethod
    def Systems(cls, **kwargs):
        systems = {}
        for key in list(kwargs.keys()):
            if "system" in key:
                value = kwargs.pop(key)
                print('here! '+key)
                systems[key] = System.from_dict(name=key, **value)

        out = DataTree.from_dict(systems)

        return out, kwargs

    @classmethod
    def Parameters(cls, **kwargs):
        parameters = {}
        for key in list(kwargs.keys()):
            if "parameters" in key:
                value = kwargs.pop(key)
                parameters[key] = Parameters.from_dict(name=key, **value)

        out = DataTree.from_dict(parameters)

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

        # # correct objects
        # for node in out.subtree:
        #     for name, var in node.variables.items():
        #         if var.dtype == object:
        #             node[name] = node[name].astype(str)
        #         for att in var.attrs:
        #             if type(var.attrs[att]) == object:
        #                 print('here I am!!!!!!!!!!!!!!!!!!!')
        #                 var.attrs[att] = var.attrs[att].astype(str)
        #     for att in node.attrs:
        #         #print(type(node.attrs[att]))
        #         if type(node.attrs[att]) == object:
        #             print('here I am-----------------')
        #             node.attrs[att] = node.attrs[att].astype(str)

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

    def to_tif(self, var=None, slice_dim=None, out_dir=None):
        """
        Export GeoTIFF files from xarray.

        - If `var` is provided, export only that variable.
        - If `var` is None, export all variables.
        - If `slice_dim` is provided and exists on a variable, export one file per slice along that dim.
        Otherwise export a single file per variable.

        Parameters
        ----------
        var : str | None
            Name of the variable to export. If None, all variables are exported.
        slice_dim : str | None
            Name of the dimension to slice along for 3D variables (e.g., "time" or "band").
        out_dir : str | Path
            Output directory for GeoTIFF files
        """
        # Ensure we are on a raster structure
        assert self._obj.attrs.get("structure") == "raster", "structure must be 'raster' to export to tif"

        ds = self._obj
        
        if out_dir is not None:
            out_dir = Path(out_dir)

        if var is None:
            # Export ALL variables
            for var_name in ds.data_vars:
                _write_one_var_to_tif(ds, var_name, slice_dim, out_dir)
        else:
            # Export JUST the requested variable
            _write_one_var_to_tif(ds, var, slice_dim, out_dir)

def _write_one_var_to_tif(ds, var_name, slice_dim=None, out_dir=None):
    """
    Write a single variable from ds to GeoTIFF(s).
    If slice_dim is provided and the variable has that dimension,
    write one GeoTIFF per slice; otherwise write a single GeoTIFF.
    """
    # skip bnds variables
    if "bnds" in var_name:
        return

    if var_name not in ds.data_vars:
        raise KeyError(f"Variable '{var_name}' not found in dataset.")

    da = ds[var_name].copy()

    # --- enforce slice_dim logic for 3D variables -----------------------------
    if da.ndim == 3 and slice_dim is None:
        raise ValueError(
            f"Variable '{var_name}' is 3D with dims {da.dims}. "
            f"Please provide `slice_dim` (one of {list(da.dims)}) to export slices."
        )

    # Remove CF 'grid_mapping' attr if present;
    # rioxarray stores CRS separately (.rio.write_crs / .rio.crs)
    if "grid_mapping" in da.attrs:
        del da.attrs["grid_mapping"]


    gt = da['spatial_ref'].attrs.get("GeoTransform")
    if gt is None:
        raise ValueError(f"No 'GeoTransform' attribute found in spatial_ref")

    # Convert tuple/list/ndarray to a space-separated string
    if isinstance(gt, (tuple, list, np.ndarray)):
        da['spatial_ref'].attrs["GeoTransform"] = " ".join(map(str, gt))
    elif isinstance(gt, str):
        pass  # already OK
    else:
        raise TypeError(f"'GeoTransform' must be str/tuple/list/ndarray, got {type(gt)}")

    # Validate: must parse to 6 values per GDAL geotransform definition
    arr = np.fromstring(da['spatial_ref'].attrs["GeoTransform"], sep=" ")
    if arr.size != 6:
        raise ValueError(f"'GeoTransform' must have six values, got {arr.size}.")

    # Set _FillValue from null_value if present
    if "null_value" in da.attrs and "_FillValue" not in da.attrs:
        if "null_value" != "not_defined":
            da.attrs["_FillValue"] = da.attrs["null_value"]

    # If variable has slice_dim, export per slice
    if slice_dim is not None and slice_dim in da.dims:
        for s in da[slice_dim].values:
            da_sel = da.sel({slice_dim: s})
            if out_dir is not None:
                out_path = out_dir / f"{var_name}_{s}.tif"
            else:
                out_path = f"{var_name}_{s}.tif"
            da_sel.rio.to_raster(str(out_path))
    else:
        if out_dir is not None:
            out_path = out_dir / f"{var_name}.tif"
        else:
            out_path = f"{var_name}.tif"
        print(out_path)
        da.rio.to_raster(str(out_path))


