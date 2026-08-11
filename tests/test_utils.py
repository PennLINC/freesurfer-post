"""Tests for freesurfer_post.utils helpers that are not CIFTI-specific."""

import warnings

import pytest

from freesurfer_post.utils import build_output_prefix, find_freesurfer_dir


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


def test_find_freesurfer_dir_prefers_run(tmp_path):
    run_dir = tmp_path / 'sub-01_ses-02_run-03'
    run_dir.mkdir()
    (tmp_path / 'sub-01_ses-02').mkdir()
    (tmp_path / 'sub-01').mkdir()

    assert find_freesurfer_dir(tmp_path, 'sub-01', 'ses-02', 'run-03') == run_dir


def test_find_freesurfer_dir_finds_run_without_session(tmp_path):
    run_dir = tmp_path / 'sub-01_run-03'
    run_dir.mkdir()

    assert find_freesurfer_dir(tmp_path, 'sub-01', run_id='run-03') == run_dir


def test_find_freesurfer_dir_finds_sessionless_run_dir(tmp_path):
    """A session may be requested even when the directory omits it."""
    run_dir = tmp_path / 'sub-01_run-03'
    run_dir.mkdir()

    with pytest.warns(UserWarning, match='ses-02_run-03.*using.*sub-01_run-03'):
        result = find_freesurfer_dir(tmp_path, 'sub-01', 'ses-02', 'run-03')

    assert result == run_dir


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


def test_find_freesurfer_dir_does_not_warn_without_entities(tmp_path):
    subject_dir = tmp_path / 'sub-01'
    subject_dir.mkdir()

    with warnings.catch_warnings():
        warnings.simplefilter('error')
        assert find_freesurfer_dir(tmp_path, 'sub-01') == subject_dir


def test_find_freesurfer_dir_lists_candidates_when_missing(tmp_path):
    with pytest.raises(FileNotFoundError, match='Searched:.*sub-01_ses-02_run-03'):
        find_freesurfer_dir(tmp_path, 'sub-01', 'ses-02', 'run-03')


def test_find_freesurfer_dir_requires_subjects_dir(tmp_path):
    with pytest.raises(FileNotFoundError, match='does not exist'):
        find_freesurfer_dir(tmp_path / 'nope', 'sub-01')
