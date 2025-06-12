"""
Coordinate Reference Systems
----------------------------

Every Survey must have a coordinate reference system (CRS) defined and all datasets within the Survey adhere to the same CRS.

This example explores the CRS variable and shows how it is linked to data variables.


Dataset Reference:
Minsley, B.J, Bloss, B.R., Hart, D.J., Fitzpatrick, W., Muldoon, M.A., Stewart, E.K., Hunt, R.J., James, S.R., Foks, N.L., and Komiskey, M.J., 2022, Airborne electromagnetic and magnetic survey data, northeast Wisconsin (ver. 1.1, June 2022): U.S. Geological Survey data release, https://doi.org/10.5066/P93SY9LI.

"""

#%%
import matplotlib.pyplot as plt
from os.path import join
import gspy
from gspy import Survey
from pprint import pprint

#%%

survey = gspy.open_datatree("../../../../example_material/example_1/model/WISkyTEM.nc")['survey']

################################################################################
# The CRS variable is called ``spatial_ref`` and gets initialized in the Survey.
# The ``spatial_ref`` is a dataless coordinate variable, meaning there are no data values,
# all information is contained within attributes.
print(survey.spatial_ref)

################################################################################
# The Survey also has a spatial_ref property which returns the ``spatial_ref`` variable

#%%
# Grid Mapping
# ++++++++++++

################################################################################
# Following the `CF conventions on Grid Mappings <http://cfconventions.org/Data/cf-conventions/cf-conventions-1.10/cf-conventions.html#appendix-grid-mappings>`_,
# the ``spatial_ref`` variable should contain key information defining the coordinate
# reference system. The attribute ``grid_mapping_name`` is required. Other key
# attributes include ``wkid`` and ``crs_wkt``.
print('grid_mapping_name: '+survey.spatial_ref.attrs['grid_mapping_name'])
print('wkid: '+survey.spatial_ref.attrs['wkid'])
print('crs_wkt: '+survey.spatial_ref.attrs['crs_wkt'])

################################################################################
# Then, each data variable should have an attribute ``grid_mapping`` that references
# the ``spatial_ref`` coordinate variable
pprint(survey['data']['raw_data']['dem'].attrs)

#%%
# Making a new Spatial Ref
# ++++++++++++++++++++++++

################################################################################
# If you need to make a new ``spatial_ref`` variable, this can
# be done with GSPy's Spatial_ref class
from gspy.gs_dataarray.Spatial_ref import Spatial_ref

################################################################################
# The Spatial_ref class takes a dictionary of values and looks for a
# ``wkid``, ``crs_wkt``, or a ``proj_string`` in that order. Note, a ``wkid``
# should have an ``authority`` key passed with it either as a separate ``authority``
# field, or as a colon separated string, e.g., 'EPSG:4326'. If none is provided
# EPSG will be used by default.
new_crs = Spatial_ref.from_dict({'wkid': 4326, 'authority': 'EPSG'})

pprint(new_crs)

################################################################################
# Note: If you are resetting the CRS variable in a Survey, be sure that all data
# groups are also updated to match and all coordinate variables (particularly
# ``x``, ``y``, and ``z``) need to be updated. In other words, if you change from a
# projected coordinate system with easting and northing coordinates to a geographic
# coordinate system, then the ``x`` and ``y`` coordinate variables need to be
# changed to longitude and latitude.