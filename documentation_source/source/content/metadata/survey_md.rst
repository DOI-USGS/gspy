###############
Survey Metadata
###############

Global attributes for the Survey group are passed through the dataset attributes, ``dataset_attrs`` dictionary. The fields below are **required** attributes. Additional fields are welcome at the user's discretion. See `CF conventions <https://cfconventions.org/Data/cf-conventions/cf-conventions-1.13/cf-conventions.html#description-of-file-contents>`_ for full description of these fields.

.. literalinclude:: ../../_static/template_survey_md.yml
   :language: yaml
   :linenos:
   :lineno-match:
   :lines: 1-12

Coordinate reference system (CRS) information is passed through the ``spatial_ref`` dictionary. GSPy requires at least one of the following fields to generates the complete spatial_ref coordinate variable with all necessary fields to accurately plot in GIS software. 

.. literalinclude:: ../../_static/template_survey_md.yml
   :language: yaml
   :linenos:
   :lineno-match:
   :lines: 12-20

Additional global metadata that pertains to the Survey and all the datasets it will contain can be added as discrete dictionaries:

.. literalinclude:: ../../_static/template_survey_md.yml
   :language: yaml
   :linenos:
   :lineno-match:
   :lines: 20-44


