# GSPy workshop

Two hands-on notebooks that build GS-format NetCDF files from raw airborne
geophysical data, starting from the position participants usually find
themselves in: a folder of numbers with no documentation at all.

- **[1_skytem_from_scratch.ipynb](1_skytem_from_scratch.ipynb)** - a SkyTEM AEM
  survey in CSV. 80 minutes. Generate metadata templates from nothing, fill them
  in, hit the errors GSPy raises when something important is missing, then build
  the whole survey and read the metadata back out.
- **[2_tempest_aseg.ipynb](2_tempest_aseg.ipynb)** - a Tempest AEM survey in
  ASEG-GDF2. 40 minutes. The same workflow on a format that carries its own
  column definitions, so most of the variable metadata arrives for free.

Do notebook 1 first; notebook 2 assumes it.

## Setup

If you already have a working `gspy` environment, use it:

```
conda activate gspy
jupyter lab
```

Otherwise:

You will need to install miniforge before creating a new conda environment. You can get the installer here
https://conda-forge.org/download/

```
conda env create -f environment.yml
conda activate gspy_workshop
jupyter lab
```

**Launch Jupyter from this folder.** Every path in the notebooks is relative to
the workshop root, so make sure you start jupyter in the root folder.

Check your setup before the workshop starts by running the first two cells of
notebook 1. If the `assert Path(DATA).is_dir()` line passes, you are ready.

## Layout

| | |
|---|---|
| `data/skytem/`, `data/tempest/` | the raw data, and **nothing else** - no metadata, by design |
| `prepared_metadata/` | completed metadata files, revealed part way through each notebook |
| `my_metadata/` | your scratch folder; everything you generate lands here |
| `solutions/` | both notebooks fully worked, with output |
| `tools/` | the scripts that built this folder (see below) |

The data has been trimmed to keep the folder small.

## Agenda

| Time | Notebook 1 |
|---|---|
| 5 min | What is in the box? |
| 15 min | Survey metadata from nothing |
| 25 min | Variable metadata from nothing |
| 10 min | Prepared metadata, and why systems exist |
| 10 min | Attaching the rest of the survey |
| 10 min | Save, reopen, and check the metadata |
| 5 min | Plotting |

| Time | Notebook 2 |
|---|---|
| 5 min | What is in the box? |
| 10 min | A template that fills itself in |
| 8 min | Survey and raw data |
| 7 min | Models derived from data |
| 5 min | A raster map |
| 5 min | Save, reopen, inspect |

Around two hours with breaks and discussion; comfortably 90 minutes if you skip
the discussion exercises.

## Exercises

Cells marked `EXERCISE` contain `...` placeholders to replace. They raise an
error if you run them unmodified, which is deliberate - it means you cannot skip
one by accident.

Several exercises are *designed to fail even when you get them right*, because
the error message is the lesson. Notebook 1 sections 2 and 3 both work this way.
Read the error rather than trying to make it go away.

Discussion exercises have no code cell. Type your answer into the markdown cell.

## Notes for maintainers

Both notebooks are generated, so do not edit the `.ipynb` files directly:

```
python tools/build_notebooks.py    # writes all four notebooks from one source
python tools/run_solutions.py      # executes both solutions notebooks end to end
```

`tools/build_notebooks.py` declares every cell once with an optional exercise
variant, which is what keeps an exercise notebook and its solutions from
drifting apart. `tools/run_solutions.py` is the test for this repository - if it
passes, every cell in both solution paths still runs against the installed gspy.

`tools/prepare_data.py` rebuilds `data/` and `prepared_metadata/` from a gspy
checkout, trimming the files on the way:

```
python tools/prepare_data.py /path/to/gspy
```

It also repoints the `files:` entries in the raster metadata, because GSPy
resolves those relative to the metadata file's own directory and this workshop
deliberately keeps metadata and data apart.

`tools/verify_skytem.py` and `tools/verify_tempest.py` walk the same two
pipelines without a Jupyter kernel. They are quicker than executing the
notebooks and give a cleaner traceback, so they are the faster way to check
whether a gspy change has broken the material.

## Data sources

Minsley, B.J., and others, 2022, Airborne electromagnetic and magnetic survey
data, northeast Wisconsin (ver. 1.1, June 2022): U.S. Geological Survey data
release, https://doi.org/10.5066/P93SY9LI

Minsley, B.J., James, S.R., Bedrosian, P.A., Pace, M.D., Hoogenboom, B.E., and
Burton, B.L., 2021, Airborne electromagnetic, magnetic, and radiometric survey
of the Mississippi Alluvial Plain, November 2019 - March 2020: U.S. Geological
Survey data release, https://doi.org/10.5066/P9E44CTQ

GSPy documentation: https://doi-usgs.github.io/gspy
