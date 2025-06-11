"""Command Line Interface for FreeSurfer Post-processing Tools."""

import click

from . import __version__
from .utils import find_freesurfer_dir
from .workflows import build_workflow


@click.command()
@click.version_option(version=__version__)
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.argument('input_path', type=click.Path(exists=True))
@click.argument('output_path', type=click.Path())
@click.argument('processing_level', type=str, default='participant')
@click.option('--subjects-dir', type=click.Path(exists=True))
@click.option('--subject-id', '-s', help='Subject ID to process')
@click.option('--session-id', '-x', help='Session ID to process')
@click.option('--working-dir', '-w', help='Path to working directory')
def main(verbose, input_path, output_path, processing_level, subjects_dir, subject_id, session_id, working_dir):
    """FreeSurfer Post-processing Tools.

    A command line interface for post-processing FreeSurfer outputs.

    INPUT_PATH: Path to FreeSurfer $SUBJECTS_DIR
    OUTPUT_PATH: Path to output directory
    PROCESSING_LEVEL: Processing level to use (default: participant)
    SUBJECTS_DIR: Path to FreeSurfer $SUBJECTS_DIR
    SUBJECT_ID: Subject ID to process
    WORKING_DIR: Path to working directory
    """
    if verbose:
        click.echo('Verbose mode enabled')

    # Get the subject's freesurfer directory
    subject_fs_dir = find_freesurfer_dir(subjects_dir, subject_id, session_id)

    click.echo(f'Processing {input_path} -> {output_path}')
    click.echo(f'Subject ID: {subject_id}')
    click.echo(f'Session ID: {session_id}')
    click.echo(f'Subject directory: {subject_fs_dir}')
    click.echo(f'Processing level: {processing_level}')
    click.echo(f'Working directory: {working_dir}')

    workflow = build_workflow(
        subject_id=subject_id,
        session_id=session_id,
        subject_freesurfer_dir=subject_fs_dir,
        output_dir=output_path,
        working_dir=working_dir,
    )

    workflow.config['execution'] = {
        'stop_on_first_crash': 'true'}
    workflow.run()


if __name__ == '__main__':
    main()
