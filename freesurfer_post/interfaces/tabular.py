import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
from nipype.interfaces.base import File, SimpleInterface, TraitedSpec, isdefined, traits

from ..utils import find_freesurfer_dir

"""Compile FreeSurfer stats files."""

hemispheres = ['lh', 'rh']
NOSUFFIX_COLS = ['Index', 'SegId', 'StructName']

ASEG_STATS_METADATA = {
    'participant_id': {'Description': 'BIDS participant ID'},
    'session_id': {'Description': 'BIDS session ID'},
    'name': {'Description': 'Name of the structure'},
    'nvoxels': {
        'Description': 'Number of voxels in the structure. Originally NVoxels.'
    },
    'volume_mm3': {
        'Description': 'Volume of the structure in mm3. Originally Volume_mm3.'
    },
    'normmean': {'Description': 'Normalized mean. Originally normMean.'},
    'normstddev': {
        'Description': 'Normalized standard deviation. Originally normStdDev.'
    },
    'normmin': {'Description': 'Normalized minimum. Originally normMin.'},
    'normmax': {'Description': 'Normalized maximum. Originally normMax.'},
    'normrange': {'Description': 'Normalized range. Originally normRange.'},
}


def statsfile_to_df(stats_fname, hemi, atlas, column_suffix=''):
    with open(stats_fname) as fo:
        data = fo.readlines()

    idx = [i for i, line in enumerate(data) if line.startswith('# ColHeaders ')]
    assert len(idx) == 1
    idx = idx[0]

    columns_row = data[idx]
    actual_data = data[idx + 1 :]
    actual_data = [line.split() for line in actual_data]
    columns = columns_row.replace('# ColHeaders ', '').split()

    df = pd.DataFrame(
        columns=[
            col + column_suffix if col not in NOSUFFIX_COLS else col for col in columns
        ],
        data=actual_data,
    )
    df.insert(0, 'hemisphere', hemi)
    df.insert(0, 'atlas', atlas)
    return df


class _SummarizeRegionStatsInputSpec(TraitedSpec):
    subject_id = traits.Str(
        desc='Subject ID',
        mandatory=True,
    )
    session_id = traits.Str(
        desc='Session ID',
        mandatory=False,
    )
    atlas_name = traits.Str(
        desc='Atlas name',
        mandatory=True,
    )
    lh_stats_file = File(
        desc='Path to left hemisphere stats file',
        exists=True,
        mandatory=True,
    )
    rh_stats_file = File(
        desc='Path to right hemisphere stats file',
        exists=True,
        mandatory=True,
    )
    lh_gwr_stats_file = File(
        desc='Path to left hemisphere g-w.pct stats file',
        exists=True,
        mandatory=True,
    )
    rh_gwr_stats_file = File(
        desc='Path to right hemisphere g-w.pct stats file',
        exists=True,
        mandatory=True,
    )
    subjects_dir = traits.Directory(
        desc='Path to subjects directory',
        exists=True,
        mandatory=True,
    )
    output_dir = traits.Directory(
        desc='Path to output directory',
        exists=True,
        mandatory=True,
    )


class _SummarizeRegionStatsOutputSpec(TraitedSpec):
    out_file = File(
        desc='TSV file with region stats for both hemispheres',
        mandatory=True,
    )


