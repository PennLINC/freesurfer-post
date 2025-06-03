"""Command Line Interface for FreeSurfer Post-processing Tools."""

import click

from . import __version__
from .core import process_data


@click.group()
@click.version_option(version=__version__)
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.pass_context
def main(ctx, verbose):
    """FreeSurfer Post-processing Tools.

    A command line interface for post-processing FreeSurfer outputs.
    """
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose

    if verbose:
        click.echo('Verbose mode enabled')


@main.command()
@click.argument('input_path', type=click.Path(exists=True))
@click.argument('output_path', type=click.Path())
@click.argument('processing_level', type=str, default='subject')
@click.option('--subject-id', '-s', help='Subject ID to process')
@click.option('--session-id', '-s', help='Session ID to process')
@click.pass_context
def process(ctx, input_path, output_path, subject_id, session_id, processing_level):
    """Process FreeSurfer data.

    INPUT_PATH: Path to FreeSurfer $SUBJECTS_DIR
    OUTPUT_PATH: Path to output directory
    SUBJECT_ID: Subject ID to process
    SESSION_ID: Session ID to process
    PROCESSING_LEVEL: Processing level to use (default: subject)
    """
    verbose = ctx.obj.get('verbose', False)

    if verbose:
        click.echo(f'Processing {input_path} -> {output_path}')
        click.echo(f'Subject ID: {subject_id}')

    try:
        result = process_data(
            input_path=input_path,
            output_path=output_path,
            subject_id=subject_id,
            session_id=session_id,
            processing_level=processing_level,
            verbose=verbose,
        )
        click.echo(f'Processing completed successfully: {result}')
    except Exception as e:
        click.echo(f'Error: {e}', err=True)
        raise click.Abort from e


@main.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.option(
    '--atlas', '-a', default='DKT', help='Atlas to use for mapping (default: DKT)'
)
@click.option(
    '--output-format',
    '-f',
    type=click.Choice(['csv', 'json', 'nifti']),
    default='csv',
    help='Output format (default: csv)',
)
@click.pass_context
def map_to_atlas(ctx, input_file, atlas, output_format):
    """Map surface data to atlas parcellation.

    INPUT_FILE: Path to surface data file (e.g., .mgh, .gii)
    """
    verbose = ctx.obj.get('verbose', False)

    if verbose:
        click.echo(f'Mapping {input_file} to {atlas} atlas')
        click.echo(f'Output format: {output_format}')

    click.echo('Atlas mapping functionality coming soon!')


if __name__ == '__main__':
    main()
