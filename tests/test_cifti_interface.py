"""Tests for the qcache-to-CIFTI interface."""

import json
from pathlib import Path

from freesurfer_post.interfaces import cifti


def _touch(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()


def test_qcache_to_cifti_writes_to_final_output(tmp_path, monkeypatch):
    subjects_dir = tmp_path / 'subjects'
    freesurfer_id = 'sub-01_ses-02_run-03'
    surface_dir = subjects_dir / freesurfer_id / 'surf'
    output_dir = tmp_path / 'output'
    work_dir = tmp_path / 'work'
    output_dir.mkdir()
    work_dir.mkdir()

    for hemi in ('lh', 'rh'):
        _touch(surface_dir / f'{hemi}.thickness.fwhm10.fsaverage.mgh')
        _touch(subjects_dir / 'fsaverage' / 'surf' / f'{hemi}.white')
    _touch(surface_dir / 'lh.pial_lgi.fsaverage.mgh')

    commands = []

    def fake_run(command, check):
        assert check is True
        commands.append(command)
        if command[0] == 'mris_convert':
            Path(command[-1]).touch()
        elif command[0] == 'wb_command':
            Path(command[2]).touch()

    def fake_resample(in_file, out_file, hemi):
        assert in_file.exists()
        assert hemi in ('L', 'R')
        out_file.touch()

    monkeypatch.setattr(cifti, 'run_command', fake_run)
    monkeypatch.setattr(cifti, '_resample_to_fslr', fake_resample)

    result = cifti.QcacheToCifti(
        subject_id='sub-01',
        session_id='ses-02',
        run_id='run-03',
        freesurfer_id=freesurfer_id,
        subjects_dir=subjects_dir,
        output_dir=output_dir,
    ).run(cwd=work_dir)

    expected_file = (
        output_dir
        / 'sub-01'
        / 'sub-01_ses-02_run-03_space-fsLR_den-164k_desc-fwhm10_thickness.dscalar.nii'
    )
    expected_sidecar = expected_file.with_name(
        'sub-01_ses-02_run-03_space-fsLR_den-164k_desc-fwhm10_thickness.json'
    )
    assert result.outputs.out_files == str(expected_file)
    assert result.outputs.out_jsons == str(expected_sidecar)
    assert expected_file.exists()
    assert expected_sidecar.exists()
    assert json.loads(expected_sidecar.read_text())['SmoothingFWHM'] == 10
    assert [command[0] for command in commands] == [
        'mris_convert',
        'mris_convert',
        'wb_command',
    ]
    assert commands[-1][2] == str(expected_file)