class SummarizeRegionStats(SimpleInterface):
    input_spec = _SummarizeRegionStatsInputSpec
    output_spec = _SummarizeRegionStatsOutputSpec

    def _run_interface(self, runtime):
        subject_id = self.inputs.subject_id
        atlas = self.inputs.atlas_name
        surfstat_dfs = []

        for hemi in hemispheres:
            # Get the surface statistics
            surfstats_file = getattr(self.inputs, f'{hemi}_stats_file')
            surfstat_df_ = statsfile_to_df(surfstats_file, hemi, atlas)

            # get the g-w.pct files
            gwr_stats_file = getattr(self.inputs, f'{hemi}_gwr_stats_file')
            gwpct_df_ = statsfile_to_df(
                gwr_stats_file, hemi, atlas, column_suffix='_wgpct'
            )
            surfstat_dfs.append(pd.merge(surfstat_df_, gwpct_df_))

        out_df = pd.concat(surfstat_dfs, axis=0, ignore_index=True)

        # The freesurfer directory may contain subject and session. check here
        session_id = (
            None if not isdefined(self.inputs.session_id) else self.inputs.session_id
        )
        out_df.insert(0, 'session_id', session_id)
        out_df.insert(0, 'subject_id', self.inputs.subject_id)

        def sanity_check_columns(reference_column, redundant_column, atol=0):
            if not np.allclose(
                out_df[reference_column].astype(np.float32),
                out_df[redundant_column].astype(np.float32),
                atol=atol,
            ):
                raise Exception(
                    f'The {reference_column} values were not identical to {redundant_column}'
                )
            out_df.drop(redundant_column, axis=1, inplace=True)

        # Do some sanity checks and remove redundant columns
        sanity_check_columns('NumVert', 'NVertices_wgpct', 0)
        sanity_check_columns('SurfArea', 'Area_mm2_wgpct', 1)
        output_dir = Path(self.inputs.output_dir) / subject_id
        output_dir.mkdir(parents=True, exist_ok=True)
        output_prefix = f'{subject_id}_{session_id}' if session_id else subject_id

        cleaned_atlas_name = (
            atlas.replace('.', '').replace('_order', '').replace('_', '')
        )

        # Convert column names to snake case
        out_df.columns = [
            col.lower().replace('-', '_').replace('.', '_') for col in out_df.columns
        ]
        # Rename subject_id to participant_id
        out_df = out_df.rename(columns={'subject_id': 'participant_id'})
        # Reorder columns to have participant_id first
        cols = out_df.columns.tolist()
        cols.remove('participant_id')
        out_df = out_df[['participant_id'] + cols]
        # Replace missing values with "n/a"
        out_df = out_df.fillna('n/a')

        # Save data
        out_df.to_csv(
            output_dir / f'{output_prefix}_seg-{cleaned_atlas_name}_surfacestats.tsv',
            sep='\t',
            index=False,
        )
        return runtime


def get_euler_from_log(reconlog):
    with reconlog.open('r') as reconlogf:
        log_lines = [line.strip() for line in reconlogf]

    def read_qc(target_str):
        (data,) = [line for line in log_lines if target_str in line]
        data = data.replace(',', '')
        tokens = data.split()
        rh_val = float(tokens[-1])
        lh_val = float(tokens[-4])
        return rh_val, lh_val

    rh_euler, lh_euler = read_qc('lheno')
    rh_holes, lh_holes = read_qc('lhholes')
    return {
        'lh_euler': {
            'value': lh_euler,
            'meta': 'Left hemisphere Euler number from recon-all.log',
        },
        'rh_euler': {
            'value': rh_euler,
            'meta': 'Right hemisphere Euler number from recon-all.log',
        },
        'lh_holes': {
            'value': lh_holes,
            'meta': 'Left hemisphere number of holes from recon-all.log',
        },
        'rh_holes': {
            'value': rh_holes,
            'meta': 'Right hemisphere number of holes from recon-all.log',
        },
    }


def read_stats(stats_file, info, get_measures=False, measures_only=False):
    """Reads stats from a freesurfer stats table.

    Parameters:
    ===========

    stats_file: str
        Path to the stats file to read
    info: dict
        Dictionary containing other collected info about the run
    get_measures: bool
        Should the # Measure lines be parsed and added to info?
    Returns: Nothing. the info dict gets keys/values added to it

    """
    with stats_file.open('r') as statsf:
        lines = statsf.readlines()
    stats_name = stats_file.name.split('.')[0]

    # Get the column names by finding the line with the header tag in it
    header_tag = '# ColHeaders'
    (header,) = [line for line in lines if header_tag in line]
    header = header[len(header_tag) :].strip().split()

    stats_df = pd.read_csv(str(stats_file), sep=r'\s+', comment='#', names=header).melt(
        id_vars=['StructName'], ignore_index=True
    )
    stats_df = stats_df[stats_df['variable'] != 'Index']

    if stats_name.startswith('lh'):
        suffix = '_Left'
    elif stats_name.startswith('rh'):
        suffix = '_Right'
    else:
        suffix = '_Sub'

    if not measures_only:
        # Get it into a nice form
        stats_df['FlatName'] = stats_df['StructName'] + '_' + stats_df['variable']

        for _, row in stats_df.iterrows():
            col_name = (
                row['FlatName']
                .replace('-', '_')
                .replace('3rd', 'Third')
                .replace('4th', 'Fourth')
                .replace('5th', 'Fifth')
            )
            if col_name in info:
                raise Exception(f'{col_name} is already present in the collected data')
            info[col_name] = {
                'value': row['value'],
                'meta': (
                    f'The "{row["variable"]}" value for the "{row["StructName"]}" '
                    f'structure. Originally in the stats/{stats_name} file.'
                ),
            }

    if get_measures:
        get_stat_measures(stats_file, suffix, info, stats_name)


