import xarray as xr
from .Container import Container
from ..gs_dataset.Dataset import Dataset
from ..metadata.Metadata import Metadata

class Survey(Container):

    @classmethod
    def from_dict(cls, metadata):

        metadata = cls.read_metadata(metadata) if isinstance(metadata, str) else metadata
        assert isinstance(metadata, dict), TypeError('metadata must have type dict')

        # Pull any nominal systems from the metadata
        systems, metadata = Container.Systems(**metadata)

        self = cls(xr.DataTree.from_dict({'survey': Dataset.Survey(**metadata)}))

        # Insert any nominal systems into the survey
        self._obj['survey'].update(systems)

        return self._obj

    @staticmethod
    def metadata_template(metadata={}, **kwargs):

        md = Survey.read_metadata(metadata) if isinstance(metadata, str) else metadata

        a = Metadata.merge(dict(title = "??", institution = "??", source = "??", history = "??",
                        references = "??", comment = "??", conventions = "CF-1.8"),
                        md.get('dataset_attrs', {}))

        b = Metadata.merge(dict(contractor_project_number = "??", contractor = "??", client = "??",
                                survey_type = "??", survey_area_name = "??", state = "??", country = "??",
                                acquisition_start = "yyyymmdd", acquisition_end = "yyyymmdd",
                                dataset_created = "yyyymmdd"),
                                md.get('survey_information', {}))

        c = Metadata.merge(dict(datum = "??", projection = "??", utm_zone = "??", epsg = "??"),
                           md.get('spatial_ref', {}))

        d = Metadata.merge(dict(traverse_line_spacing = "??", traverse_line_direction = "??", tie_line_spacing = "??",
                                tie_line_direction = "??", nominal_line_spacing = "??", nominal_terrain_clearance = "??",
                                final_line_kilometers = "??", traverse_line_numbers = "??", tie_line_numbers = "??"),
                                md.get('flightline_information', {}))

        e = Metadata.merge(dict(aircraft = "??", magnetometer = "??", spectrometer_system = "??",
                                radar_altimeter_system = "??", radar_altimeter_sample_rate = "??",
                                laser_altimeter_system = "??", navigation_system = "??", acquisition_system = "??"),
                                md.get('survey_equipment', {}))

        out = Metadata(dict(dataset_attrs = a,
                    survey_information = b,
                    spatial_ref = c,
                    flightline_information = d,
                    survey_equipment = e))
        return out

    # # def write_ncml(self, filename):
    # #     """ Write an NcML (NetCDF XML) metadata file

    # #     TODO: Re-write this.

    # #     Parameters
    # #     ----------
    # #     filename : str
    # #         Name of the NetCDF file to generate NcML for

    # #     """

    # #     infile = '{}.ncml'.format('.'.join(filename.split('.')[:-1]))
    # #     f = open(infile, 'w')

    # #     f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
    # #     f.write('<netcdf xmlns="http://www.unidata.ucar.edu/namespaces/netcdf/ncml-2.2" location="{}">\n\n'.format(filename.split(os.sep)[-1]))
    # #     f.write('<group name="/survey">\n\n')

    # #     ### Survey Dimensions:
    # #     for dim in self.xarray.dims:
    # #         f.write('  <dimension name="%s" length="%s"/>\n' % (dim, self.xarray.dims[dim]))
    # #     if len(self.xarray.dims) > 0:
    # #         f.write('\n')

    # #     ### Survey Attributes:
    # #     for attr in self.xarray.attrs:
    # #         att_val = self.xarray.attrs[attr]
    # #         if '"' in str(att_val):
    # #             att_val = att_val.replace('"',"'")
    # #         f.write('  <attribute name="%s" value="%s"/>\n' % (attr, att_val))
    # #     f.write('\n')

    # #     ### Survey Variables:
    # #     for var in self.xarray.variables:
    # #         tmpvar = self.xarray.variables[var]
    # #         dtype = str(tmpvar.dtype).title()[:-2]
    # #         if var == 'crs' or dtype == 'object':
    # #             f.write('  <variable name="%s" shape="%s" type="String">\n' % (var, " ".join(tmpvar.dims)))
    # #         else:
    # #             f.write('  <variable name="%s" shape="%s" type="%s">\n' % (var, " ".join(tmpvar.dims), dtype))
    # #         for attr in tmpvar.attrs:
    # #             att_val = tmpvar.attrs[attr]
    # #             if '"' in str(att_val):
    # #                 att_val = att_val.replace('"',"'")
    # #             f.write('    <attribute name="%s" type="String" value="%s"/>\n' % (attr, att_val))
    # #         f.write('  </variable>\n\n')
    # #     f.close()

    # #     # Tabular
    # #     for i, m in enumerate(self._tabular):
    # #         f = open(infile, 'a')
    # #         if i == 0:
    # #             f.write('  <group name="/tabular">\n\n')
    # #         f.write('    <group name="/{}">\n\n'.format(i))
    # #         f.close()
    # #         m.gs_dataset.write_ncml(filename, group="tabular", index=i)
    # #         f = open(infile, 'a')
    # #         f.write('    </group>\n\n')
    # #         if i == len(self._tabular)-1:
    # #             f.write('  </group>\n\n')
    # #         f.close()

    # #     # Raster
    # #     for i, m in enumerate(self._raster):
    # #         f = open(infile, 'a')
    # #         if i == 0:
    # #             f.write('  <group name="/raster">\n\n')
    # #         f.write('    <group name="/{}">\n\n'.format(i))
    # #         f.close()
    # #         m.gs_dataset.write_ncml(filename, group="raster", index=i)
    # #         f = open(infile, 'a')
    # #         f.write('    </group>\n\n')
    # #         if i == len(self._raster)-1:
    # #             f.write('  </group>\n\n')
    # #         f.close()

    # #     f = open(infile, 'a')
    # #     f.write('</group>\n\n')
    # #     f.write('</netcdf>')
    # #     f.close()

    # # @property
    # # def contents(self):
    # #     """print out the contents of the survey"""

    # #     out = ""
    # #     # tabular
    # #     if len(self.tabular) > 0:
    # #         out += 'tabular:\n'
    # #         if isinstance(self.tabular, list):
    # #             for t, tab in enumerate(self.tabular):
    # #                 out += '    [%i] %s\n' % (t, tab.attrs['content'])
    # #         else:
    # #             out += '    [0] %s\n' % (self.tabular.attrs['content'])

    # #     # raster
    # #     if len(self.raster) > 0:
    # #         out += 'raster:\n'
    # #         if isinstance(self.raster, list):
    # #             for r, rast in enumerate(self.raster):
    # #                 out += '    [%i] %s\n' % (r, rast.attrs['content'])
    # #         else:
    # #             out += '    [0] %s\n' % (self.raster.attrs['content'])

    # #     return out


