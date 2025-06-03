"""Tests for freesurfer_post.core module."""

from pathlib import Path

import pytest

from freesurfer_post.core import process_data


class TestProcessData:
    """Test cases for process_data function."""

    def test_process_data_with_valid_inputs(self, tmp_path):
        """Test process_data with valid inputs."""
        # Create temporary input and output directories
        input_dir = tmp_path / 'input'
        output_dir = tmp_path / 'output'
        input_dir.mkdir()

        # Create a mock surf directory to simulate FreeSurfer structure
        surf_dir = input_dir / 'surf'
        surf_dir.mkdir()

        result = process_data(
            input_path=input_dir,
            output_path=output_dir,
            subject_id='test_subject',
            hemisphere='both',
            verbose=False,
        )

        assert result['subject_id'] == 'test_subject'
        assert result['status'] == 'completed'
        assert Path(result['output_path']) == output_dir
        assert output_dir.exists()

    def test_process_data_nonexistent_input(self, tmp_path):
        """Test process_data with nonexistent input path."""
        input_dir = tmp_path / 'nonexistent'
        output_dir = tmp_path / 'output'

        with pytest.raises(FileNotFoundError):
            process_data(
                input_path=input_dir, output_path=output_dir, subject_id='test_subject'
            )

    def test_process_data_auto_detect_subject_id(self, tmp_path):
        """Test automatic subject ID detection."""
        # Create a directory structure that looks like a subject directory
        subject_dir = tmp_path / 'sub-01'
        surf_dir = subject_dir / 'surf'
        surf_dir.mkdir(parents=True)

        output_dir = tmp_path / 'output'

        result = process_data(
            input_path=subject_dir,
            output_path=output_dir,
            subject_id=None,  # Should auto-detect
            hemisphere='lh',
        )

        assert result['subject_id'] == 'sub-01'
        assert result['hemisphere'] == 'lh'

    def test_process_data_missing_subject_id(self, tmp_path):
        """Test error when subject ID cannot be detected."""
        # Create a directory that doesn't look like a subject directory
        input_dir = tmp_path / 'not_a_subject'
        input_dir.mkdir()
        output_dir = tmp_path / 'output'

        with pytest.raises(ValueError, match='Could not detect subject ID'):
            process_data(input_path=input_dir, output_path=output_dir, subject_id=None)


# Placeholder tests for other functions
class TestSurfaceDataLoading:
    """Test cases for surface data loading functions."""

    def test_load_surface_data_not_implemented(self):
        """Test that load_surface_data raises NotImplementedError."""
        from freesurfer_post.core import load_surface_data

        with pytest.raises(NotImplementedError):
            load_surface_data('dummy_path.mgh')


class TestNeuromapsTransform:
    """Test cases for neuromaps transformation functions."""

    def test_apply_neuromaps_transform_not_implemented(self):
        """Test that apply_neuromaps_transform raises NotImplementedError."""
        import numpy as np

        from freesurfer_post.core import apply_neuromaps_transform

        dummy_data = np.array([1, 2, 3])

        with pytest.raises(NotImplementedError):
            apply_neuromaps_transform(dummy_data, 'fsaverage', 'fslr32k')


class TestFMRIPrepIntegration:
    """Test cases for fMRIPrep integration functions."""

    def test_extract_fmriprep_surfaces_missing_subject(self, tmp_path):
        """Test extract_fmriprep_surfaces with missing subject directory."""
        from freesurfer_post.core import extract_fmriprep_surfaces

        fmriprep_dir = tmp_path / 'fmriprep'
        fmriprep_dir.mkdir()

        with pytest.raises(FileNotFoundError):
            extract_fmriprep_surfaces(fmriprep_dir, 'sub-01')