def get_stat_measures(stats_file, suffix, info, stats_name):
    """Read a "Measure" from a stats file.

    Parameters:
    ===========

    stats_file: Path
        Path to a .stats file containing the measure you want
    info: dict
        Dictionary with all this subject's info
    """
    with stats_file.open('r') as statsf:
        lines = statsf.readlines()
    suffix = ''
    if '/rh.' in str(stats_file):
        suffix = '_rh'
    elif '/lh.' in str(stats_file):
        suffix = '_lh'

    measure_pat = re.compile(
        '# Measure ([A-Za-z]+), ([A-Za-z]+),* [-A-Za-z ]+, ([0-9.]+), .*'
    )
    for line in lines:
        match = re.match(measure_pat, line)
        if match:
            pt1, pt2, value = match.groups()
            pt1 = pt1 if pt1 == pt2 else f'{pt1}_{pt2}'
            key = f'{pt1}{suffix}'
            if key in info and not float(value) == info[key]['value']:
                raise Exception(
                    f'{key} is already in the metadata with a different value'
                )
            info[key] = {
                'value': float(value),
                'meta': (
                    'This is a whole-brain metadata measure with two '
                    f'possible labels, "{pt1}" and "{pt2}". It comes '
                    f'from the stats/{stats_name} file.'
                ),
            }


class _FSStatsInputSpec(TraitedSpec):
    subject_id = traits.Str(
        desc='Subject ID',
        mandatory=True,
    )
    session_id = traits.Str(
        desc='Session ID',
        mandatory=False,
    )
    subjects_dir = traits.Directory(
        desc='Path to ${SUBJECTS_DIR}',
        exists=True,
        mandatory=True,
    )
    output_dir = traits.Directory(
        desc='Path to output directory',
        exists=True,
        mandatory=True,
    )


class _FSStatsOutputSpec(TraitedSpec):
    out_file = File(
        desc='TSV file with region stats for both hemispheres',
        mandatory=True,
    )


