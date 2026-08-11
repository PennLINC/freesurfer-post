"""Tests for staging a writable copy of a FreeSurfer subject directory."""

import pytest

from freesurfer_post.prepare import STAGED_SUBJECTS_DIRNAME, stage_freesurfer_dir


def _build_subject(subjects_dir, freesurfer_id):
    subject_dir = subjects_dir / freesurfer_id
    for relative_path in ('surf/lh.white', 'mri/wm.mgz', 'scripts/recon-all.log'):
        path = subject_dir / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(relative_path)
    return subject_dir


def test_stage_copies_subject_and_leaves_input_untouched(tmp_path):
    subjects_dir = tmp_path / 'inputs'
    subject_dir = _build_subject(subjects_dir, 'sub-01_ses-02')
    (subjects_dir / 'fsaverage' / 'surf').mkdir(parents=True)
    working_dir = tmp_path / 'work'

    staged = stage_freesurfer_dir(subject_dir, working_dir)

    assert staged == working_dir / STAGED_SUBJECTS_DIRNAME / 'sub-01_ses-02'
    assert (staged / 'surf' / 'lh.white').read_text() == 'surf/lh.white'
    assert (staged / 'scripts' / 'recon-all.log').exists()

    # Writing into the copy must not reach the input dataset.
    (staged / 'surf' / 'lh.thickness.fsaverage.mgh').write_text('new')
    assert not (subject_dir / 'surf' / 'lh.thickness.fsaverage.mgh').exists()


def test_stage_links_fsaverage_from_input(tmp_path):
    subjects_dir = tmp_path / 'inputs'
    subject_dir = _build_subject(subjects_dir, 'sub-01')
    fsaverage = subjects_dir / 'fsaverage' / 'surf'
    fsaverage.mkdir(parents=True)
    (fsaverage / 'lh.white').touch()

    staged = stage_freesurfer_dir(subject_dir, tmp_path / 'work')

    staged_fsaverage = staged.parent / 'fsaverage'
    assert staged_fsaverage.is_symlink()
    assert (staged_fsaverage / 'surf' / 'lh.white').exists()


def test_stage_falls_back_to_freesurfer_home(tmp_path, monkeypatch):
    subjects_dir = tmp_path / 'inputs'
    subject_dir = _build_subject(subjects_dir, 'sub-01')
    freesurfer_home = tmp_path / 'freesurfer'
    (freesurfer_home / 'subjects' / 'fsaverage' / 'surf').mkdir(parents=True)
    monkeypatch.setenv('FREESURFER_HOME', str(freesurfer_home))

    staged = stage_freesurfer_dir(subject_dir, tmp_path / 'work')

    assert (staged.parent / 'fsaverage').resolve() == (
        freesurfer_home / 'subjects' / 'fsaverage'
    )


def test_stage_requires_an_fsaverage(tmp_path, monkeypatch):
    subjects_dir = tmp_path / 'inputs'
    subject_dir = _build_subject(subjects_dir, 'sub-01')
    monkeypatch.delenv('FREESURFER_HOME', raising=False)

    with pytest.raises(FileNotFoundError, match='fsaverage'):
        stage_freesurfer_dir(subject_dir, tmp_path / 'work')


def test_stage_removes_stale_isrunning_locks(tmp_path):
    subjects_dir = tmp_path / 'inputs'
    subject_dir = _build_subject(subjects_dir, 'sub-01')
    (subject_dir / 'scripts' / 'IsRunning.lh+rh').touch()
    (subjects_dir / 'fsaverage').mkdir()

    staged = stage_freesurfer_dir(subject_dir, tmp_path / 'work')

    assert list((staged / 'scripts').glob('IsRunning*')) == []
    # The input dataset keeps whatever it had.
    assert (subject_dir / 'scripts' / 'IsRunning.lh+rh').exists()


def test_stage_is_repeatable(tmp_path):
    subjects_dir = tmp_path / 'inputs'
    subject_dir = _build_subject(subjects_dir, 'sub-01')
    (subjects_dir / 'fsaverage').mkdir()
    working_dir = tmp_path / 'work'

    first = stage_freesurfer_dir(subject_dir, working_dir)
    second = stage_freesurfer_dir(subject_dir, working_dir)

    assert first == second
    assert (second / 'surf' / 'lh.white').exists()


def test_stage_rejects_a_missing_subject(tmp_path):
    with pytest.raises(FileNotFoundError, match='FreeSurfer directory not found'):
        stage_freesurfer_dir(tmp_path / 'inputs' / 'sub-01', tmp_path / 'work')
