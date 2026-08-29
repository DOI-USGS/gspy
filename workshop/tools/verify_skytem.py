"""Run the full SkyTEM workshop pipeline headlessly, to check the trimmed data.

Mirrors the solution path of 1_skytem_from_scratch.ipynb.  Run from the
workshop root:

    python tools/verify_skytem.py

"""
import warnings
from os.path import join

import matplotlib
import numpy as np

matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402

import gspy  # noqa: E402
from gspy import Dataset, Metadata, Survey  # noqa: E402

warnings.filterwarnings('ignore')

DATA = 'data/skytem'
PREPARED = 'prepared_metadata/skytem'
SCRATCH = 'my_metadata'

# ---------------------------------------------------------------- templates
print("== Survey template ==")
template = Survey.metadata_template()
template.dump(join(SCRATCH, 'survey_template.yml'))
print(sorted(template.keys()))

print("\n== Dataset template from the raw CSV ==")
template = Dataset.metadata_template(join(DATA, 'skytem_contractor_data.csv'))
template.dump(join(SCRATCH, 'raw_data_template.yml'))
print(f"{len(template['variables'])} variables")
print("HM_X ->", template['variables']['HM_X'])

# ------------------------------------------------------------------- survey
print("\n== Survey ==")
survey = Survey.from_dict(join(PREPARED, 'skytem_survey.yml'))
print(survey.gs.tree)

# --------------------------------------------------------------------- data
data_container = survey.gs.add_container(
    'data', **dict(content="raw and processed data", comment="workshop"))

raw_systems = Metadata.read(join(PREPARED, 'skytem_system.yml'))

rd = data_container.gs.add(key='raw_data',
                           data=join(DATA, 'skytem_contractor_data.csv'),
                           metadata_file=join(PREPARED, 'skytem_contractor_data.yml'),
                           system=raw_systems)
print("raw_data ok", dict(rd.sizes))

proc_systems = {"skytem_system": rd["skytem_system"].isel(lm_gate_times=np.s_[1:],
                                                          hm_gate_times=np.s_[10:]),
                "magnetic_system": rd["magnetic_system"]}

pd_ = data_container.gs.add(key='processed_data',
                            data=join(DATA, 'skytem_processed_data.csv'),
                            metadata_file=join(PREPARED, 'skytem_processed_data.yml'),
                            system=proc_systems)
print("processed_data ok", dict(pd_.sizes))

# ------------------------------------------------------------------- models
model_container = survey.gs.add_container(
    'models', **dict(content="Inverted models"))

mods = model_container.gs.add(key='inverted_models',
                              data=join(DATA, 'skytem_inverted_models.csv'),
                              metadata_file=join(PREPARED, 'skytem_inverted_models.yml'))
print("inverted_models ok", dict(mods.sizes))

# -------------------------------------------------------- derivative products
bedrock = data_container.gs.add(key='depth_to_bedrock',
                                data=join(DATA, 'top_dolomite_blocky_lidar.csv'),
                                metadata_file=join(PREPARED, 'bedrock_picks.yml'))
print("depth_to_bedrock ok", dict(bedrock.sizes))

derived_maps = survey.gs.add_container(
    'derived_maps', **dict(content="raster products derived from airborne data and models"))

maps = derived_maps.gs.add(key='maps',
                           metadata_file=join(PREPARED, 'magnetics_bedrock_picks.yml'))
print("maps ok", dict(maps.sizes))

# -------------------------------------------------------------------- netcdf
out = join(SCRATCH, 'skytem_workshop.nc')
survey.gs.to_netcdf(out)
print("\nwrote", out)

new_survey = gspy.open_datatree(out)['survey']
print(new_survey.gs.tree)

# ---------------------------------------------------------------- inspection
print("\n== Inspecting metadata ==")
raw = new_survey['data']['raw_data']
print("dataset attrs:", list(raw.attrs)[:8])
print("height attrs:", raw['height'].attrs)
print("all units:", list(new_survey.gs.get_all_attr('units'))[:5])

# ------------------------------------------------------------------ plotting
plt.figure()
new_survey['data']['raw_data']['height'].plot()
plt.figure()
new_survey['data']['processed_data']['tx_altitude'].plot()
plt.figure()
new_survey['derived_maps']['maps']['magnetic_tmi'].plot(cmap='jet')
plt.close('all')
print("\nplots ok")
print("\nALL SKYTEM STEPS PASSED")
