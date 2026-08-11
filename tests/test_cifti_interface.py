"""Tests for the qcache-to-CIFTI interface."""

import json
import subprocess
from pathlib import Path

import pytest

from freesurfer_post.interfaces import cifti


def _touch(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()


def _fake_runner(commands, returncode=0, stderr=''):
    """Build a ``subprocess.run`` stand-in that records its invocations."""

    def fake_run(command, capture_output, text, check):
        assert capture_output is True
        assert text is True
        # The return code is inspected explicitly so that stderr can be
        # included in the error, so check must stay off.
        assert check is False
        commands.append(command)
        if returncode == 0:
            if command[0] == 'mris_convert':
                Path(command[-1]).touch()
            elif command[0] == 'wb_command':
                Path(command[2]).touch()
        return subprocess.CompletedProcess(
            command, returncode, stdout='some stdout', stderr=stderr
        )

    return fake_run


def _fake_resample(in_file, out_file, hemi):
    assert in_file.exists()
    assert hemi in ('L', 'R')
    out_file.touch()


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
    monkeypatch.setattr(cifti, 'run_command', _fake_runner(commands))
    monkeypatch.setattr(cifti, '_resample_to_fslr', _fake_resample)

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
    # The dense scalar's map is named after the metric; without -name-file
    # wb_command would call it '#1'.
    assert commands[-1][-2] == '-name-file'
    assert Path(commands[-1][-1]).name == 'thickness.fwhm10.map-name.txt'


def test_qcache_to_cifti_removes_intermediate_giftis(tmp_path, monkeypatch):
    subjects_dir = tmp_path / 'subjects'
    freesurfer_id = 'sub-01'
    surface_dir = subjects_dir / freesurfer_id / 'surf'
    output_dir = tmp_path / 'output'
    work_dir = tmp_path / 'work'
    output_dir.mkdir()
    work_dir.mkdir()

    for hemi in ('lh', 'rh'):
        _touch(surface_dir / f'{hemi}.thickness.fsaverage.mgh')
        _touch(surface_dir / f'{hemi}.sulc.fwhm5.fsaverage.mgh')
        _touch(subjects_dir / 'fsaverage' / 'surf' / f'{hemi}.white')

    monkeypatch.setattr(cifti, 'run_command', _fake_runner([]))
    monkeypatch.setattr(cifti, '_resample_to_fslr', _fake_resample)

    cifti.QcacheToCifti(
        subject_id='sub-01',
        freesurfer_id=freesurfer_id,
        subjects_dir=subjects_dir,
        output_dir=output_dir,
    ).run(cwd=work_dir)

    assert sorted(path.name for path in output_dir.glob('sub-01/*')) == [
        'sub-01_space-fsLR_den-164k_desc-fwhm5_sulc.dscalar.nii',
        'sub-01_space-fsLR_den-164k_desc-fwhm5_sulc.json',
        'sub-01_space-fsLR_den-164k_thickness.dscalar.nii',
        'sub-01_space-fsLR_den-164k_thickness.json',
    ]
    # No GIFTIs or map-name files are left behind in the working directory.
    assert list(work_dir.iterdir()) == []


def test_qcache_to_cifti_reports_command_output_on_failure(tmp_path, monkeypatch):
    subjects_dir = tmp_path / 'subjects'
    freesurfer_id = 'sub-01'
    surface_dir = subjects_dir / freesurfer_id / 'surf'
    output_dir = tmp_path / 'output'
    work_dir = tmp_path / 'work'
    output_dir.mkdir()
    work_dir.mkdir()

    for hemi in ('lh', 'rh'):
        _touch(surface_dir / f'{hemi}.thickness.fsaverage.mgh')
        _touch(subjects_dir / 'fsaverage' / 'surf' / f'{hemi}.white')

    monkeypatch.setattr(
        cifti,
        'run_command',
        _fake_runner([], returncode=1, stderr='no such surface'),
    )

    with pytest.raises(RuntimeError, match='no such surface'):
        cifti.QcacheToCifti(
            subject_id='sub-01',
            freesurfer_id=freesurfer_id,
            subjects_dir=subjects_dir,
            output_dir=output_dir,
        ).run(cwd=work_dir)
