"""
Help! I have no metadata
------------------------

This example shows how GSPy can help when you have a large data file and need to do the
tedious task of filling out the variable metadata.

By doing a first-pass through GSPy with a data json file that is *missing* the ``variable_metadata`` dictionary,
the code will break, but will generate a template file containing placeholder metadata dictionaries for all
variables from the data file (in this case the column headers of the CSV data file). The user can then fill in
this template and then add it to the data json file.

This image shows a snippet of what the output template json file contains. Each variable is given a dictionary
of attributes with the default values of "not_defined" which the user can then go through and update.

"""
#%%

from os.path import join
from gspy import Survey, Dataset
import matplotlib.pyplot as plt
from matplotlib import image as img

#%%
# Generate the Variable Metadata Template for My Dataset
# ++++++++++++++++++++++++++++++++++++++++++++++++++++++

#%%
# Zero existing metadata
# Initialize the Survey
template = Survey.metadata_template()
template.dump("template_survey_empty.yml")


#%%
# Prefilled existing metadata file
# Path to example files
data_path = '..//..//..//..//example_material//example_2'

# Define the Survey metadata file
metadata = join(data_path, "data//Resolve_survey_md.yml")

# Initialize the Survey
template = Survey.metadata_template(metadata)
template.dump("template_md_survey.yml")

#%%
# Define input data file (CSV format) and the
# associated metadata file (without the variable_metadata dictionary)
data = join(data_path, 'data//Resolve.csv')
metadata = join(data_path, 'data//Resolve_data_md_without_variables.yml')

template = Dataset.metadata_template(data)
template.dump("template_md_resolve_empty.yml")

template = Dataset.metadata_template(data, metadata)
template.dump("template_md_resolve.yml")

#%%
data_path = '..//..//..//..//example_material//example_1'

data = join(data_path, 'data//WI_SkyTEM_2021_ContractorData.csv')
metadata = join(data_path, 'data//WI_SkyTEM_raw_data_md.yml')
template = Dataset.metadata_template(data, metadata)
template.dump("template_md_skytem.yml")

#%%
# Loupe Data

data_path = '..//..//..//..//example_material//example_3'

data = join(data_path, 'data//Kankakee.dat')
metadata = join(data_path, 'data//loupe_data_metadata.yml')

template = Dataset.metadata_template(data_filename=data, metadata_file=metadata)
template.dump("template_md_loupe.yml")