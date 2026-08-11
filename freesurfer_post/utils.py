"""Utility functions for FreeSurfer post-processing."""

import logging
import warnings
from pathlib import Path

LOGGER = logging.getLogger('nipype.interface')

# Resampling an extensive quantity (one whose value depends on how much
# surface a vertex covers) with barycentric interpolation does not conserve
# the total. Sidecars for these metrics say so instead of implying that the
# fsLR values can be summed to recover a native-surface total.
_EXTENSIVE_CAVEAT = (
    'Values are interpolated, not conserved: the resampled map does not sum '
    'to the native-surface total.'
)

# FreeSurfer qcache metrics that are converted to CIFTI, keyed by the metric
# name as it appears in a qcache filename. These are every measure in
# FreeSurfer 7's recon-all ``measurelist``; ``pial_lgi`` is deliberately absent
# because it needs ``-localGI``, which needs MATLAB. The suffixes are
# intentionally stable derivative names, since qcache's dots and underscores
# are not valid BIDS suffix characters.
QCACHE_CIFTI_METRICS = {
    'area': {
        'suffix': 'area',
        'description': 'vertex-wise cortical white-surface area',
        'units': 'mm^2',
        'extensive': True,
    },
    'area.pial': {
        'suffix': 'areaPial',
        'description': 'vertex-wise cortical pial-surface area',
        'units': 'mm^2',
        'extensive': True,
    },
    'curv': {
        'suffix': 'curv',
        'description': 'cortical surface curvature',
        'units': 'mm^-1',
    },
    'jacobian_white': {
        'suffix': 'jacobianWhite',
        'description': 'Jacobian determinant of the white-surface registration',
        'units': 'arbitrary',
    },
    'sulc': {
        'suffix': 'sulc',
        'description': 'sulcal depth',
        'units': 'mm',
    },
    'thickness': {
        'suffix': 'thickness',
        'description': 'cortical thickness',
        'units': 'mm',
    },
    'volume': {
        'suffix': 'volume',
        'description': 'vertex-wise cortical gray matter volume',
        'units': 'mm^3',
        'extensive': True,
    },
    # recon-all's measure name keeps its .mgh extension, and qcache only
    # strips .mgz, so the filenames really do contain 'w-g.pct.mgh'.
    'w-g.pct.mgh': {
        'suffix': 'wgPct',
        'description': 'gray/white intensity contrast',
        'units': 'percent',
    },
    'white.H': {
        'suffix': 'whiteH',
        'description': 'mean curvature of the white surface',
        'units': 'mm^-1',
    },
    'white.K': {
        'suffix': 'whiteK',
        'description': 'Gaussian curvature of the white surface',
        'units': 'mm^-2',
    },
}


def build_output_prefix(
    subject_id: str,
    session_id: str | None = None,
    run_id: str | None = None,
) -> str:
    """Build the subject/session/run prefix used by output files."""
    entities = [subject_id]
    if session_id is not None:
        entities.append(session_id)
    if run_id is not None:
        entities.append(run_id)
    return '_'.join(entities)


def find_qcache_metric_pairs(
    surface_dir: str | Path,
) -> list[tuple[str, Path, Path]]:
    """Find paired hemispheric qcache metrics in fsaverage space.

    Returns tuples containing the metric name, left-hemisphere file, and
    right-hemisphere file. An incomplete pair is treated as an error because a
    cortical dense scalar must contain both hemispheres.
    """
    surface_dir = Path(surface_dir)
    suffix = '.fsaverage.mgh'
    hemispheric_files: dict[str, dict[str, Path]] = {'lh': {}, 'rh': {}}
    skipped = set()

    for hemi in hemispheric_files:
        for metric_file in surface_dir.glob(f'{hemi}.*{suffix}'):
            metric = metric_file.name[len(f'{hemi}.') : -len(suffix)]
            if parse_qcache_metric(metric) is None:
                skipped.add(metric)
            else:
                hemispheric_files[hemi][metric] = metric_file

    # Say what was dropped, so that a hole in QCACHE_CIFTI_METRICS is visible
    # in the logs rather than showing up as quietly missing outputs.
    if skipped:
        LOGGER.info(
            'Skipping %d unsupported fsaverage qcache metric(s) in %s: %s',
            len(skipped),
            surface_dir,
            ', '.join(sorted(skipped)),
        )

    left_metrics = set(hemispheric_files['lh'])
    right_metrics = set(hemispheric_files['rh'])
    incomplete_metrics = left_metrics.symmetric_difference(right_metrics)
    if incomplete_metrics:
        metrics = ', '.join(sorted(incomplete_metrics))
        raise FileNotFoundError(f'Unpaired fsaverage qcache metrics: {metrics}')

    if not left_metrics:
        raise FileNotFoundError(f'No fsaverage qcache metrics found in {surface_dir}')

    return [
        (
            metric,
            hemispheric_files['lh'][metric],
            hemispheric_files['rh'][metric],
        )
        for metric in sorted(left_metrics)
    ]


