"""
Systems (YAML, GA-AEM .stm, templates)
--------------------------------------

Where a system definition comes from.

A GSPy ``System`` says what recorded the data: the transmitters, the receivers, the
couplets pairing them, and the gate times or frequencies the data is sampled at.
There are three ways to get one, and this example works through all of them:

1. **From a YAML file** you have already written - :meth:`System.open`.
2. **From a GA-AEM ``.stm`` file**, the system file GALEISBSTDEM forward models
   with - :meth:`System.from_stm`. Both flavours are read: the ``System Begin``
   block a time domain system is written as, and the table of coil pairs a
   frequency domain system is written as.
3. **From a template** for the method family, to fill in by hand -
   :meth:`System.metadata_template`.

The three mix. A ``.stm`` is a forward modelling file rather than a system
description, so it answers what it can and the rest is left as template
placeholders reading ``?? what goes here ??`` - hand it a YAML alongside, or dump
what it knows to a template and finish the job by hand.

"""
#%%
from os.path import join

import matplotlib.pyplot as plt
import numpy as np

from gspy import Survey, System

system_path = join('..', 'data_files', 'systems')


def placeholders(system):
    """The fields nothing has answered yet."""
    return [name for name in system.data_vars if '??' in str(system[name].values)]


#%%
# A system is described per method family
# +++++++++++++++++++++++++++++++++++++++
#
# Each family names the fields that method uses. This is the vocabulary every
# route below ends up speaking, whichever file it started from.

print(System.templates())

#%%
# From a YAML file
# ++++++++++++++++
#
# The ordinary case: a file holding one system, under a key with "system" in it.

resolve = System.open(join(system_path, 'Resolve_system.yml'))
print(resolve)

#%%
# A file written for a dataset often holds several systems - the electromagnetic
# system and the magnetometer that flew with it. Name the one you want.

skytem_md = join('..', 'data_files', 'skytem_csv', 'data', 'skytem_system.yml')
magnetometer = System.open(skytem_md, name='magnetic_system')
print(magnetometer['receiver_label'].values)

#%%
# From a GA-AEM .stm file, frequency domain
# ++++++++++++++++++++++++++++++++++++++++
#
# A frequency domain ``.stm`` is a table with a row per coil pair: the frequency,
# then the orientation, moment and position of the transmitting and receiving
# dipole.
#
# .. literalinclude:: /../../examples/data_files/systems/Resolve.stm
#    :language: text
#    :linenos:
#    :caption: Resolve.stm
#

resolve_stm = System.from_stm(join(system_path, 'Resolve.stm'))

#%%
# The coil labels come from the frequency and orientation of each pair, the
# frequencies become the ``frequency`` dimension, and the separations are the
# receiver position less the transmitter position.

print(resolve_stm['transmitter_label'].values)
print(resolve_stm['frequency'].values)
print(resolve_stm['couplet_txrx_dx'].values)

#%%
# Coplanar or coaxial is worked out from the pair of orientations.

print(resolve_stm['couplet_orientation'].values)

#%%
# From a GA-AEM .stm file, time domain
# ++++++++++++++++++++++++++++++++++++
#
# A time domain ``.stm`` is a nest of ``Name Begin`` ... ``Name End`` blocks. The
# waveform and the gate times are tables of unkeyed numbers inside them.
#
# .. literalinclude:: /../../examples/data_files/systems/Tempest.stm
#    :language: text
#    :linenos:
#    :caption: Tempest.stm
#

tempest_stm = System.from_stm(join(system_path, 'Tempest.stm'))

#%%
# The gate times arrive as bounds, because that is what the file states, and the
# centres are their midpoints. Which receivers there are is read from the
# components the file scales its output by, at the bottom of the file.

print(tempest_stm['gate_times'].values[:4])
print(tempest_stm['receiver_label'].values)
print(tempest_stm['couplet_label'].values)

#%%
# Several .stm files, one dual moment system
# ++++++++++++++++++++++++++++++++++++++++++
#
# GA-AEM writes a moment per file, so a dual moment system is two files. Give
# them as ``{transmitter label: file}`` and they become the two transmitters of
# one system, in the order given.

moments = {'LM': join(system_path, 'SkytemLM.stm'),
           'HM': join(system_path, 'SkytemHM.stm')}
skytem_stm = System.from_stm(moments)

#%%
# These two files only scale their output by z, so one receiving coil is what is
# read from them. If the aircraft carried a coil the forward model did not use,
# say so - the extra coil's fields become placeholders to fill in.

print(skytem_stm['receiver_label'].values)
print(System.from_stm(moments, receivers=['z', 'x'])['couplet_label'].values)

#%%
# Each moment brings its own gate times, named after the transmitter they belong
# to, and the couplets point at the right ones.

print([d for d in skytem_stm.sizes if 'gate_times' in d])
print(skytem_stm['couplet_gate_times'].values)

#%%
# The two waveforms are interpolated onto one shared time axis, since
# ``waveform_current`` is stated per transmitter over a common ``waveform_time``.
# A transmitter reads as zero outside its own span.

fig, ax = plt.subplots(2, 1, figsize=(9, 7))

