import os
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

        self._obj['survey'].attrs['type'] = 'survey'

        return self._obj['survey']

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


