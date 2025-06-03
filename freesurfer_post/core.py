"""Core processing functions for FreeSurfer post-processing."""

from pathlib import Path

import numpy as np


def process_data(
    input_path: str | Path,
    output_path: str | Path,
    subject_id: str | None = None,
    session_id: str | None = None,
    processing_level: str = 'subject',
    verbose: bool = False,
) -> dict:
    """Process FreeSurfer data with optional fMRIPrep integration.

    Parameters
    ----------
    input_path : str or Path
        Path to FreeSurfer subjects directory or specific subject
    output_path : str or Path
        Path to output directory
    subject_id : str, optional
        Subject ID to process. If None, will attempt to detect from input_path
    session_id : str, optional
        Session ID to process. If None, will attempt to detect from input_path
    processing_level : str
        Processing level to use ("subject" or "group")
    verbose : bool
        Enable verbose output

    Returns
    -------
    dict
        Processing results and metadata
    """
    input_path = Path(input_path)
    output_path = Path(output_path)

    if verbose:
        print(f'Input path: {input_path}')
        print(f'Output path: {output_path}')
        print(f'Subject ID: {subject_id}')
        print(f'Session ID: {session_id}')
        print(f'Processing level: {processing_level}')

    # Create output directory if it doesn't exist
    output_path.mkdir(parents=True, exist_ok=True)

    # Basic validation
    if not input_path.exists():
        raise FileNotFoundError(f'Input path does not exist: {input_path}')

    # Detect subject ID if not provided
    if subject_id is None:
        if input_path.is_dir() and (input_path / 'surf').exists():
            # Input path appears to be a subject directory
            subject_id = input_path.name
        else:
            raise ValueError('Could not detect subject ID. Please provide --subject-id')

    if verbose:
        print(f'Detected/using subject ID: {subject_id}')

    # TODO: Implement actual processing logic with fMRIPrep and neuromaps
    # For now, return basic metadata
    result = {
        'subject_id': subject_id,
        'session_id': session_id,
        'processing_level': processing_level,
        'input_path': str(input_path),
        'output_path': str(output_path),
        'status': 'completed',
        'processed_files': [],
    }

    # Placeholder for actual processing
    print(
        'Note: Core processing functionality will be implemented based on specific requirements'
    )

    return result


def load_surface_data(filepath: str | Path) -> np.ndarray:
    """Load surface data from various formats.

    Parameters
    ----------
    filepath : str or Path
        Path to surface data file

    Returns
    -------
    np.ndarray
        Surface data array
    """
    filepath = Path(filepath)

    if not filepath.exists():
        raise FileNotFoundError(f'File not found: {filepath}')

    # TODO: Implement loading for different formats (.mgh, .gii, etc.)
    # This would typically use nibabel or similar
    raise NotImplementedError('Surface data loading not yet implemented')


def apply_neuromaps_transform(
    data: np.ndarray, source_space: str, target_space: str
) -> np.ndarray:
    """Apply neuromaps transformation between surface spaces.

    Parameters
    ----------
    data : np.ndarray
        Source surface data
    source_space : str
        Source surface space (e.g., 'fsaverage', 'fslr32k')
    target_space : str
        Target surface space

    Returns
    -------
    np.ndarray
        Transformed surface data
    """
    # TODO: Implement neuromaps transformation
    # This would use the neuromaps package for surface-to-surface transforms
    raise NotImplementedError('Neuromaps transformation not yet implemented')


def extract_fmriprep_surfaces(fmriprep_dir: str | Path, subject_id: str) -> dict:
    """Extract surface files from fMRIPrep output.

    Parameters
    ----------
    fmriprep_dir : str or Path
        Path to fMRIPrep output directory
    subject_id : str
        Subject identifier

    Returns
    -------
    dict
        Dictionary mapping surface types to file paths
    """
    fmriprep_dir = Path(fmriprep_dir)
    subject_dir = fmriprep_dir / f'sub-{subject_id}'

    if not subject_dir.exists():
        raise FileNotFoundError(f'Subject directory not found: {subject_dir}')

    # TODO: Implement fMRIPrep surface file detection
    # Look for typical fMRIPrep surface outputs
    return {}
