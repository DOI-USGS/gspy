"""Run the full Tempest (ASEG-GDF) workshop pipeline headlessly.

Mirrors the solution path of 2_tempest_aseg.ipynb.  Run from the workshop root:

    python tools/verify_tempest.py

"""
import warnings
from os.path import join

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402

import gspy  # noqa: E402
from gspy import Dataset, Survey  # noqa: E402

warnings.filterwarnings('ignore')

DATA = 'data/tempest'
PREPARED = 'prepared_metadata/tempest'
SCRATCH = 'my_metadata'

# ---------------------------------------------------------------- templates
print("== Dataset template straight from the ASEG-GDF file ==")
template = Dataset.metadata_template(join(DATA, 'Tempest.dat'))
template.dump(join(SCRATCH, 'tempest_raw_template.yml'))
print(f"{len(template['variables'])} variables")
for name in ('Line', 'DTM', 'EMX_HPRG'):
    print(f"  {name} -> {template['variables'][name]}")

# ------------------------------------------------------------------- survey
print("\n== Survey ==")
survey = Survey.from_dict(join(PREPARED, 'Tempest_survey_md.yml'))
print(survey.gs.tree)

# --------------------------------------------------------------------- data
data_container = survey.gs.add_container('data', **dict(content="raw data"))

rd = data_container.gs.add(key='raw_data',
                           data=join(DATA, 'Tempest.dat'),
                           metadata_file=join(PREPARED, 'Tempest_data_md.yml'))
print("raw_data ok", dict(rd.sizes))

# ------------------------------------------------------------------- models
model_container = survey.gs.add_container(
    'models', **dict(content="inverted 1-D electrical resistivity models"))

mod = model_container.gs.add(key='inverted_models',
                             data=join(DATA, 'Tempest_model.dat'),
                             metadata_file=join(PREPARED, 'Tempest_model_md.yml'),
                             system=rd.tempest_system,
                             derived_from=rd)
print("inverted_models ok", dict(mod.sizes))

# -------------------------------------------------------------------- raster
map_container = survey.gs.add_container('derived_maps', **dict(content="derived maps"))

maps = map_container.gs.add(key='maps',
                            metadata_file=join(PREPARED, 'Tempest_raster_md.yml'))
print("maps ok", dict(maps.sizes))

# -------------------------------------------------------------------- netcdf
out = join(SCRATCH, 'tempest_workshop.nc')
survey.gs.to_netcdf(out)
print("\nwrote", out)

new_survey = gspy.open_datatree(out)['survey']
print(new_survey.gs.tree)

# ---------------------------------------------------------------- inspection
print("\n== Inspecting metadata ==")
raw = new_survey['data']['raw_data']
print("dataset attrs:", list(raw.attrs)[:8])
print("one variable:", list(raw.data_vars)[:5])

# ------------------------------------------------------------------ plotting
plt.figure()
new_survey['data']['raw_data'].gs.scatter(x='x', hue='tx_height', cmap='jet')
plt.figure()
new_survey['derived_maps/maps']['magnetic_tmi'].plot(cmap='jet', robust=True)
plt.close('all')
print("\nplots ok")
print("\nALL TEMPEST STEPS PASSED")
