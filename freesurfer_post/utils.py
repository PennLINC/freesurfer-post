"""Utility functions for FreeSurfer post-processing."""

import json
from pathlib import Path
from typing import Any

import pandas as pd


def validate_freesurfer_subject(
    subjects_dir: str | Path, subject_id: str
) -> bool:
    """Validate that a FreeSurfer subject directory exists and has expected structure.

    Parameters
    ----------
    subjects_dir : str or Path
        Path to FreeSurfer subjects directory
    subject_id : str
        Subject identifier

    Returns
    -------
    bool
        True if valid FreeSurfer subject directory
    """
    subjects_dir = Path(subjects_dir)
    subject_dir = subjects_dir / subject_id

    if not subject_dir.exists():
        return False

    # Check for essential FreeSurfer directories
    required_dirs = ['surf', 'mri', 'label']
    return all((subject_dir / dirname).exists() for dirname in required_dirs)


def find_freesurfer_subjects(subjects_dir: str | Path) -> list[str]:
    """Find all valid FreeSurfer subjects in a directory.

    Parameters
    ----------
    subjects_dir : str or Path
        Path to FreeSurfer subjects directory

    Returns
    -------
    List[str]
        List of valid subject IDs
    """
    subjects_dir = Path(subjects_dir)

    if not subjects_dir.exists():
        return []

    subjects = []
    for item in subjects_dir.iterdir():
        if item.is_dir() and validate_freesurfer_subject(subjects_dir, item.name):
            subjects.append(item.name)

    return sorted(subjects)


def save_results(
    data: dict[str, Any], output_path: str | Path, file_format: str = 'json'
) -> None:
    """Save processing results to file.

    Parameters
    ----------
    data : dict
        Data to save
    output_path : str or Path
        Output file path
    file_format : str
        Output format ("json", "csv", "pkl")
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if file_format == 'json':
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)
    elif file_format == 'csv':
        if isinstance(data, dict) and 'data' in data:
            df = pd.DataFrame(data['data'])
            df.to_csv(output_path, index=False)
        else:
            # Convert dict to DataFrame if possible
            try:
                df = pd.DataFrame([data])
                df.to_csv(output_path, index=False)
            except Exception as e:
                raise ValueError('Cannot convert data to CSV format') from e
    elif file_format == 'pkl':
        import pickle

        with open(output_path, 'wb') as f:
            pickle.dump(data, f)
    else:
        raise ValueError(f'Unsupported format: {file_format}')


def load_config(config_path: str | Path) -> dict[str, Any]:
    """Load configuration from JSON or YAML file.

    Parameters
    ----------
    config_path : str or Path
        Path to configuration file

    Returns
    -------
    dict
        Configuration dictionary
    """
    config_path = Path(config_path)

    if not config_path.exists():
        raise FileNotFoundError(f'Config file not found: {config_path}')

    if config_path.suffix == '.json':
        with open(config_path) as f:
            return json.load(f)
    elif config_path.suffix in ['.yaml', '.yml']:
        try:
            import yaml

            with open(config_path) as f:
                return yaml.safe_load(f)
        except ImportError as e:
            raise ImportError('PyYAML is required to load YAML config files') from e
    else:
        raise ValueError(f'Unsupported config file format: {config_path.suffix}')


def get_hemisphere_files(
    subject_dir: str | Path, hemisphere: str = 'both'
) -> dict[str, list[Path]]:
    """Get hemisphere-specific surface files.

    Parameters
    ----------
    subject_dir : str or Path
        Path to subject directory
    hemisphere : str
        Hemisphere ("lh", "rh", or "both")

    Returns
    -------
    dict
        Dictionary mapping hemisphere to list of surface files
    """
    subject_dir = Path(subject_dir)
    surf_dir = subject_dir / 'surf'

    if not surf_dir.exists():
        return {}

    hemisphere_files = {}

    if hemisphere in ['lh', 'both']:
        lh_files = [f for f in surf_dir.glob('lh.*') if f.is_file()]
        hemisphere_files['lh'] = lh_files

    if hemisphere in ['rh', 'both']:
        rh_files = [f for f in surf_dir.glob('rh.*') if f.is_file()]
        hemisphere_files['rh'] = rh_files

    return hemisphere_files


def setup_logging(
    verbose: bool = False, log_file: str | Path | None = None
) -> None:
    """Set up logging configuration.

    Parameters
    ----------
    verbose : bool
        Enable verbose logging
    log_file : str or Path, optional
        Path to log file
    """
    import logging

    level = logging.DEBUG if verbose else logging.INFO
    format_str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    handlers = [logging.StreamHandler()]

    if log_file:
        log_file = Path(log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file))

    logging.basicConfig(level=level, format=format_str, handlers=handlers)


def check_dependencies() -> dict[str, bool]:
    """Check if required dependencies are available.

    Returns
    -------
    dict
        Dictionary mapping package names to availability status
    """
    dependencies = {
        'numpy': False,
        'pandas': False,
        'click': False,
        'nibabel': False,
        'fmriprep': False,
        'neuromaps': False,
    }

    for package in dependencies:
        try:
            __import__(package)
            dependencies[package] = True
        except ImportError:
            pass

    return dependencies
