"""Generate the workshop notebooks and their solution counterparts.

Every cell is declared once, with an optional exercise variant.  Emitting both
notebooks from one source is the only reliable way to keep an exercise notebook
and its solutions from drifting apart as the material gets edited.

Usage
-----
    python tools/build_notebooks.py

Writes
------
    1_skytem_from_scratch.ipynb
    2_tempest_aseg.ipynb
    solutions/1_skytem_from_scratch_solutions.ipynb
    solutions/2_tempest_aseg_solutions.ipynb

"""
from pathlib import Path
from textwrap import dedent

import nbformat as nbf

HERE = Path(__file__).resolve().parent.parent

KERNELSPEC = {'display_name': 'Python 3 (gspy)',
              'language': 'python',
              'name': 'python3'}


class Notebook:
    """Collects cells, then emits an exercise and a solutions notebook."""

    def __init__(self):
        self._cells = []

    @staticmethod
    def _check_indent(text):
        """Reject cell text holding a line that starts at column zero.

        Every cell below is written inside an indented triple quoted block, so a
        flush left line can only have come from an escape expanding while this file
        was read - a bare ``\\n`` inside a print, usually.  It is worth catching
        because of what it does downstream: ``dedent`` looks for a common prefix,
        that one line gives it an empty one, and so nothing is stripped from any
        line.  The cell then lands in the notebook indented by eight spaces, and
        every line of it after the first raises IndentationError.
        """
        for number, line in enumerate(text.splitlines(), start=1):
            if line and not line[0].isspace():
                raise ValueError(
                    f"cell text line {number} starts at column zero:\n"
                    f"    {line}\n"
                    "dedent cannot strip a common prefix past that, so the whole "
                    "cell would arrive indented.  For a newline inside a string, "
                    "write a doubled backslash-n rather than a single one.")

    def md(self, text, exercise=None):
        """A markdown cell.  ``exercise`` overrides the text in the exercise
        notebook, for prompts that would give the answer away in reverse."""
        self._check_indent(text)
        if exercise is not None:
            self._check_indent(exercise)
        self._cells.append(('markdown', dedent(text).strip(), dedent(exercise).strip()
                            if exercise is not None else None))
        return self

    def code(self, solution, exercise=None):
        """A code cell.  ``exercise`` is the blanked version; when omitted the
        same code appears in both notebooks."""
        self._check_indent(solution)
        if exercise is not None:
            self._check_indent(exercise)
        self._cells.append(('code', dedent(solution).strip(), dedent(exercise).strip()
                            if exercise is not None else None))
        return self

    def _build(self, which):
        notebook = nbf.v4.new_notebook()
        notebook.metadata['kernelspec'] = KERNELSPEC
        for kind, solution, exercise in self._cells:
            source = solution if (which == 'solution' or exercise is None) else exercise
            # Expanded after dedent, because a multi line banner at column zero
            # would leave dedent with no common prefix to strip.
            source = source.replace(BANNER_TOKEN, EXERCISE_BANNER)
            if kind == 'markdown':
                notebook.cells.append(nbf.v4.new_markdown_cell(source))
            else:
                # A cell that does not parse is a cell nobody can complete, and an
                # exercise blank is still syntactically whole, so every code cell in
                # both notebooks has to compile.
                index = len(notebook.cells)
                try:
                    compile(source, f'{which} cell {index}', 'exec')
                except SyntaxError as error:
                    raise ValueError(f"{which} cell {index} does not parse: "
                                     f"{error.msg} on line {error.lineno}\n\n"
                                     f"{source}") from None
                notebook.cells.append(nbf.v4.new_code_cell(source))
        return notebook

    def write(self, exercise_path, solution_path):
        for path, which in ((exercise_path, 'exercise'), (solution_path, 'solution')):
            path.parent.mkdir(parents=True, exist_ok=True)
            nbf.write(self._build(which), str(path))
            print(f"wrote {path.relative_to(HERE)}")


BANNER_TOKEN = '#EXERCISE#'
EXERCISE_BANNER = ("# " + "-" * 68
                   + "\n# EXERCISE - complete the lines marked with ..."
                   + "\n# " + "-" * 68)


# ===========================================================================
#  Notebook 1 - SkyTEM CSV, from no metadata at all
# ===========================================================================

