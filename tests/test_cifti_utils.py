"""Tests for CIFTI filename and qcache-pair helpers."""

import pytest

from freesurfer_post.utils import (
    QCACHE_CIFTI_METRICS,
    build_cifti_metadata,
    build_cifti_output_name,
    build_cifti_sidecar_name,
    build_output_prefix,
    find_freesurfer_dir,
    find_qcache_metric_pairs,
)


@pytest.mark.parametrize(
    ('subject_id', 'session_id', 'run_id', 'expected'),
    [
        ('sub-01', None, None, 'sub-01'),
        ('sub-01', 'ses-02', None, 'sub-01_ses-02'),
        ('sub-01', None, 'run-03', 'sub-01_run-03'),
        ('sub-01', 'ses-02', 'run-03', 'sub-01_ses-02_run-03'),
    ],
)
def test_build_output_prefix(subject_id, session_id, run_id, expected):
    assert build_output_prefix(subject_id, session_id, run_id) == expected


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
            'sub-01_ses-02_space-fsLR_den-164k_desc-fwhm0_JacobianWhite.dscalar.nii',
        ),
        ('curv', 'sub-01_ses-02_space-fsLR_den-164k_curv.dscalar.nii'),
        ('sulc', 'sub-01_ses-02_space-fsLR_den-164k_sulc.dscalar.nii'),
        (
            'thickness.fwhm15',
            'sub-01_ses-02_space-fsLR_den-164k_desc-fwhm15_thickness.dscalar.nii',
        ),
        ('volume', 'sub-01_ses-02_space-fsLR_den-164k_volume.dscalar.nii'),
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
            'at 164k surface density.'
        ),
        'Units': 'mm',
        'SmoothingFWHM': 10,
        'SmoothingFWHMUnits': 'mm',
    }


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


def test_find_qcache_metric_pairs_ignores_pial_lgi(tmp_path):
    for hemi in ('lh', 'rh'):
        (tmp_path / f'{hemi}.thickness.fwhm10.fsaverage.mgh').touch()
    (tmp_path / 'lh.pial_lgi.fsaverage.mgh').touch()

    pairs = find_qcache_metric_pairs(tmp_path)

    assert [metric for metric, _, _ in pairs] == ['thickness.fwhm10']


def test_find_qcache_metric_pairs_includes_all_requested_qcache_outputs(tmp_path):
    metrics = [
        metric
        for source_metric in QCACHE_CIFTI_METRICS
        for metric in (
            source_metric,
            *(f'{source_metric}.fwhm{fwhm}' for fwhm in (0, 5, 10, 15, 20, 25)),
        )
    ]
    for hemi in ('lh', 'rh'):
        for metric in metrics:
            (tmp_path / f'{hemi}.{metric}.fsaverage.mgh').touch()
        (tmp_path / f'{hemi}.pial_lgi.fsaverage.mgh').touch()

    pairs = find_qcache_metric_pairs(tmp_path)

    assert len(pairs) == 63
    assert all('pial_lgi' not in metric for metric, _, _ in pairs)


def test_find_qcache_metric_pairs_rejects_empty_directory(tmp_path):
    with pytest.raises(FileNotFoundError, match='No fsaverage qcache metrics'):
        find_qcache_metric_pairs(tmp_path)


def test_find_freesurfer_dir_prefers_run(tmp_path):
    run_dir = tmp_path / 'sub-01_ses-02_run-03'
    run_dir.mkdir()

    assert find_freesurfer_dir(tmp_path, 'sub-01', 'ses-02', 'run-03') == run_dir


def test_find_freesurfer_dir_finds_run_without_session(tmp_path):
    run_dir = tmp_path / 'sub-01_run-03'
    run_dir.mkdir()

    assert find_freesurfer_dir(tmp_path, 'sub-01', run_id='run-03') == run_dir


def test_find_freesurfer_dir_warns_when_falling_back_to_session(tmp_path):
    session_dir = tmp_path / 'sub-01_ses-02'
    session_dir.mkdir()

    with pytest.warns(UserWarning, match='run-03.*using.*ses-02'):
        result = find_freesurfer_dir(tmp_path, 'sub-01', 'ses-02', 'run-03')

    assert result == session_dir


def test_find_freesurfer_dir_warns_when_falling_back_to_subject(tmp_path):
    subject_dir = tmp_path / 'sub-01'
    subject_dir.mkdir()

    with pytest.warns(UserWarning, match='ses-02.*using.*sub-01'):
        result = find_freesurfer_dir(tmp_path, 'sub-01', 'ses-02')

    assert result == subject_dir
