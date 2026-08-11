"""Tests for CIFTI filename and qcache-pair helpers."""

import pytest

from freesurfer_post.utils import (
    QCACHE_CIFTI_METRICS,
    build_cifti_metadata,
    build_cifti_output_name,
    build_cifti_sidecar_name,
    find_qcache_metric_pairs,
)

QCACHE_FWHMS = (0, 5, 10, 15, 20, 25)


@pytest.mark.parametrize(
    ('metric', 'expected'),
    [
        ('area', 'sub-01_ses-02_space-fsLR_den-164k_area.dscalar.nii'),
        (
            'area.pial.fwhm25',
            'sub-01_ses-02_space-fsLR_den-164k_desc-fwhm25_areaPial.dscalar.nii',
        ),
        (
            'jacobian_white.fwhm0',
            'sub-01_ses-02_space-fsLR_den-164k_desc-fwhm0_jacobianWhite.dscalar.nii',
        ),
        ('curv', 'sub-01_ses-02_space-fsLR_den-164k_curv.dscalar.nii'),
        ('sulc', 'sub-01_ses-02_space-fsLR_den-164k_sulc.dscalar.nii'),
        (
            'thickness.fwhm15',
            'sub-01_ses-02_space-fsLR_den-164k_desc-fwhm15_thickness.dscalar.nii',
        ),
        ('volume', 'sub-01_ses-02_space-fsLR_den-164k_volume.dscalar.nii'),
        # recon-all's measure name keeps its .mgh extension.
        ('w-g.pct.mgh', 'sub-01_ses-02_space-fsLR_den-164k_wgPct.dscalar.nii'),
        (
            'w-g.pct.mgh.fwhm10',
            'sub-01_ses-02_space-fsLR_den-164k_desc-fwhm10_wgPct.dscalar.nii',
        ),
        (
            'white.H.fwhm5',
            'sub-01_ses-02_space-fsLR_den-164k_desc-fwhm5_whiteH.dscalar.nii',
        ),
        (
            'white.K.fwhm10',
            'sub-01_ses-02_space-fsLR_den-164k_desc-fwhm10_whiteK.dscalar.nii',
        ),
    ],
)
def test_build_cifti_output_name(metric, expected):
    assert build_cifti_output_name('sub-01_ses-02', metric) == expected


@pytest.mark.parametrize('metric', ['pial_lgi', 'pial_lgi.fwhm10', 'nonsense'])
def test_build_cifti_output_name_rejects_unsupported(metric):
    with pytest.raises(ValueError, match='Unsupported qcache metric'):
        build_cifti_output_name('sub-01', metric)


def test_build_cifti_sidecar_name():
    assert (
        build_cifti_sidecar_name('sub-01_space-fsLR_den-164k_thickness.dscalar.nii')
        == 'sub-01_space-fsLR_den-164k_thickness.json'
    )


def test_build_cifti_metadata_records_smoothing():
    metadata = build_cifti_metadata('thickness.fwhm10')

    assert metadata == {
        'Description': (
            'FreeSurfer cortical thickness, resampled from fsaverage to fsLR '
            'at 164k surface density with area-adaptive barycentric '
            'interpolation.'
        ),
        'Units': 'mm',
        'SmoothingFWHM': 10,
        'SmoothingFWHMUnits': 'mm',
    }


def test_build_cifti_metadata_omits_smoothing_for_native_metric():
    metadata = build_cifti_metadata('curv')

    assert 'SmoothingFWHM' not in metadata
    assert metadata['Units'] == 'mm^-1'


@pytest.mark.parametrize('metric', ['area', 'area.pial', 'volume'])
def test_build_cifti_metadata_flags_non_conserved_metrics(metric):
    """Interpolated areas and volumes do not sum to the native-surface total."""
    assert 'not conserved' in build_cifti_metadata(metric)['Description']


@pytest.mark.parametrize('metric', ['thickness', 'curv', 'sulc'])
def test_build_cifti_metadata_omits_caveat_for_intensive_metrics(metric):
    assert 'not conserved' not in build_cifti_metadata(metric)['Description']


def test_find_qcache_metric_pairs(tmp_path):
    expected_metrics = ['area.fwhm0', 'thickness.fwhm10']
    for hemi in ('lh', 'rh'):
        for metric in expected_metrics:
            (tmp_path / f'{hemi}.{metric}.fsaverage.mgh').touch()

    pairs = find_qcache_metric_pairs(tmp_path)

    assert [metric for metric, _, _ in pairs] == expected_metrics
    assert all(lh_file.name.startswith('lh.') for _, lh_file, _ in pairs)
    assert all(rh_file.name.startswith('rh.') for _, _, rh_file in pairs)


def test_find_qcache_metric_pairs_rejects_unpaired_metric(tmp_path):
    (tmp_path / 'lh.thickness.fwhm10.fsaverage.mgh').touch()

    with pytest.raises(FileNotFoundError, match='Unpaired.*thickness.fwhm10'):
        find_qcache_metric_pairs(tmp_path)


def test_find_qcache_metric_pairs_ignores_pial_lgi(tmp_path, caplog):
    for hemi in ('lh', 'rh'):
        (tmp_path / f'{hemi}.thickness.fwhm10.fsaverage.mgh').touch()
    (tmp_path / 'lh.pial_lgi.fsaverage.mgh').touch()

    with caplog.at_level('INFO', logger='nipype.interface'):
        pairs = find_qcache_metric_pairs(tmp_path)

    assert [metric for metric, _, _ in pairs] == ['thickness.fwhm10']
    # Dropped metrics are logged, so a hole in the allowlist is not silent.
    assert 'pial_lgi' in caplog.text


def test_find_qcache_metric_pairs_covers_the_recon_all_measure_list(tmp_path):
    """Every measure in recon-all's qcache ``measurelist`` is converted."""
    metrics = [
        metric
        for source_metric in QCACHE_CIFTI_METRICS
        for metric in (
            source_metric,
            *(f'{source_metric}.fwhm{fwhm}' for fwhm in QCACHE_FWHMS),
        )
    ]
    for hemi in ('lh', 'rh'):
        for metric in metrics:
            (tmp_path / f'{hemi}.{metric}.fsaverage.mgh').touch()
        (tmp_path / f'{hemi}.pial_lgi.fsaverage.mgh').touch()

    pairs = find_qcache_metric_pairs(tmp_path)

    assert len(QCACHE_CIFTI_METRICS) == 10
    assert len(pairs) == len(QCACHE_CIFTI_METRICS) * (len(QCACHE_FWHMS) + 1)
    assert all('pial_lgi' not in metric for metric, _, _ in pairs)


def test_cifti_suffixes_are_unique_and_alphanumeric():
    """Suffixes are the output contract, so they must be valid and distinct."""
    suffixes = [info['suffix'] for info in QCACHE_CIFTI_METRICS.values()]

    assert len(set(suffixes)) == len(suffixes)
    assert all(suffix.isalnum() for suffix in suffixes)
    assert all(suffix[0].islower() for suffix in suffixes)


def test_find_qcache_metric_pairs_rejects_empty_directory(tmp_path):
    with pytest.raises(FileNotFoundError, match='No fsaverage qcache metrics'):
        find_qcache_metric_pairs(tmp_path)