def build_skytem():
    nb = Notebook()

    nb.md("""
        # Building a GS file from scratch

        ## A GSPy workshop

        You have been handed a folder of airborne geophysical data from a survey in
        northeast Wisconsin. There is no documentation. There are no units. There is
        nothing telling you what the columns mean or what coordinate system the
        data are in.

        By the end of this notebook you will have turned that folder into a single,
        self-describing NetCDF file that a colleague could pick up in ten years and
        still understand.

        | | Section | Time |
        |---|---|---|
        | 1 | What is in the box? | 5 min |
        | 2 | Survey metadata from nothing | 15 min |
        | 3 | Variable metadata from nothing | 25 min |
        | 4 | Prepared metadata, and why systems exist | 10 min |
        | 5 | Attaching the rest of the survey | 10 min |
        | 6 | Save, reopen, and check the metadata | 10 min |
        | 7 | Plotting | 5 min |

        **Before you start:** activate the environment and launch Jupyter from the
        workshop root folder, so that the relative paths below resolve.

        ```
        conda activate gspy
        jupyter lab
        ```

        Cells marked **EXERCISE** contain `...` placeholders that you need to
        replace. They will raise an error if you run them unchanged - that is
        deliberate. The completed notebook lives in `solutions/`.

        *Source data: Minsley, B.J, and others, 2022, Airborne electromagnetic and
        magnetic survey data, northeast Wisconsin (ver. 1.1, June 2022): U.S.
        Geological Survey data release, https://doi.org/10.5066/P93SY9LI*
        """)

    nb.code("""
        import warnings
        from os.path import join
        from pathlib import Path

        import matplotlib.pyplot as plt
        import numpy as np
        import pandas as pd
        import xarray as xr

        import gspy
        from gspy import Dataset, Metadata, Survey

        warnings.filterwarnings('ignore')

        DATA = 'data/skytem'            # the data we were handed
        PREPARED = 'prepared_metadata/skytem'   # metadata prepared earlier, used from section 4
        SCRATCH = 'my_metadata'         # everything you generate goes here

        Path(SCRATCH).mkdir(exist_ok=True)

        print('gspy     ', gspy.__version__)
        print('xarray   ', xr.__version__)
        assert Path(DATA).is_dir(), 'Run Jupyter from the workshop root folder'
        """)

    # ---------------------------------------------------------------- section 1
    nb.md("""
        ---
        ---
        ## 1. What is in the box?

        Start by looking at what files you actually have.
        """)

    nb.code("""
        for path in sorted(Path(DATA).iterdir()):
            print(f'{path.name:<38} {path.stat().st_size / 1e6:>6.1f} MB')
        """)

    nb.md("""
        Four CSV files and four GeoTIFFs. No `.yml`, no `.json`, no readme, no data
        dictionary. There is no accompanying metadata with these files.

        ---
        ### Exercise 1.1

        Have a look inside the raw AEM data file. How many rows and columns are
        there, and what are the columns called?

        *Hint: `pandas.read_csv`, then `.shape` and `.columns`.*
        """)

    nb.code(f"""
        #EXERCISE#
        raw_csv = join(DATA, 'skytem_contractor_data.csv')

        df = pd.read_csv(raw_csv)

        print(df.shape)
        print(list(df.columns))
        """,
        f"""
        #EXERCISE#
        raw_csv = join(DATA, 'skytem_contractor_data.csv')

        df = ...      # read the file

        print(df.shape)
        print(list(df.columns))
        """)

    nb.md("""
        Now ask yourself:

        - What are the units of `Alt`? Is it metres or feet?
        - `Alt`, `Height` and `DEM` are three different vertical coordinate data. Which is
          height above ground, which is elevation above a datum, and which datum?
        - `E_Nad83` and `N_Nad83` are eastings and northings in *some* projection.
          Which one?
        - What does `-9999.99` mean, and which columns use it?
        - There are 31 columns starting `HM_X[`. What is the second dimension, and
          what are its values?

        Nothing in the file answers any of these. This is the problem a GS file
        solves: the answers travel *with* the data, in a format software can read.
        """)

    # ---------------------------------------------------------------- section 2
    nb.md("""
        ---
        ---
        ## 2. Survey metadata from nothing

        GSPy metadata lives at four levels:

        - **Survey** - facts about the whole survey: who flew it, when, where, in
          what coordinate reference system, with what instruments.
        - **Container** - Groups of datasets
        - **Dataset** - facts about one table or raster of numbers, right down to
          each individual variable.
        - **Supplementary** - System information, inversion parameters.

        You do not have to write either from memory. `metadata_template()` inspects
        what you have and writes out a skeleton for you to fill in. Start with the
        survey, which needs no data file at all.
        """)

    nb.code("""
        template = Survey.metadata_template()
        template.dump(join(SCRATCH, 'survey_template.yml'))

        print(Path(SCRATCH, 'survey_template.yml').read_text())
        """)

    nb.md("""
        Every `??` is a question GSPy is asking you. Open
        `my_metadata/survey_template.yml` in your editor and have a look - in real
        work this is the file you would fill in and keep under version control
        alongside the data.

        ---
        ### Exercise 2.1

        What do you think happens if we hand that template straight back to GSPy
        without filling anything in?
        """)

    nb.code("""
        try:
            survey = Survey.from_dict(join(SCRATCH, 'survey_template.yml'))
            print('It worked, which is suspicious')
        except Exception as e:
            print(f'{type(e).__name__}: {e}')
        """)

    nb.md("""
        > `CRSError: Invalid projection: ??:??`

        It fails on the coordinate reference system, and you can see the two `??`
        placeholders it choked on. GSPy will not build a survey that cannot say where
        on Earth it is.

        ---
        ### Exercise 2.2

        Fill in the minimum needed to build a survey. Two things are required: `wkid` and `authority` under `spatial_ref`.

        What you know about this survey:

        - it was flown over **northeast Wisconsin**, and the positions are
          **Wisconsin Transverse Mercator, NAD83**, which is **EPSG:3071**
        - elevations are referenced to **NAVD88**
        - it was flown by **SkyTEM Canada Inc** for the **U.S. Geological Survey**
          between **2021-01-17** and **2021-02-07**

        Note the pattern below: you pass what you know to `metadata_template()`, and
        it merges your entries over the skeleton. Anything you leave out comes back
        as `??`, so the template doubles as a to-do list.

        *Hint: `wkid` is a number, `authority` is a string.
        """)

    nb.code(f"""
        #EXERCISE#
        known = {{
            'dataset_attrs': {{
                'title': 'SkyTEM AEM Survey, Northeast Wisconsin Bedrock Mapping',
                'institution': 'USGS Geology, Geophysics, and Geochemistry Science Center',
            }},
            'spatial_ref': {{
                'wkid': 3071,
                'authority': 'EPSG',
                'vertical_crs': 'NAVD88',
            }},
            'survey_information': {{
                'contractor': 'SkyTEM Canada Inc',
                'client': 'U.S. Geological Survey',
                'survey_type': 'EM/Mag',
                'acquisition_start': 20210117,
                'acquisition_end': 20210207,
            }},
        }}

        template = Survey.metadata_template(known)
        template.dump(join(SCRATCH, 'survey_filled.yml'))

        my_survey = Survey.from_dict(template)
        my_survey
        """,
        f"""
        #EXERCISE#
        known = {{
            'dataset_attrs': {{
                'title': ...,
                'institution': ...,
            }},
            'spatial_ref': {{
                'wkid': ...,
                'authority': ...,
                'vertical_crs': ...,
            }},
            'survey_information': {{
                'contractor': ...,
                'client': ...,
                'survey_type': 'EM/Mag',
                'acquisition_start': ...,   # yyyymmdd, as a number
                'acquisition_end': ...,
            }},
        }}

        template = Survey.metadata_template(known)
        template.dump(join(SCRATCH, 'survey_filled.yml'))

        my_survey = Survey.from_dict(template)
        my_survey
        """)

    nb.code("""
        # A check you can run: did the required entries actually get filled in?

        assert my_survey.attrs['title'] != '??', 'title is still a placeholder'
        assert 'spatial_ref' in my_survey.coords, 'no spatial reference was attached'

        print('Survey built with CRS:', my_survey['spatial_ref'].attrs.get('spatial_ref', 'see attrs'))
        print('\\nAttributes GSPy kept:')

        for key, value in my_survey.attrs.items():
            print(f'  {key:<14} {str(value)[:70]}')
        """)

    nb.md("""
        Notice that the entries you left as `??` were carried through rather than
        silently dropped.
        """)

    # ---------------------------------------------------------------- section 3
    nb.md("""
        ---
        ---
        ## 3. Variable metadata from nothing

        Now the tedious part, and the part GSPy helps with most. The raw CSV has 34
        distinct variables and every one of them needs a name, a long name, units
        and a no-data value.

        Pass the data file to `Dataset.metadata_template()` and it reads the header
        for you, so the skeleton already knows what your variables are called.
        """)

    nb.code("""
        template = Dataset.metadata_template(join(DATA, 'skytem_contractor_data.csv'))
        template.dump(join(SCRATCH, 'raw_data_template.yml'))

        print(f"{len(template['variables'])} variables found\\n")

        print(list(template['variables']))

        for name in list(template['variables'])[:6]:
            print(f'{name}:')

            for key, value in template['variables'][name].items():
                print(f'    {key}: {value}')
        """)

    nb.md("""
        Every field is `not_defined`. A CSV header gives GSPy the *names* of your
        variables and nothing else - it cannot guess that `Alt` is in metres.

        Keep that in mind for section 2 of the tempest notebook, where the same call
        on an ASEG-GDF file comes back mostly filled in, because that format carries
        its own column definitions.

        The template has a second block worth looking at before we start filling
        things in. It shows how we can define dimensions in the data like the number of gate times or layer depths.
        """)

    nb.code("""
        for name, entry in template['dimensions'].items():
            print(f'{name}:')
            print(f"    {entry['long_name'][:100]}")
        """)

    nb.md("""
        Those two are not real dimensions - they are worked examples, showing the two
        ways you can declare a dimension by hand: by `length`/`increment`/`origin`
        for a regular axis, or by explicit `bounds` and `centers` for an irregular
        one. Remember that they exist; we will come back to them shortly.

        ---
        ### Exercise 3.1

        Fill in the dataset attributes and say which variables are the coordinates.

        Look back at the column list from exercise 1.1 and decide which column is
        the x coordinate, which is y, which is the vertical coordinate, and which is
        time. Then run the cell - it will not work yet, and the error message is the
        point of the exercise.

        *Hint: the eastings and northings are named after their datum. `DEM` is a
        ground elevation. `DateTime` is a date and time.*
        """)

    nb.code(f"""
        #EXERCISE#
        template['dataset_attrs'] = {{
            'content': 'raw data',
            'comment': 'Minimally processed AEM and magnetic data provided by SkyTEM',
            'type': 'data',
            'structure': 'tabular',
            'mode': 'airborne',
            'method': 'electromagnetic, time domain',
            'instrument': 'skytem',
        }}

        template['coordinates'] = {{
            'x': 'E_Nad83',
            'y': 'N_Nad83',
            'z': 'DEM',
            't': 'DateTime',
        }}

        # The report below shows an error rather than raising it, so check here that
        # there is nothing left unanswered - otherwise a blank would look like a pass

        assert Ellipsis not in template['dataset_attrs'].values(), 'fill in every attribute'
        assert Ellipsis not in template['coordinates'].values(), 'name all four coordinates'


        # A container to hang datasets from, then try to attach the raw data
        data_container = my_survey.gs.add_container('data', content='raw and processed data')

        try:
            data_container.gs.add(key='raw_data',
                                  data=join(DATA, 'skytem_contractor_data.csv'),
                                  metadata_file=template)
        except Exception as e:
            print(f'{{type(e).__name__}}: {{e}}')

        template['dimensions'] = {{}} # Workshop specific for teaching only

        """,
        f"""
        #EXERCISE#
        template['dataset_attrs'] = {{
            'content': ...,        # a one line summary of what this dataset holds
            'comment': ...,
            'type': ...,           # 'data' or 'models'
            'structure': 'tabular',
            'mode': ...,           # ground, airborne, borehole ...
            'method': ...,         # what geophysical method is this?
            'instrument': ...,
        }}

        template['coordinates'] = {{
            'x': ...,
            'y': ...,
            'z': ...,
            't': ...,
        }}

        # The report below shows an error rather than raising it, so check here that
        # there is nothing left unanswered - otherwise a blank would look like a pass

        assert Ellipsis not in template['dataset_attrs'].values(), 'fill in every attribute'
        assert Ellipsis not in template['coordinates'].values(), 'name all four coordinates'


        # A container to hang datasets from, then try to attach the raw data
        data_container = my_survey.gs.add_container('data', content='raw and processed data')

        try:
            data_container.gs.add(key='raw_data',
                                  data=join(DATA, 'skytem_contractor_data.csv'),
                                  metadata_file=template)
        except Exception as e:
            print(f'{{type(e).__name__}}: {{e}}')

        template['dimensions'] = {{}} # Workshop specific for teaching only
        """)

    nb.md("""
        > `z coordinate definition requires entries positive: up or down, and datum`

        GSPy is refusing to accept a vertical coordinate that does not say which way
        is up. "Elevation 300" is meaningless without knowing whether it is measured
        upwards from a datum or downwards from the surface, and from which datum.
        This is exactly the ambiguity you saw in section 1 with `Alt`, `Height`
        and `DEM`.

        ---
        ### Exercise 3.2

        Fill in the four coordinate variables properly, and three ordinary variables
        by hand so you can feel what the full job is like.

        What you know:

        - eastings and northings are in **metres**
        - `DEM` is a ground elevation in metres, measured **up** from **NAVD88**
        - `DateTime` is a date, with units **days since 1900-01-01**
        - `Height` is instrument height above ground, in metres
        - `Base_Mag` is the base station magnetic field, in **nT**, and uses
          **-9999.99** where there is no reading
        """)

    nb.code(f"""
        #EXERCISE#
        variables = template['variables']

        variables['E_Nad83'].update(
            standard_name='easting_nad83',
            long_name='Easting, Wisconsin Transverse Mercator, NAD83',
            units='meter',
            axis='X')

        variables['N_Nad83'].update(
            standard_name='northing_nad83',
            long_name='Northing, Wisconsin Transverse Mercator, NAD83',
            units='meter',
            axis='Y')

        variables['DEM'].update(
            standard_name='ground_elevation',
            long_name='Ground surface elevation from a digital elevation model',
            units='meter',
            positive='up',
            datum='NAVD88')

        variables['DateTime'].update(
            standard_name='datetime',
            long_name='Date and time of the measurement',
            units='days since 1900-01-01',
            datum='1900-01-01')

        variables['Height'].update(
            standard_name='instrument_height',
            long_name='Instrument height above ground',
            units='meter')

        variables['Base_Mag'].update(
            standard_name='base_station_magnetic_field',
            long_name='Total magnetic field measured at the base station',
            units='nT',
            missing_value=-9999.99)

        for name in ('E_Nad83', 'DEM', 'Base_Mag'):
            print(name, '->', dict(variables[name]))
        """,
        f"""
        #EXERCISE#
        variables = template['variables']

        variables['E_Nad83'].update(
            standard_name=...,
            long_name=...,
            units=...,
            axis='X')

        variables['N_Nad83'].update(
            standard_name=...,
            long_name=...,
            units=...,
            axis='Y')

        variables['DEM'].update(
            standard_name=...,
            long_name=...,
            units=...,
            positive=...,      # which way does the number increase?
            datum=...)

        variables['DateTime'].update(
            standard_name=...,
            long_name=...,
            units=...,         # 'days since ....-..-..'
            datum=...)

        variables['Height'].update(
            standard_name=...,
            long_name=...,
            units=...)

        variables['Base_Mag'].update(
            standard_name=...,
            long_name=...,
            units=...,
            missing_value=...)

        for name in ('E_Nad83', 'DEM', 'Base_Mag'):
            print(name, '->', dict(variables[name]))
        """)

    nb.md("""
            A quick check to make sure the placeholders where filled in.

            missing_value is allowed to stay not_defined -
            most of these variables genuinely have no no-data value -
            but nothing may be left as a placeholder.
            """)

    nb.code("""
        for name in ('E_Nad83', 'N_Nad83', 'DEM', 'DateTime', 'Height', 'Base_Mag'):
            for key, value in variables[name].items():
                assert value is not Ellipsis, f'{name}.{key} is still a placeholder'
            for key in ('standard_name', 'long_name', 'units'):
                assert variables[name][key] != 'not_defined', f'{name}.{key} is undefined'
        print('All six variables are described')
        """)

    nb.md("""
        ---
        ### Exercise 3.3

        Try again. A different error this time - read it carefully before moving on.
        """)

    nb.code("""
        try:
            data_container.gs.add(key='raw_data',
                                  data=join(DATA, 'skytem_contractor_data.csv'),
                                  metadata_file=template)
        except Exception as e:
            print(f'{type(e).__name__}: {e}')


        print("\\nwhat the template said about HM_X:\\n")

        print(template['variables']['HM_X'])
        """)

    nb.md("""
        > `Could not match dimensions for variable HM_X with metadata dimensions ['index', '??']`

        Look at where that `'??'` came from.

        When GSPy read the CSV header it found
        31 columns called `HM_X[0]` through `HM_X[30]`, and worked out that they are
        not 31 separate variables - they are **one** variable with a second
        dimension.

        It filled in `index` for you, because that is the record number,
        and left `??` for the dimension it cannot possibly know yet.
        """)

    nb.code("""
        hm_x_columns = [c for c in df.columns if c.startswith('HM_X[')]
        print(f'{len(hm_x_columns)} columns collapse into one 2-D variable:')
        print(hm_x_columns[:4], '...', hm_x_columns[-2:])
        """)

    nb.md("""
        ---
        ### Exercise 3.4 - discussion, no code

        The second dimension of `HM_X` is the receiver gate times: 31 time windows
        over which the decaying secondary field was measured.

        There are two ways to give GSPy that dimension. One is with a `dimensions:`
        block in the datasets metadata; write out the 31 gate times there and the
        `??` resolves.

        The other is to attach a **system**.

        Which is right depends on
        a question about the gate times themselves:

        - Are those gate times a property of *this data file*, or of the
          *instrument that produced it*?
        - The same instrument also flew the processed dataset, and the inverted
          models were derived from it. Where should the gate times be written down
          so that all three can refer to the same definition?
        - What else about the instrument would you need in order to invert this data
          properly - or to understand it in twenty years?

        *Your answer:*

        This is what GSPy calls a **system**: transmitter and receiver geometry,
        waveform, gate times, base frequencies, coil orientations. It lives in a file
        of its own, and every dataset acquired with that instrument points at it.

        Systems have templates too - one per method family, shaped to however many
        transmitters and receivers you tell it about.
        """)

    nb.code("""
        from gspy import System

        print('families with a template:', System.templates())

        skytem = System.metadata_template('tdem', name='skytem_system',
                                          transmitters=['LM', 'HM'],  # dual moment
                                          receivers=['z', 'x'])       # two coils

        skytem.dump(join(SCRATCH, 'skytem_system_template.yml'))

        print('\\ndimensions:', list(skytem['skytem_system']['dimensions']))
        print('\\nvariables :', list(skytem['skytem_system']['variables']))
        """)

    nb.md("""
        Two moments and two coils, so the template asks for `lm_gate_times` and
        `hm_gate_times` - the second dimension for `HM_X` was missing, named for you before you
        have written down a single number.

        Filling that skeleton in, though, is genuinely an afternoon with the
        contractor's report open:
        """)

    nb.code("""
        import json

        print(json.dumps(skytem, default=str).count('??'), 'placeholders to fill in')
        """)

    nb.md("""
        You have now done the from-scratch job by hand for six variables out of
        thirty-four, which is enough to know what it involves.

        From here on we use metadata prepared earlier.
        """)

    # ---------------------------------------------------------------- section 4
    nb.md("""
        ---
        ---
        ## 4. Prepared metadata, and why systems exist

        `prepared_metadata/skytem/` holds the completed files - the same ones you
        have been building towards.
        """)

    nb.code("""
        for path in sorted(Path(PREPARED).iterdir()):
            print(f'{path.name:<38} {path.stat().st_size / 1e3:>6.1f} kB')
        """)

    nb.md("""
        `skytem_system.yml` is the biggest, and it is the one that answers section 3.
        It holds two system definitions, one per instrument. Here is the start of the
        SkyTEM one - notice the gate times that `HM_X` was asking for.

        #### Open skytem_system.yml in jupyter lab and take a look
        """)


    nb.md("""

        #### Build the survey

        It is now purely descriptive - who flew it, where,
        in what CRS - with no instruments in it.
        """)

    nb.code("""
        survey = Survey.from_dict(join(PREPARED, 'skytem_survey.yml'))
        print(survey.gs.tree)

        survey
        """)

    nb.md("""
        Just `/survey`, no children yet. Datasets get attached to a container, and
        are told which systems they were acquired with.

        ---
        ### Exercise 4.1

        Let's add a container and some data to the survey.

        *Hint: `survey.gs.add_container(name, content=...)`, then
        `container.gs.add(key=..., data=..., metadata_file=..., system=...)`.*
        """)

    nb.code(f"""
        #EXERCISE#
        data_container = survey.gs.add_container(
            'data', content='raw and processed data')

        raw_data = data_container.gs.add(
            key='raw_data',
            data=join(DATA, 'skytem_contractor_data.csv'),
            metadata_file=join(PREPARED, 'skytem_contractor_data.yml'),
            system=join(PREPARED, 'skytem_system.yml'))

        print(dict(raw_data.sizes))
        print(raw_data.gs.tree)

        raw_data
        """,
        f"""
        #EXERCISE#
        data_container = survey.gs.add_container(
            'data', content='raw and processed data')

        raw_data = data_container.gs.add(
            key='raw_data',
            data=...,
            metadata_file=...,
            system=...)

        print(dict(raw_data.sizes))
        print(raw_data.gs.tree)

        raw_data
        """)

    nb.md("""
        `hm_gate_times: 32` and `lm_gate_times: 28`. The `??` from section 3 has
        been resolved by the system, and `HM_X` is now a genuine 2-D variable with a
        labelled time axis.

        Both systems were also attached below the dataset as their own groups, which
        is where you go to read them back - `raw_data['skytem_system']`.

        ---
        ### Exercise 4.2

        Now the processed data. During processing the first low moment gate and the
        first ten high moment gates were culled - they were too noisy to use. So the
        processed data has **27** low moment and **22** high moment gates.

        The system attached to a dataset has to describe *that* dataset. If you
        attach the full SkyTEM system to the processed data, you are claiming gate
        times that are not there.

        So take the system off the raw dataset, subset it with xarray's `isel` on the two gate
        time dimensions, and pass that.

        *Hint: `raw_data['skytem_system'].isel(lm_gate_times=np.s_[1:], hm_gate_times=np.s_[10:])`
        drops the first entry of one and the first ten of the other. The magnetic
        system is unchanged, so pass `raw_data['magnetic_system']` straight through.*
        """)

    nb.code(f"""
        #EXERCISE#
        processed_systems = {{
            'skytem_system': raw_data['skytem_system'].isel(lm_gate_times=np.s_[1:],
                                                            hm_gate_times=np.s_[10:]),
            'magnetic_system': raw_data['magnetic_system'],
        }}

        processed_data = data_container.gs.add(
            key='processed_data',
            data=join(DATA, 'skytem_processed_data.csv'),
            metadata_file=join(PREPARED, 'skytem_processed_data.yml'),
            system=processed_systems)

        print('raw      ', dict(raw_data.sizes))
        print('processed', dict(processed_data.sizes))

        processed_data
        """,
        f"""
        #EXERCISE#
        processed_systems = {{
            'skytem_system': raw_data['skytem_system'].isel(lm_gate_times=...,
                                                            hm_gate_times=...),
            'magnetic_system': ...,
        }}

        processed_data = data_container.gs.add(
            key='processed_data',
            data=join(DATA, 'skytem_processed_data.csv'),
            metadata_file=join(PREPARED, 'skytem_processed_data.yml'),
            system=processed_systems)

        print('raw      ', dict(raw_data.sizes))
        print('processed', dict(processed_data.sizes))

        processed_data
        """)

    nb.code("""
        assert processed_data.sizes['lm_gate_times'] == 27, 'expected 27 low moment gates'
        assert processed_data.sizes['hm_gate_times'] == 22, 'expected 22 high moment gates'
        print('The processed data and its system agree')
        """)

    # ---------------------------------------------------------------- section 5
    nb.md("""
        ---
        ---
        ## 5. Attaching the rest of the survey

        The point of a GS file is that the *whole* survey travels together: raw
        data, processed data, inverted models, and the products derived from them.
        Containers let you group them in whatever way makes sense for your survey.

        ---
        ### Exercise 5.1

        Inverted resistivity models belong in their own branch, because they are
        models rather than measurements. Create a `models` container and attach
        `skytem_inverted_models.csv` with `skytem_inverted_models.yml`.

        *Hint: same two calls as exercise 4.1, but no system is needed here.*
        """)

    nb.code(f"""
        #EXERCISE#
        model_container = survey.gs.add_container('models', content='Inverted models')

        models = model_container.gs.add(
            key='inverted_models',
            data=join(DATA, 'skytem_inverted_models.csv'),
            metadata_file=join(PREPARED, 'skytem_inverted_models.yml'))

        print(dict(models.sizes))

        models
        """,
        f"""
        #EXERCISE#
        model_container = survey.gs.add_container(..., content='Inverted models')

        models = model_container.gs.add(
            key=...,
            data=...,
            metadata_file=...)

        print(dict(models.sizes))

        models
        """)

    nb.md("""
        `layer_depth: 40` - each record is a 40 layer resistivity model. Its
        metadata file also carries an `inversion_parameters` block, which becomes a
        sub-group recording which software inverted the data and when.

        ---
        ### Exercise 5.2

        The depth-to-bedrock picks were derived from those models, but they are
        point observations, so they go on the `data` branch alongside the AEM data.
        Attach `top_dolomite_blocky_lidar.csv` with `bedrock_picks.yml` under the
        key `depth_to_bedrock`.
        """)

    nb.code(f"""
        #EXERCISE#
        bedrock = data_container.gs.add(
            key='depth_to_bedrock',
            data=join(DATA, 'top_dolomite_blocky_lidar.csv'),
            metadata_file=join(PREPARED, 'bedrock_picks.yml'))

        print(dict(bedrock.sizes))

        bedrock
        """,
        f"""
        #EXERCISE#
        bedrock = data_container.gs.add(
            key=...,
            data=...,
            metadata_file=...)

        print(dict(bedrock.sizes))

        bedrock
        """)

    nb.md("""
        ---
        ### Exercise 5.3

        Finally the interpolated grids. Rasters work slightly differently: there is
        no `data`, because the metadata file names the GeoTIFFs itself -
        one variable can even be built from a stack of files.

        Create a `derived_maps` container and add the maps using
        `magnetics_bedrock_picks.yml`.
        """)

    nb.code("""
        # Look at how a raster variable names its own file

        raster_yml = Path(PREPARED, 'magnetics_bedrock_picks.yml').read_text().splitlines()
        start = next(i for i, line in enumerate(raster_yml) if 'magnetic_tmi' in line)
        print('\\n'.join(raster_yml[start:start + 8]))
        """)

    nb.code(f"""
        #EXERCISE#
        derived_maps = survey.gs.add_container(
            'derived_maps',
            content='raster products derived from airborne data and models')

        maps = derived_maps.gs.add(
            key='maps',
            metadata_file=join(PREPARED, 'magnetics_bedrock_picks.yml'))

        print(dict(maps.sizes))

        maps
        """,
        f"""
        #EXERCISE#
        derived_maps = survey.gs.add_container(
            ...,
            content='raster products derived from airborne data and models')

        maps = derived_maps.gs.add(
            key=...,
            metadata_file=...)      # note: no data argument for rasters

        print(dict(maps.sizes))

        maps
        """)

    nb.code("""
        print(survey.gs.tree)
        """)

    nb.md("""
        Five datasets across three containers, with the instrument definitions
        attached to the datasets that used them. That is the whole survey.
        """)

    # ---------------------------------------------------------------- section 6
    nb.md("""
        ---
        ---
        ## 6. Save, reopen, and check the metadata

        Everything so far has been in memory. Write it to a single NetCDF file.
        """)

    nb.code("""
        out_file = join(SCRATCH, 'skytem_workshop.nc')
        survey.gs.to_netcdf(out_file)

        print(f'{Path(out_file).stat().st_size / 1e6:.1f} MB written to {out_file}')
        """)

    nb.md("""
        Now shut the door on everything you know. Forget the CSV files, forget this
        notebook. All you have is that one file.
        """)

    nb.code("""
        import xarray as xr
        reopened = xr.open_datatree(out_file)['survey']

        reopened
        """)

    nb.md("""
        ---
        ### Exercise 6.1

        This is the question you will be asked every time you hand someone a GS
        file: how do they find out what is in it and what it means? There are four
        parts to it, and you now have a real file to answer them against.

        **a) What datasets does this file contain?**

        *Hint: containers and surveys have a `.gs.tree` property.*
        """)

    nb.code(f"""
        #EXERCISE#
        tree = reopened.gs.tree

        print(tree)
        assert 'raw_data' in str(tree), 'that does not look like the survey tree'
        """,
        f"""
        #EXERCISE#
        tree = ...

        print(tree)
        assert 'raw_data' in str(tree), 'that does not look like the survey tree'
        """)

    nb.md("""
        **b) What does the survey say about itself?** Who made it, when, why, and in
        what coordinate reference system?
        """)

    nb.code(f"""
        reopened
        """)

    nb.md("""
        **c) What does one variable mean?** Take `height` in the raw data - find its
        long name, its units, and its valid range, without opening a single CSV.
        """)

    nb.code(f"""
        raw = reopened['data']['raw_data']

        raw['height']

        """)

    nb.md("""
        Note that `valid_range` was computed for you on the way in - GSPy records
        the actual range of the data next to what the data claims to be.

        **d) Sweep one attribute across the whole file.** List the units of every
        variable in the survey at once.

        *Hint: `.gs.get_all_attr(attribute)` walks the tree and returns a mapping of
        variable path to value.*
        """)

    nb.code(f"""
        #EXERCISE#
        all_units = reopened.gs.get_all_attr('units')

        print(f'{{len(all_units)}} variables carry a units attribute\\n')
        for path, units in list(all_units.items())[:12]:
            print(f'{{units:<28}} {{path}}')
        """,
        f"""
        #EXERCISE#
        all_units = ...

        print(f'{{len(all_units)}} variables carry a units attribute\\n')
        for path, units in list(all_units.items())[:12]:
            print(f'{{units:<28}} {{path}}')
        """)


    nb.md("""
        Outside Python, `ncdump -h skytem_workshop.nc` prints the whole schema, and
        the file opens in NCView, Panoply, QGIS and anything else that reads NetCDF. Nothing
        about the metadata is GSPy-specific once it is written.
        """)

    # ---------------------------------------------------------------- section 7
    nb.md("""
        ---
        ---
        ## 7. Plotting

        Because a GS file is an `xarray` DataTree, everything xarray can do works,
        and the units and long names come along for the ride on the axes.

        Everything is lazy loaded too, contents only enter RAM when they are requested.
        """)

    nb.code("""
        plt.figure(figsize=(9, 3))
        reopened['data']['raw_data']['height'].plot()
        plt.tight_layout()
        """)

    nb.code("""
        plt.figure(figsize=(7, 6))
        reopened['derived_maps']['maps']['magnetic_tmi'].plot(cmap='jet', robust=True)
        plt.tight_layout()
        """)

    nb.md("""
        ---
        ### Exercise 7.1

        Plot the depth to bedrock grid, and then make a scatter plot of the bedrock
        picks coloured by their elevation.

        *Hint: the grid variable is `bedrock_depth` in `derived_maps/maps`. For the
        scatter, GSPy adds `.gs.scatter(hue=...)` to tabular datasets - look at
        `reopened['data']['depth_to_bedrock']` to find a variable to colour by.*
        """)

    nb.code(f"""
        #EXERCISE#
        plt.figure(figsize=(7, 6))
        reopened['derived_maps']['maps']['bedrock_depth'].plot(cmap='viridis', robust=True)
        plt.tight_layout()

        plt.figure(figsize=(7, 6))
        reopened['data']['depth_to_bedrock'].gs.scatter(hue='br_elevation', cmap='terrain')
        plt.tight_layout()
        """,
        f"""
        #EXERCISE#
        plt.figure(figsize=(7, 6))
        reopened[...][...][...].plot(cmap='viridis', robust=True)
        plt.tight_layout()

        plt.figure(figsize=(7, 6))
        reopened['data']['depth_to_bedrock'].gs.scatter(hue=..., cmap='terrain')
        plt.tight_layout()
        """)

    nb.md("""
        ---
        ---
        ## Where next

        You started with four CSVs, four GeoTIFFs and no idea what any of it meant.
        You now have one file that answers every question from section 1 in a single
        line of code.

        Two things worth taking away:

        1. **`metadata_template()` is the way in.** You never have to write a GS
           metadata file from a blank page. Generate the skeleton, fill in the `??`,
           and let the error messages tell you what is still missing.
        2. **The metadata is a one-time cost.** Filling in 34 variables is tedious
           once. Every future use of the data - by you, by a colleague, by
           software - reads it for free.

        Next: **`2_tempest_aseg.ipynb`** walks the same path for an ASEG-GDF survey,
        where the file format carries its own column definitions and the template
        comes back mostly filled in already.

        - GSPy documentation: https://doi-usgs.github.io/gspy
        - The examples this workshop is built from live in `examples/` in the gspy
          repository.
        """)

    nb.write(HERE / '1_skytem_from_scratch.ipynb',
             HERE / 'solutions' / '1_skytem_from_scratch_solutions.ipynb')


