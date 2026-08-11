"""Staging of a writable copy of a FreeSurfer subject directory."""

import contextlib
import logging
import os
import shutil
from pathlib import Path

LOGGER = logging.getLogger('freesurfer_post')

# Name of the ${SUBJECTS_DIR} created inside the working directory.
STAGED_SUBJECTS_DIRNAME = 'staged_freesurfer'


def _link_fsaverage(source_subjects_dir: Path, staged_subjects_dir: Path) -> None:
    """Make ``fsaverage`` reachable from the staged ${SUBJECTS_DIR}.

    ``recon-all -qcache`` resamples to fsaverage and ``SurfaceTransform`` reads
    its annots, so both need ``$SUBJECTS_DIR/fsaverage`` to resolve. recon-all
    would create this symlink itself, but only for its own stage and only after
    deciding the target is missing, so create it up front and fail with a clear
    message when there is nothing to point at.
    """
    destination = staged_subjects_dir / 'fsaverage'
    if destination.exists():
        return

    candidates = [source_subjects_dir / 'fsaverage']
    freesurfer_home = os.getenv('FREESURFER_HOME')
    if freesurfer_home:
        candidates.append(Path(freesurfer_home) / 'subjects' / 'fsaverage')

    for candidate in candidates:
        if candidate.exists():
            # Another subject sharing this working directory may win the race.
            with contextlib.suppress(FileExistsError):
                destination.symlink_to(candidate.resolve())
            return

    searched = ', '.join(str(candidate) for candidate in candidates)
    raise FileNotFoundError(f'Could not find an fsaverage subject: {searched}')


def stage_freesurfer_dir(
    subject_freesurfer_dir: str | Path,
    working_dir: str | Path,
) -> Path:
    """Copy a FreeSurfer subject directory into the working directory.

    Every FreeSurfer step in this pipeline writes into ``$SUBJECTS_DIR``:
    ``SurfaceTransform`` adds annots to ``label/``, ``ParcellationStats`` and
    ``SegStats`` add tables to ``stats/``, and ``recon-all -qcache`` adds
    roughly 100 MB of ``*.fsaverage.mgh`` files to ``surf/`` while appending to
    ``scripts/``. Doing that in place would mutate the input dataset, which is
    typically read-only and, under BABS, a DataLad dataset that has to stay
    clean.

    The trade-off is disk: this duplicates the subject directory, on the order
    of 1-2 GB, inside the working directory.

    Parameters
    ----------
    subject_freesurfer_dir : str or Path
        Path to the subject's directory in the input ``$SUBJECTS_DIR``.
    working_dir : str or Path
        Path to the nipype working directory.

    Returns
    -------
    Path
        Path to the subject's directory in the staged ``$SUBJECTS_DIR``.
    """
    subject_freesurfer_dir = Path(subject_freesurfer_dir)
    if not subject_freesurfer_dir.is_dir():
        raise FileNotFoundError(
            f'FreeSurfer directory not found: {subject_freesurfer_dir}'
        )

    source_subjects_dir = subject_freesurfer_dir.parent
    freesurfer_id = subject_freesurfer_dir.name
    staged_subjects_dir = Path(working_dir) / STAGED_SUBJECTS_DIRNAME
    staged_freesurfer_dir = staged_subjects_dir / freesurfer_id
    staged_subjects_dir.mkdir(parents=True, exist_ok=True)

    LOGGER.info('Staging %s -> %s', subject_freesurfer_dir, staged_freesurfer_dir)
    shutil.copytree(
        subject_freesurfer_dir,
        staged_freesurfer_dir,
        dirs_exist_ok=True,
    )

    # A lock left behind by an interrupted run would make recon-all refuse to
    # start, and nothing is running in a directory we just created.
    scripts_dir = staged_freesurfer_dir / 'scripts'
    if scripts_dir.is_dir():
        for lock_file in scripts_dir.glob('IsRunning*'):
            LOGGER.info('Removing stale lock %s', lock_file)
            lock_file.unlink()

    _link_fsaverage(source_subjects_dir, staged_subjects_dir)

    return staged_freesurfer_dir