for i, label in enumerate(skytem_stm['transmitter_label'].values):
    ax[0].plot(skytem_stm['waveform_time'].values,
               skytem_stm['transmitter_waveform_current'].values[i, :],
               marker='.', label=label)
ax[0].set(xlabel='time (s)', ylabel='normalised current',
          title='SkyTEM waveforms, read from two .stm files')
ax[0].legend()

for label, dimension in zip(skytem_stm['transmitter_label'].values,
                            ['lm_gate_times', 'hm_gate_times']):
    gates = skytem_stm[dimension].values
    ax[1].semilogx(gates, np.full(gates.size, label), marker='|', linestyle='none')
ax[1].set(xlabel='gate time (s)', title='Gate times, per moment')

plt.tight_layout()

#%%
# What a .stm cannot say
# ++++++++++++++++++++++
#
# Plenty. The format describes an airborne dipole for a forward model, so the
# mode is airborne and there is no loop geometry to ask for, but nothing in it
# says what instrument flew, how many transients were stacked, or what the
# receiver coils were.

print(placeholders(tempest_stm))

#%%
# GA-AEM also normalises the loop away, writing one turn of one square metre
# carrying one amp with the data scaled to match. Importing that would claim a
# 1 m^2 single turn loop, so it is flagged instead and the loop left placeheld.

print(tempest_stm['data_normalized'].values)

#%%
# Nothing read is thrown away, though. Anything in the file that GSPy has no
# field for is kept in the attributes under ``stm_``, the normalised loop
# included, so the file can be reconstructed from the system.

for key, value in tempest_stm.attrs.items():
    if key.startswith('stm_'):
        print(f"{key}: {value}")

#%%
# Dump what the file knows, fill in the rest by hand
# +++++++++++++++++++++++++++++++++++++++++++++++++
#
# :meth:`System.metadata_from_stm` gives the metadata rather than the built
# system, so it can be written out as a template: the imported values are real,
# and what the file could not say is still a placeholder to answer.

metadata = System.metadata_from_stm(join(system_path, 'Tempest.stm'))
metadata.dump("template_md_stm_tempest.yml")

#%%
#
# .. literalinclude:: /../../examples/Creating_GS_Files/template_md_stm_tempest.yml
#    :language: yaml
#    :linenos:
#    :caption: Tempest.stm written out as a system template
#

#%%
# Filled in, it reads straight back.

print(System.open("template_md_stm_tempest.yml").attrs['method'])

#%%
# A .stm and a YAML together
# ++++++++++++++++++++++++++
#
# The other way round: keep a small YAML holding only what the file cannot say,
# and let the ``.stm`` supply the waveform, the gate times and the geometry.
#
# .. literalinclude:: /../../examples/data_files/systems/Tempest_stm_extras.yml
#    :language: yaml
#    :linenos:
#    :caption: Tempest_stm_extras.yml
#

tempest = System.from_stm(join(system_path, 'Tempest.stm'),
                          metadata=join(system_path, 'Tempest_stm_extras.yml'))

#%%
# The YAML wins wherever the two overlap, so it can correct the file as well as
# add to it - here it puts the real loop back over the normalised one.

print(tempest.attrs['instrument'])
print(tempest['transmitter_area'].values, tempest['transmitter_peak_current'].values)
print(tempest['couplet_txrx_dz'].values)

#%%
# What is left placeheld is what neither source knows. Answer those, or delete
# the fields this system does not have, and the definition is finished.

print(placeholders(tempest))

#%%
# From a template alone
# +++++++++++++++++++++
#
# With no file to start from, ask for the family and the shape. See
# :ref:`sphx_glr_examples_Creating_GS_Files_plot_help_I_have_no_variable_metadata.py`
# for more on templates.

template = System.metadata_template('tdem', name='skytem_system',
                                    transmitters=['LM', 'HM'], receivers=['z', 'x'])
print(list(template['skytem_system']['dimensions']))

#%%
# Attaching one to the data it recorded
# +++++++++++++++++++++++++++++++++++++
#
# Whichever route built it, a system is handed to the dataset it recorded as that
# dataset is added. :meth:`System.metadata_from_stm` returns the metadata under
# its own name, which is the shape ``system`` expects.
#
# The labels matter here. A variable in the data file points at the couplet that
# measured it by name, so label the transmitter the way the data file writes it -
# a bare ``.stm`` does not name its own transmitter, and would be indexed
# ``transmitter_1`` instead.

tempest_path = join('..', 'data_files', 'tempest_aseg', 'data')

survey = Survey.from_dict(join(tempest_path, 'Tempest_survey_md.yml'))
container = survey.gs.add_container('data', **dict(content='raw data'))
raw = container.gs.add(key='raw_data',
                       data=join(tempest_path, 'Tempest.dat'),
                       metadata_file=join(tempest_path, 'Tempest_data_md.yml'),
                       system=System.metadata_from_stm(
                           {'z': join(system_path, 'Tempest.stm')},
                           name='tempest_system',
                           metadata=join(system_path, 'Tempest_stm_extras.yml')))

#%%
# Which is what the ``system_couplet`` of each electromagnetic variable is checked
# against.

print(raw['tempest_system']['couplet_label'].values)
print({name: raw.dataset[name].attrs['system_couplet']
       for name in ('emx_nonhprg', 'emz_nonhprg')})

plt.show()
