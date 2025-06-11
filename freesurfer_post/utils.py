"""Utility functions for FreeSurfer post-processing."""

import warnings
from pathlib import Path


def find_freesurfer_dir(
    subjects_dir: str | Path, subject_id: str, session_id: str | None = None
) -> Path:
    """Find a valid FreeSurfer subject directory in a directory.

    Parameters
    ----------
    subjects_dir : str or Path
        Path to FreeSurfer subjects directory
    subject_id : str
        Subject identifier
    session_id : str, optional
        Session identifier

    Returns
    -------
    Path
        Path to valid FreeSurfer subject directory
    """
    subjects_dir = Path(subjects_dir)

    if not subjects_dir.exists():
        raise FileNotFoundError(f'Subjects directory {subjects_dir} does not exist')

    warn_no_session = False
    if session_id is not None:
        if (subjects_dir / f'{subject_id}_{session_id}').exists():
            return subjects_dir / f'{subject_id}_{session_id}'
        warn_no_session = True

    if (subjects_dir / subject_id).exists():
        if warn_no_session:
            warnings.warn(
                f'{subjects_dir}/{subject_id}_{session_id} not found in {subjects_dir}'
                f'using {subjects_dir}/{subject_id} instead',
                stacklevel=2,
            )
        return subjects_dir / subject_id
    raise FileNotFoundError(
        f'No directory found for subject: {subject_id}, session: {session_id}'
    )