# ===========================================================================
#  Notebook 2 - Tempest ASEG-GDF
# ===========================================================================

def build_tempest():
    nb = Notebook()

    nb.md("""
        # A second format: ASEG-GDF

        ## GSPy workshop, part 2

        Part 1 built a GS file from CSV files, where the header gives you column
        names and nothing else. This notebook walks the same path for a Tempest AEM
        survey stored in **ASEG-GDF2**, a format that carries its own column
        definitions.

        The interesting question is how much less work you have to do.

        | | Section | Time |
        |---|---|---|
        | 1 | What is in the box? | 5 min |
        | 2 | A template that fills itself in | 10 min |
        | 3 | Survey and raw data | 8 min |
        | 4 | Models derived from data | 7 min |
        | 5 | A raster map | 5 min |
        | 6 | Save, reopen, inspect | 5 min |

        Roughly 40 minutes. Cells marked **EXERCISE** need completing; solutions are
        in `solutions/`.

        *Source data: Minsley, B.J., James, S.R., Bedrosian, P.A., Pace, M.D.,
        Hoogenboom, B.E., and Burton, B.L., 2021, Airborne electromagnetic,
        magnetic, and radiometric survey of the Mississippi Alluvial Plain,
        November 2019 - March 2020: U.S. Geological Survey data release,
        https://doi.org/10.5066/P9E44CTQ*
        """)

    nb.code("""
        import warnings
        from os.path import join
        from pathlib import Path

        import matplotlib.pyplot as plt

        import gspy
        from gspy import Dataset, Survey

        warnings.filterwarnings('ignore')

        DATA = 'data/tempest'
        PREPARED = 'prepared_metadata/tempest'
        SCRATCH = 'my_metadata'

        Path(SCRATCH).mkdir(exist_ok=True)
        assert Path(DATA).is_dir(), 'Run Jupyter from the workshop root folder'
        print('gspy', gspy.__version__)
        """)

    # ---------------------------------------------------------------- section 1
    nb.md("""
        ---
        ---
        ## 1. What is in the box?
        """)

    nb.code("""
        for path in sorted(Path(DATA).iterdir()):
            print(f'{path.name:<28} {path.stat().st_size / 1e6:>6.1f} MB')
        """)

    nb.md("""
        An ASEG-GDF dataset comes in pairs: a `.dat` file holding whitespace
        delimited numbers with **no header at all**, and a `.dfn` definition file
        describing the columns. Look at the first few lines of each.
        """)

    nb.code("""
        print('--- Tempest.dfn ---')
        print('\\n'.join(Path(DATA, 'Tempest.dfn').read_text().splitlines()[:8]))
        print()
        print('--- Tempest.dat ---')
        with open(join(DATA, 'Tempest.dat')) as f:
            for _ in range(2):
                print(f.readline()[:140], '...')
        """)

    nb.md("""
        Each `DEFN` line names a column and describes it:

        ```
        DEFN 15 ST=RECD,RT=;GPS_Elevation:f8.2:UNIT=m:NULL=-999.99,NAME=Final GPS Elevation (Ortho)
        ```

        That single line carries the column name, its Fortran format, its **units**,
        its **no-data value** and a **descriptive name**. Compare that with a CSV
        header, which gave you the word `Alt` and left you guessing.

        ---
        ### Exercise 1.1 - discussion, no code

        Which of the questions that stumped us in part 1 section 1 could you now
        answer from the DFN alone? Which ones still could not be answered?

        *Your answer:*
        """)

    # ---------------------------------------------------------------- section 2
    nb.md("""
        ---
        ---
        ## 2. A template that fills itself in

        Same call as part 1, pointed at the `.dat` file. GSPy finds the matching
        `.dfn` on its own.
        """)

    nb.code("""
        template = Dataset.metadata_template(join(DATA, 'Tempest.dat'))
        template.dump(join(SCRATCH, 'tempest_raw_template.yml'))

        print(f"{len(template['variables'])} variables found\\n")
        for name in ('Line', 'GPS_Elevation', 'DTM', 'EMX_HPRG'):
            print(f'{name}:')
            for key, value in template['variables'][name].items():
                print(f'    {key}: {value}')
            print()
        """)

    nb.md("""
        Compare that with part 1, where all four fields came back `not_defined`.
        Here `long_name`, `units` and `missing_value` are already populated,
        straight out of the DFN, for 61 variables.

        `EMX_HPRG` shows the same `dimensions: ['index', '??']` as `HM_X` did - the
        DFN says there are 15 windows, but not what time each window corresponds to.
        Gate times are a property of the instrument, so they still have to come from
        a system definition. Some things a file format cannot tell you.

        ---
        ### Exercise 2.1

        Find out what is still missing. Count how many variables have at least one
        `not_defined` field, and show which fields those are.

        *Hint: iterate over `template['variables'].items()` and look for values
        equal to `'not_defined'`.*
        """)

    nb.code(f"""
        #EXERCISE#
        incomplete = {{}}
        for name, attrs in template['variables'].items():
            missing = [key for key, value in attrs.items() if value == 'not_defined']
            assert isinstance(missing, list), 'missing should be a list of attribute names'
            if missing:
                incomplete[name] = missing

        print(f'{{len(incomplete)}} of {{len(template["variables"])}} variables have gaps\\n')
        for name, missing in list(incomplete.items())[:10]:
            print(f'{{name:<20}} {{missing}}')
        """,
        f"""
        #EXERCISE#
        incomplete = {{}}
        for name, attrs in template['variables'].items():
            missing = ...
            assert isinstance(missing, list), 'missing should be a list of attribute names'
            if missing:
                incomplete[name] = missing

        print(f'{{len(incomplete)}} of {{len(template["variables"])}} variables have gaps\\n')
        for name, missing in list(incomplete.items())[:10]:
            print(f'{{name:<20}} {{missing}}')
        """)

    nb.md("""
        Mostly `units`, on variables that genuinely have none - line numbers, flight
        numbers, dates - plus the handful the DFN left blank. The DFN got you most
        of the way; the rest is judgement.

        Notice also what the DFN could *not* provide: which columns are the
        coordinates. `Easting_Albers` and `Northing_Albers` are obvious to you and
        invisible to software.
        """)

    nb.code("""
        print('coordinates GSPy still needs:')
        for axis, value in template['coordinates'].items():
            print(f'  {axis}: {value}')
        """)

    # ---------------------------------------------------------------- section 3
    nb.md("""
        ---
        ---
        ## 3. Survey and raw data

        From here the workflow is identical to part 1, so we move at pace with the
        prepared metadata.
        """)

    nb.code("""
        survey = Survey.from_dict(join(PREPARED, 'Tempest_survey_md.yml'))
        print(survey.gs.tree)

        survey
        """)

    nb.md("""
        A survey with no children, same as part 1. The system definition is placed
        differently this time, though: instead of a standalone `skytem_system.yml`
        handed to `system=`, the Tempest system is written *inside*
        `Tempest_data_md.yml`, and a container lifts out any top level key whose name
        contains `system`.

        Both are valid. Which you want depends on whether the instrument description
        is shared: a standalone file when several datasets cite one instrument, an
        inline block when it describes only this dataset.

        ---
        ### Exercise 3.1

        Create a `data` container and attach `Tempest.dat` using
        `Tempest_data_md.yml`. No `system=` argument is needed, because the system
        comes in with the metadata file.
        """)

    nb.code(f"""
        #EXERCISE#
        data_container = survey.gs.add_container('data', content='raw data')

        raw_data = data_container.gs.add(
            key='raw_data',
            data=join(DATA, 'Tempest.dat'),
            metadata_file=join(PREPARED, 'Tempest_data_md.yml'))

        print(dict(raw_data.sizes))
        print(survey.gs.tree)

        raw_data
        """,
        f"""
        #EXERCISE#
        data_container = survey.gs.add_container(..., content='raw data')

        raw_data = data_container.gs.add(
            key=...,
            data=...,
            metadata_file=...)

        print(dict(raw_data.sizes))
        print(survey.gs.tree)

        raw_data
        """)

    nb.md("""
        `gate_times: 15` resolved the `??`, and `tempest_system` now hangs below the
        raw data as its own group.
        """)

    # ---------------------------------------------------------------- section 4
    nb.md("""
        ---
        ---
        ## 4. Models derived from data

        The inverted models were produced from that raw data with that same
        instrument, and `system=raw_data.tempest_system` records it: the models
        cite the *same* system definition rather than describing it a second time.

        ---
        ### Exercise 4.1

        Attach `Tempest_model.dat` with `Tempest_model_md.yml` to a new `models`
        container, passing the system from the raw data.
        """)

    nb.code(f"""
        #EXERCISE#
        model_container = survey.gs.add_container(
            'models', content='inverted 1-D electrical resistivity models')

        models = model_container.gs.add(
            key='inverted_models',
            data=join(DATA, 'Tempest_model.dat'),
            metadata_file=join(PREPARED, 'Tempest_model_md.yml'),
            system=raw_data.tempest_system)

        print(dict(models.sizes))

        models
        """,
        f"""
        #EXERCISE#
        model_container = survey.gs.add_container(..., content='inverted 1-D electrical resistivity models')

        models = model_container.gs.add(
            key=...,
            data=...,
            metadata_file=...,
            system=...)

        print(dict(models.sizes))

        models
        """)

    nb.md("""
        `layer_depth: 30` alongside `gate_times: 15` - the models carry both their
        own layer geometry and the gate times of the data they were fitted to.
        """)

    # ---------------------------------------------------------------- section 5
    nb.md("""
        ---
        ---
        ## 5. A raster map

        ---
        ### Exercise 5.1

        Add the contractor's total magnetic intensity grid to a `derived_maps`
        container, using `Tempest_raster_md.yml`. Remember rasters take no
        `data`.
        """)

    nb.code(f"""
        #EXERCISE#
        map_container = survey.gs.add_container('derived_maps', content='derived maps')

        maps = map_container.gs.add(
            key='maps',
            metadata_file=join(PREPARED, 'Tempest_raster_md.yml'))

        print(dict(maps.sizes))

        maps
        """,
        f"""
        #EXERCISE#
        map_container = survey.gs.add_container(..., content='derived maps')

        maps = map_container.gs.add(
            key=...,
            metadata_file=...)

        print(dict(maps.sizes))

        maps
        """)

    # ---------------------------------------------------------------- section 6
    nb.md("""
        ---
        ---
        ## 6. Save, reopen, inspect
        """)

    nb.code("""
        out_file = join(SCRATCH, 'tempest_workshop.nc')
        survey.gs.to_netcdf(out_file)

        reopened = gspy.open_datatree(out_file)['survey']
        print(reopened.gs.tree)
        """)

    nb.md("""
        ---
        ### Exercise 6.1

        The same four questions as part 1 section 6, now on this file. Pick any
        variable in the raw data and report its long name, units and no-data value -
        then check them against the `DEFN` line for that column in `Tempest.dfn`.
        The whole point is that they agree.
        """)

    nb.code(f"""
        #EXERCISE#
        raw = reopened['data']['raw_data']

        variable = 'gps_elevation'      # GSPy lower-cases variable names on the way in
        for key, value in raw[variable].attrs.items():
            print(f'{{key:<16}} {{value}}')

        print()
        for line in Path(DATA, 'Tempest.dfn').read_text().splitlines():
            if 'GPS_Elevation' in line:
                print(line.strip())
        """,
        f"""
        #EXERCISE#
        raw = reopened['data']['raw_data']

        variable = ...      # note: GSPy lower-cases variable names on the way in
        for key, value in ...:
            print(f'{{key:<16}} {{value}}')

        print()
        for line in Path(DATA, 'Tempest.dfn').read_text().splitlines():
            if ... in line:
                print(line.strip())
        """)

    nb.md("""
        ---
        ### Exercise 6.2

        Two plots to finish: a scatter of the raw data coloured by transmitter
        height, and the magnetic grid.

        *Hint: `.gs.scatter(x='x', hue=...)` for the tabular data. The grid variable
        is `magnetic_tmi`.*
        """)

    nb.code(f"""
        #EXERCISE#
        plt.figure(figsize=(7, 6))
        reopened['data']['raw_data'].gs.scatter(x='x', hue='tx_height', cmap='jet')
        plt.tight_layout()

        plt.figure(figsize=(7, 6))
        reopened['derived_maps/maps']['magnetic_tmi'].plot(cmap='jet', robust=True)
        plt.tight_layout()
        """,
        f"""
        #EXERCISE#
        plt.figure(figsize=(7, 6))
        reopened['data']['raw_data'].gs.scatter(x='x', hue=..., cmap='jet')
        plt.tight_layout()

        plt.figure(figsize=(7, 6))
        reopened[...][...].plot(cmap='jet', robust=True)
        plt.tight_layout()
        """)

    nb.md("""
        ---
        ---
        ## Taking stock

        Same eight-step workflow, two very different input formats. What changed was
        only how much of the variable metadata came for free:

        | | CSV (part 1) | ASEG-GDF (part 2) |
        |---|---|---|
        | variable names | from the header | from the DFN |
        | long names | you write them | from the DFN |
        | units | you write them | from the DFN |
        | no-data values | you write them | from the DFN |
        | which columns are coordinates | you say so | you say so |
        | gate times, instrument geometry | a system definition | a system definition |

        The two rows at the bottom never come for free, in any format. They are
        knowledge about the survey, not about the file, and writing them down once
        in a system definition is the most valuable thing in this workshop.

        - GSPy documentation: https://doi-usgs.github.io/gspy
        """)

    nb.write(HERE / '2_tempest_aseg.ipynb',
             HERE / 'solutions' / '2_tempest_aseg_solutions.ipynb')


if __name__ == '__main__':
    build_skytem()
    build_tempest()
