"""Tests for freesurfer_post.utils module."""

import json

import pytest

from freesurfer_post.utils import (
    check_dependencies,
    find_freesurfer_subjects,
    get_hemisphere_files,
    save_results,
    validate_freesurfer_subject,
)


class TestFreeSurferValidation:
    """Test cases for FreeSurfer subject validation."""

    def test_validate_freesurfer_subject_valid(self, tmp_path):
        """Test validation with a valid FreeSurfer subject."""
        subjects_dir = tmp_path / 'subjects'
        subject_dir = subjects_dir / 'sub-01'

        # Create required directories
        (subject_dir / 'surf').mkdir(parents=True)
        (subject_dir / 'mri').mkdir(parents=True)
        (subject_dir / 'label').mkdir(parents=True)

        assert validate_freesurfer_subject(subjects_dir, 'sub-01') is True

    def test_validate_freesurfer_subject_missing_dirs(self, tmp_path):
        """Test validation with missing required directories."""
        subjects_dir = tmp_path / 'subjects'
        subject_dir = subjects_dir / 'sub-01'

        # Create only some directories
        (subject_dir / 'surf').mkdir(parents=True)
        (subject_dir / 'mri').mkdir(parents=True)
        # Missing 'label' directory

        assert validate_freesurfer_subject(subjects_dir, 'sub-01') is False

    def test_validate_freesurfer_subject_nonexistent(self, tmp_path):
        """Test validation with nonexistent subject."""
        subjects_dir = tmp_path / 'subjects'
        subjects_dir.mkdir()

        assert validate_freesurfer_subject(subjects_dir, 'nonexistent') is False

    def test_find_freesurfer_subjects(self, tmp_path):
        """Test finding FreeSurfer subjects in a directory."""
        subjects_dir = tmp_path / 'subjects'

        # Create valid subjects
        for subject_id in ['sub-01', 'sub-02']:
            subject_dir = subjects_dir / subject_id
            (subject_dir / 'surf').mkdir(parents=True)
            (subject_dir / 'mri').mkdir(parents=True)
            (subject_dir / 'label').mkdir(parents=True)

        # Create invalid subject (missing directories)
        invalid_subject = subjects_dir / 'invalid'
        invalid_subject.mkdir(parents=True)

        # Create non-directory item
        (subjects_dir / 'file.txt').touch()

        subjects = find_freesurfer_subjects(subjects_dir)
        assert subjects == ['sub-01', 'sub-02']

    def test_find_freesurfer_subjects_empty_dir(self, tmp_path):
        """Test finding subjects in empty directory."""
        subjects_dir = tmp_path / 'empty'
        subjects_dir.mkdir()

        subjects = find_freesurfer_subjects(subjects_dir)
        assert subjects == []

    def test_find_freesurfer_subjects_nonexistent_dir(self, tmp_path):
        """Test finding subjects in nonexistent directory."""
        nonexistent_dir = tmp_path / 'nonexistent'

        subjects = find_freesurfer_subjects(nonexistent_dir)
        assert subjects == []


class TestSaveResults:
    """Test cases for saving results to different formats."""

    def test_save_results_json(self, tmp_path):
        """Test saving results as JSON."""
        data = {'test': 'value', 'number': 42}
        output_file = tmp_path / 'results.json'

        save_results(data, output_file, format='json')

        assert output_file.exists()
        with open(output_file) as f:
            loaded_data = json.load(f)
        assert loaded_data == data

    def test_save_results_csv_with_dataframe_data(self, tmp_path):
        """Test saving results as CSV with DataFrame-compatible data."""
        data = {'data': [{'col1': 1, 'col2': 'a'}, {'col1': 2, 'col2': 'b'}]}
        output_file = tmp_path / 'results.csv'

        save_results(data, output_file, format='csv')

        assert output_file.exists()
        # Basic check that file was created (detailed CSV testing would require pandas)

    def test_save_results_pickle(self, tmp_path):
        """Test saving results as pickle."""
        data = {'test': 'value', 'complex': [1, 2, {'nested': True}]}
        output_file = tmp_path / 'results.pkl'

        save_results(data, output_file, format='pkl')

        assert output_file.exists()
        # Basic check that file was created

    def test_save_results_unsupported_format(self, tmp_path):
        """Test error with unsupported format."""
        data = {'test': 'value'}
        output_file = tmp_path / 'results.xyz'

        with pytest.raises(ValueError, match='Unsupported format'):
            save_results(data, output_file, format='xyz')


class TestHemisphereFiles:
    """Test cases for hemisphere file handling."""

    def test_get_hemisphere_files_both(self, tmp_path):
        """Test getting files for both hemispheres."""
        subject_dir = tmp_path / 'sub-01'
        surf_dir = subject_dir / 'surf'
        surf_dir.mkdir(parents=True)

        # Create some hemisphere files
        (surf_dir / 'lh.pial').touch()
        (surf_dir / 'lh.white').touch()
        (surf_dir / 'rh.pial').touch()
        (surf_dir / 'rh.white').touch()
        (surf_dir / 'other.file').touch()  # Should be ignored

        files = get_hemisphere_files(subject_dir, hemisphere='both')

        assert 'lh' in files
        assert 'rh' in files
        assert len(files['lh']) == 2
        assert len(files['rh']) == 2

    def test_get_hemisphere_files_left_only(self, tmp_path):
        """Test getting files for left hemisphere only."""
        subject_dir = tmp_path / 'sub-01'
        surf_dir = subject_dir / 'surf'
        surf_dir.mkdir(parents=True)

        (surf_dir / 'lh.pial').touch()
        (surf_dir / 'rh.pial').touch()

        files = get_hemisphere_files(subject_dir, hemisphere='lh')

        assert 'lh' in files
        assert 'rh' not in files
        assert len(files['lh']) == 1

    def test_get_hemisphere_files_no_surf_dir(self, tmp_path):
        """Test getting files when surf directory doesn't exist."""
        subject_dir = tmp_path / 'sub-01'
        subject_dir.mkdir()

        files = get_hemisphere_files(subject_dir)
        assert files == {}


class TestDependencyCheck:
    """Test cases for dependency checking."""

    def test_check_dependencies(self):
        """Test dependency checking function."""
        dependencies = check_dependencies()

        assert isinstance(dependencies, dict)
        assert 'numpy' in dependencies
        assert 'pandas' in dependencies
        assert 'click' in dependencies

        # These should be True since they're required dependencies
        assert dependencies['numpy'] is True
        assert dependencies['pandas'] is True
        assert dependencies['click'] is True
