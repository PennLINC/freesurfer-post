"""Utility functions for FreeSurfer post-processing."""

import warnings
from pathlib import Path

# FreeSurfer qcache metrics that are converted to CIFTI. The names on the
# right are intentionally stable derivative suffixes; qcache's dots and
# underscores are not valid BIDS suffix characters.
QCACHE_CIFTI_METRICS = {
    'area': {
        'suffix': 'area',
        'description': 'vertex-wise cortical surface area',
        'units': 'mm^2',
    },
    'area.pial': {
        'suffix': 'areaPial',
        'description': 'vertex-wise cortical pial surface area',
        'units': 'mm^2',
    },
    'curv': {
        'suffix': 'curv',
        'description': 'cortical surface curvature',
        'units': 'mm^-1',
    },
    'jacobian_white': {
        'suffix': 'JacobianWhite',
        'description': 'Jacobian determinant of the white-surface registration',
        'units': '1',
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
        'description': 'vertex-wise cortical volume',
        'units': 'mm^3',
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
    if session_id:
        entities.append(session_id)
    if run_id:
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

    for hemi in hemispheric_files:
        for metric_file in surface_dir.glob(f'{hemi}.*{suffix}'):
            metric = metric_file.name[len(f'{hemi}.') : -len(suffix)]
            if parse_qcache_metric(metric) is not None:
                hemispheric_files[hemi][metric] = metric_file

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
    metadata: dict[str, str | int] = {
        'Description': (
            f'FreeSurfer {metric_info["description"]}, resampled from fsaverage '
            'to fsLR at 164k surface density.'
        ),
        'Units': metric_info['units'],
    }
    if smoothing_fwhm is not None:
        metadata['SmoothingFWHM'] = smoothing_fwhm
        metadata['SmoothingFWHMUnits'] = 'mm'
    return metadata


def parse_qcache_metric(
    metric: str,
) -> tuple[str, dict[str, str], int | None] | None:
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

    preferred_candidate = None

    # Most specific: subject[_session]_run.
    if run_id is not None:
        entities = [subject_id]
        if session_id is not None:
            entities.append(session_id)
        entities.append(run_id)
        candidate = subjects_dir / '_'.join(entities)
        preferred_candidate = candidate
        if candidate.exists():
            return candidate

    # Next: subject_session.
    if session_id is not None:
        candidate = subjects_dir / f'{subject_id}_{session_id}'
        if preferred_candidate is None:
            preferred_candidate = candidate
        if candidate.exists():
            if preferred_candidate != candidate:
                warnings.warn(
                    f'{preferred_candidate} not found; using {candidate} instead',
                    stacklevel=2,
                )
            return candidate

    # Fallback: subject.
    candidate = subjects_dir / subject_id
    if candidate.exists():
        if preferred_candidate is not None:
            warnings.warn(
                f'{preferred_candidate} not found; using {candidate} instead',
                stacklevel=2,
            )
        return candidate

    raise FileNotFoundError(
        f'No directory found for subject: {subject_id}, session: {session_id}, run: {run_id}'
    )