def build_cifti_output_name(output_prefix: str, metric: str) -> str:
    """Build the BIDS filename for an fsLR 164k qcache dense scalar."""
    parsed_metric = parse_qcache_metric(metric)
    if parsed_metric is None:
        raise ValueError(f'Unsupported qcache metric: {metric}')

    _, metric_info, smoothing_fwhm = parsed_metric
    entities = [output_prefix, 'space-fsLR', 'den-164k']
    if smoothing_fwhm is not None:
        entities.append(f'desc-fwhm{smoothing_fwhm}')
    return f'{"_".join(entities)}_{metric_info["suffix"]}.dscalar.nii'


def build_cifti_sidecar_name(cifti_name: str) -> str:
    """Build the JSON sidecar filename corresponding to a CIFTI filename."""
    if not cifti_name.endswith('.dscalar.nii'):
        raise ValueError(f'Not a dense-scalar CIFTI filename: {cifti_name}')
    return f'{cifti_name.removesuffix(".dscalar.nii")}.json'


def build_cifti_metadata(metric: str) -> dict[str, str | int]:
    """Build metadata for a qcache-derived fsLR CIFTI dense scalar."""
    parsed_metric = parse_qcache_metric(metric)
    if parsed_metric is None:
        raise ValueError(f'Unsupported qcache metric: {metric}')

    _, metric_info, smoothing_fwhm = parsed_metric
    description = (
        f'FreeSurfer {metric_info["description"]}, resampled from fsaverage to '
        'fsLR at 164k surface density with area-adaptive barycentric '
        'interpolation.'
    )
    if metric_info.get('extensive'):
        description = f'{description} {_EXTENSIVE_CAVEAT}'

    metadata: dict[str, str | int] = {
        'Description': description,
        'Units': metric_info['units'],
    }
    if smoothing_fwhm is not None:
        metadata['SmoothingFWHM'] = smoothing_fwhm
        metadata['SmoothingFWHMUnits'] = 'mm'
    return metadata


def parse_qcache_metric(
    metric: str,
) -> tuple[str, dict[str, str | bool], int | None] | None:
    """Parse a supported qcache metric and its optional smoothing level.

    ``pial_lgi`` and any other unsupported qcache products are intentionally
    excluded from CIFTI generation.
    """
    base_metric, separator, smoothing_label = metric.rpartition('.fwhm')
    if separator:
        if not smoothing_label.isdecimal():
            return None
        smoothing_fwhm = int(smoothing_label)
    else:
        base_metric = metric
        smoothing_fwhm = None

    metric_info = QCACHE_CIFTI_METRICS.get(base_metric)
    if metric_info is None:
        return None
    return base_metric, metric_info, smoothing_fwhm


def find_freesurfer_dir(
    subjects_dir: str | Path,
    subject_id: str,
    session_id: str | None = None,
    run_id: str | None = None,
) -> Path:
    """Find a valid FreeSurfer subject directory in a directory.

    Parameters
    ----------
    subjects_dir : str or Path
        Path to FreeSurfer subjects directory
    subject_id : str
        Subject identifier
    session_id : str, optional
        Session identifier
    run_id : str, optional
        Run identifier

    Returns
    -------
    Path
        Path to valid FreeSurfer subject directory
    """
    subjects_dir = Path(subjects_dir)

    if not subjects_dir.exists():
        raise FileNotFoundError(f'Subjects directory {subjects_dir} does not exist')

    # Most specific first. Every combination of the requested entities is a
    # candidate, because FreeSurfer directory names are only conventionally
    # related to BIDS entities.
    entity_sets = [
        (session_id, run_id),
        (None, run_id),
        (session_id, None),
        (None, None),
    ]
    candidates: list[Path] = []
    for session, run in entity_sets:
        name = '_'.join(
            entity for entity in (subject_id, session, run) if entity is not None
        )
        candidate = subjects_dir / name
        if candidate not in candidates:
            candidates.append(candidate)

    preferred_candidate = candidates[0]
    for candidate in candidates:
        if candidate.exists():
            if candidate != preferred_candidate:
                warnings.warn(
                    f'{preferred_candidate} not found; using {candidate} instead',
                    stacklevel=2,
                )
            return candidate

    searched = ', '.join(str(candidate) for candidate in candidates)
    raise FileNotFoundError(
        f'No directory found for subject: {subject_id}, session: {session_id}, '
        f'run: {run_id}. Searched: {searched}'
    )
