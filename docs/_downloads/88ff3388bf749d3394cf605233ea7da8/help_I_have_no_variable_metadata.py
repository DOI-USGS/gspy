"""
Help! I have no variable metadata
---------------------------------

This example shows how GSPy can help when you have a large data file and need to do the tedious task of filling out the variable metadata.

By doing a first-pass through GSPy with a data json file that is *missing* the ``variable_metadata`` dictionary, the code will break, but will generate a template file containing placeholder metadata dictionaries for all variables from the data file (in this case the column headers of the CSV data file). The user can then fill in this template and then add it to the data json file.

This image shows a snippet of what the output template json file contains. Each variable is given a dictionary of attributes with the default values of "not_defined" which the user can then go through and update.

"""
#%%

from os.path import join
from gspy import Survey
import matplotlib.pyplot as plt
from matplotlib import image as img

#%%
# Generate the Variable Metadata Template for My Dataset
# ++++++++++++++++++++++++++++++++++++++++++++++++++++++

# Path to example files
data_path = '..//..//..//..//example_material//example_2'

# Define the Survey metadata file
metadata = join(data_path, "data//Resolve_survey_md.yml")

# Initialize the Survey
survey = Survey(metadata)

#%%

# Define input data file (CSV format) and the
# associated metadata file (without the variable_metadata dictionary)
d_data = join(data_path, 'data//Resolve.csv')
d_supp = join(data_path, 'data//Resolve_data_md_without_variables.yml')

# Attempt to add the raw AEM data from CSV-format
# This will trigger an error message when no variable metadata is found, however the error will
# output a template json file with this dataset's variable names, to then be filled in by the user
plt.imshow(img.imread("../../_static/variable_metadata_template_snippet.png"))

# try:
#    survey.add_tabular(type='csv', data_filename=d_data, metadata_file=d_supp)
# except Exception as e:
#    print(e)
# print(e)

# %%
# .. image:: ..//..//_static//variable_metadata_template_snippet.png
#    :scale: 50 %
#    :align: center
