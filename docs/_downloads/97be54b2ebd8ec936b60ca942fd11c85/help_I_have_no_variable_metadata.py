
"""
Help! I have no variable metadata
---------------------------------

"""
#%%
from os.path import join
from gspy import Survey

# Path to example files
data_path = '..//..//supplemental'

# Define ..//supplemental information file
..//supplemental = join(data_path, "region//MAP//data//Resolve_survey_md.json")

survey = Survey(..//supplemental)

d_data = join(data_path, 'region//MAP//data//Resolve.csv')
d_supp = join(data_path, 'region//MAP//data//Resolve_data_md_without_variables.json')

survey.add_tabular(type='csv', data_filename=d_data, metadata_file=d_supp)