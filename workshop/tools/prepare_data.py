"""Build the workshop data folder from a gspy source checkout.

The workshop is meant to be handed out as a self-contained folder, so the data
files are copied here rather than referenced in place.  They are also trimmed:
tabular files keep every Nth record and rasters are decimated by a factor of 2.
That keeps the whole folder around 12 MB instead of 44 MB while leaving every
file recognisable and every gspy code path exercised.

The completed YAML metadata files are copied into ``prepared_metadata`` and are
deliberately kept *out* of ``data``.  The workshop opens with the premise that
no metadata exists at all, so ``data`` must contain nothing but data.

Usage
-----
    python tools/prepare_data.py /path/to/gspy_repo

"""
import re
from argparse import ArgumentParser
from pathlib import Path
from shutil import copyfile

import rasterio
import rioxarray  # noqa: F401  (registers the .rio accessor)

# Tabular files: (source path relative to examples/data_files, destination name,
# keep-every-Nth-record).  Headers are always kept.
TABULAR = [
    ('skytem_csv/data/skytem_contractor_data.csv', 'skytem/skytem_contractor_data.csv', 4),
    ('skytem_csv/data/skytem_processed_data.csv', 'skytem/skytem_processed_data.csv', 4),
    ('skytem_csv/data/top_dolomite_blocky_lidar.csv', 'skytem/top_dolomite_blocky_lidar.csv', 4),
    ('skytem_csv/model/skytem_inverted_models.csv', 'skytem/skytem_inverted_models.csv', 4),
    ('tempest_aseg/data/Tempest.dat', 'tempest/Tempest.dat', 4),
    ('tempest_aseg/model/Tempest_model.dat', 'tempest/Tempest_model.dat', 4),
]

# Files copied verbatim.  The ASEG definition files describe the columns, not
# the records, so they must not be trimmed.
VERBATIM = [
    ('tempest_aseg/data/Tempest.dfn', 'tempest/Tempest.dfn'),
    ('tempest_aseg/model/Tempest_model.dfn', 'tempest/Tempest_model.dfn'),
]

# Rasters, decimated by DECIMATE in both directions.
RASTERS = [
    ('skytem_csv/data/mag_tmi.tif', 'skytem/mag_tmi.tif'),
    ('skytem_csv/data/mag_rmf.tif', 'skytem/mag_rmf.tif'),
    ('skytem_csv/data/top_bedrock.tif', 'skytem/top_bedrock.tif'),
    ('skytem_csv/data/bedrock_depth.tif', 'skytem/bedrock_depth.tif'),
    ('tempest_aseg/data/mag.tif', 'tempest/mag.tif'),
]

DECIMATE = 2

# The completed metadata, revealed part way through the workshop.  Flattened out
# of the data/model split used by the gspy examples.
PREPARED_METADATA = [
    ('skytem_csv/data/skytem_survey.yml', 'skytem/skytem_survey.yml'),
    ('skytem_csv/data/skytem_system.yml', 'skytem/skytem_system.yml'),
    ('skytem_csv/data/skytem_contractor_data.yml', 'skytem/skytem_contractor_data.yml'),
    ('skytem_csv/data/skytem_processed_data.yml', 'skytem/skytem_processed_data.yml'),
    ('skytem_csv/data/bedrock_picks.yml', 'skytem/bedrock_picks.yml'),
    ('skytem_csv/data/magnetics_bedrock_picks.yml', 'skytem/magnetics_bedrock_picks.yml'),
    ('skytem_csv/model/skytem_inverted_models.yml', 'skytem/skytem_inverted_models.yml'),
    ('tempest_aseg/data/Tempest_survey_md.yml', 'tempest/Tempest_survey_md.yml'),
    ('tempest_aseg/data/Tempest_data_md.yml', 'tempest/Tempest_data_md.yml'),
    ('tempest_aseg/data/Tempest_raster_md.yml', 'tempest/Tempest_raster_md.yml'),
    ('tempest_aseg/model/Tempest_model_md.yml', 'tempest/Tempest_model_md.yml'),
]


# gspy resolves the ``files:`` entries of a raster metadata file relative to the
# directory holding that metadata file.  The workshop keeps metadata and data in
# separate folders, so those entries have to be repointed on the way in.
RASTER_METADATA = [
    'skytem/magnetics_bedrock_picks.yml',
    'tempest/Tempest_raster_md.yml',
]


def trim_tabular(source, destination, keep_every, has_header):
    """Copy a text data file, keeping every Nth record."""
    with open(source, 'r') as f:
        lines = f.readlines()

    header, records = (lines[:1], lines[1:]) if has_header else ([], lines)
    kept = records[::keep_every]

    with open(destination, 'w') as f:
        f.writelines(header + kept)

    return len(records), len(kept)


def decimate_raster(source, destination, step):
    """Copy a raster, keeping every ``step`` th row and column.

    Decimation rather than averaging, so that no-data values never smear into
    their neighbours and every value in the output is a real measurement.
    """
    da = rioxarray.open_rasterio(source)
    small = da.isel(x=slice(None, None, step), y=slice(None, None, step))

    with rasterio.open(source) as r:
        nodata = r.nodata
    if nodata is not None:
        small.rio.write_nodata(nodata, inplace=True)

    small.rio.to_raster(destination)

    return da.shape, small.shape


def repoint_raster_files(metadata_file, track):
    """Rewrite bare ``*.tif`` names so they resolve from the metadata folder."""
    text = metadata_file.read_text()
    prefix = f"../../data/{track}/"

    def replace(match):
        return prefix + match.group(0)

    updated = re.sub(r'[\w.\-]+\.tif', replace, text)
    metadata_file.write_text(updated)

    return len(re.findall(re.escape(prefix), updated))


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('gspy_repo', type=Path,
                        help='Path to a gspy checkout containing examples/data_files')
    args = parser.parse_args()

    source_root = args.gspy_repo / 'examples' / 'data_files'
    assert source_root.is_dir(), f"No examples/data_files under {args.gspy_repo}"

    here = Path(__file__).resolve().parent.parent
    data_root = here / 'data'
    metadata_root = here / 'prepared_metadata'

    for subdirectory in ('skytem', 'tempest'):
        (data_root / subdirectory).mkdir(parents=True, exist_ok=True)
        (metadata_root / subdirectory).mkdir(parents=True, exist_ok=True)
    (here / 'my_metadata').mkdir(exist_ok=True)

    for source, destination, keep_every in TABULAR:
        has_header = source.endswith('.csv')
        n_in, n_out = trim_tabular(source_root / source, data_root / destination,
                                   keep_every, has_header)
        print(f"{destination:<45} {n_in:>7} -> {n_out:>7} records")

    for source, destination in VERBATIM:
        copyfile(source_root / source, data_root / destination)
        print(f"{destination:<45} copied verbatim")

    for source, destination in RASTERS:
        shape_in, shape_out = decimate_raster(source_root / source,
                                              data_root / destination, DECIMATE)
        print(f"{destination:<45} {str(shape_in):>18} -> {str(shape_out):>18}")

    for source, destination in PREPARED_METADATA:
        copyfile(source_root / source, metadata_root / destination)
        print(f"prepared_metadata/{destination:<28} copied")

    for destination in RASTER_METADATA:
        track = destination.split('/')[0]
        n = repoint_raster_files(metadata_root / destination, track)
        print(f"prepared_metadata/{destination:<28} repointed {n} raster path(s)")


if __name__ == '__main__':
    main()