class FSStats(SimpleInterface):
    input_spec = _FSStatsInputSpec
    output_spec = _FSStatsOutputSpec

    def _run_interface(self, runtime):
        subject_id = self.inputs.subject_id
        session_id = (
            self.inputs.session_id if isdefined(self.inputs.session_id) else None
        )
        subjects_dir = Path(self.inputs.subjects_dir)
        fs_dir = find_freesurfer_dir(subjects_dir, subject_id, session_id)

        fs_audit = {
            'subject_id': {'value': subject_id, 'meta': 'BIDS subject id'},
            'session_id': {'value': session_id, 'meta': 'BIDS session id'},
        }
        fs_audit.update(get_euler_from_log(fs_dir / 'scripts' / 'recon-all.log'))

        # Add global stats from two of the surface stats files
        read_stats(
            fs_dir / 'stats' / 'lh.aparc.pial.stats',
            fs_audit,
            get_measures=True,
            measures_only=True,
        )
        read_stats(
            fs_dir / 'stats' / 'rh.aparc.pial.stats',
            fs_audit,
            get_measures=True,
            measures_only=True,
        )

        # And grab the volume stats from aseg
        read_stats(fs_dir / 'stats' / 'aseg.stats', fs_audit, get_measures=True)

        # Remove SegId, it's the same for everyone
        for key in list(fs_audit.keys()):
            if 'SegId' in key:
                del fs_audit[key]

        # Write the outputs
        output_dir = Path(self.inputs.output_dir) / subject_id
        output_dir.mkdir(parents=True, exist_ok=True)
        output_prefix = f'{subject_id}_{session_id}' if session_id else subject_id
        atlas_tsv = output_dir / f'{output_prefix}_seg-FreeSurfer_morph.tsv'
        whole_brain_tsv = output_dir / f'{output_prefix}_desc-FreeSurfer_qc.tsv'
        atlas_json = output_dir / f'{output_prefix}_seg-FreeSurfer_morph.json'
        whole_brain_json = output_dir / f'{output_prefix}_desc-FreeSurfer_qc.json'

        # Convert all the keys to snake case
        fs_audit_renamed = {}
        for key in fs_audit:
            fs_audit_renamed[key.lower().replace('-', '_').replace('.', '_')] = (
                fs_audit[key]
            )
        fs_audit_renamed['participant_id'] = fs_audit_renamed['subject_id']
        del fs_audit_renamed['subject_id']

        # Extract just the values from the audit data
        data_value = {key: value['value'] for key, value in fs_audit_renamed.items()}
        data_df = pd.DataFrame([data_value])

        cols = data_df.columns.tolist()
        id_cols = ['participant_id', 'session_id']
        id_cols = [col for col in id_cols if col in cols]

        # Split data_df into two dataframes, one for the atlas and one for the whole brain measures
        suffixes = [
            '_nvoxels',
            '_volume_mm3',
            '_normmean',
            '_normstddev',
            '_normmin',
            '_normmax',
            '_normrange',
        ]

        atlas_columns = [
            col
            for col in data_df.columns
            if any(col.endswith(suffix) for suffix in suffixes)
        ]
        whole_brain_columns = [
            col for col in data_df.columns if col not in atlas_columns
        ]
        atlas_df = data_df[id_cols + atlas_columns]
        whole_brain_df = data_df[id_cols + whole_brain_columns]

        atlas_df = melt_with_suffix_list(atlas_df, id_cols, suffixes)

        # Create metadata with the same column names as the TSV
        wholebrain_metadata = {
            key: fs_audit_renamed[key]['meta'] for key in whole_brain_df.columns
        }

        with atlas_json.open('w') as jsonf:
            json.dump(ASEG_STATS_METADATA, jsonf, indent=2, sort_keys=True)

        with whole_brain_json.open('w') as jsonf:
            json.dump(wholebrain_metadata, jsonf, indent=2, sort_keys=True)

        atlas_df.to_csv(atlas_tsv, sep='\t', na_rep='n/a', index=False)
        whole_brain_df.to_csv(whole_brain_tsv, sep='\t', na_rep='n/a', index=False)
        return runtime


def melt_with_suffix_list(df, id_cols, suffixes):
    """Melt a DataFrame from wide form to long form using a predefined list of suffixes.

    Parameters:
    -----------
    df : pandas.DataFrame
        Input DataFrame in wide form
    id_cols : list
        List of ID column names to preserve
    suffixes : list
        List of suffix strings to look for in column names

    Returns:
    --------
    pandas.DataFrame
        DataFrame in long form with ID columns, 'name' column, and separate columns for each
        suffix.
    """
    # Get all non-ID columns
    all_cols = df.columns.tolist()
    non_id_cols = [col for col in all_cols if col not in id_cols]

    # Find all unique names by removing suffixes from column names
    names = []
    for col in non_id_cols:
        for suffix in suffixes:
            if col.endswith(suffix):
                name = col[: -len(suffix)]  # Remove the suffix to get the name
                names.append(name)
                continue

    # Create the result DataFrame starting with ID columns
    result_rows = []

    for _, row in df.iterrows():
        for name in names:
            new_row = {}
            # Add ID columns
            for id_col in id_cols:
                new_row[id_col] = row[id_col]

            # Add the name
            new_row['name'] = name

            # Add values for each suffix
            for suffix in suffixes:
                col_name = name + suffix
                if col_name in df.columns:
                    # Remove leading underscore from suffix for cleaner column name
                    clean_suffix = suffix.lstrip('_')
                    new_row[clean_suffix] = row[col_name]
                else:
                    # If column doesn't exist, add NaN or None
                    clean_suffix = suffix.lstrip('_')
                    new_row[clean_suffix] = None

            result_rows.append(new_row)

    return pd.DataFrame(result_rows)
