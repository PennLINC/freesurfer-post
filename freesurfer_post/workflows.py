from pathlib import Path

import nipype.interfaces.utility as niu
import nipype.pipeline.engine as pe
from nipype.interfaces import freesurfer as fs
from nipype.interfaces.base import traits

from .interfaces import FSStats, SummarizeRegionStats, SurfStatsMetadata

# Directory in the container with the collection of annots
ANNOTS_DIR = Path('/opt/freesurfer_tabulate/annots/')

# Special atlases that we need to warp from fsaverage to native
AVAILABLE_PARCELLATIONS = [
    'AAL',
    'CC200',
    'CC400',
    'glasser',
    'gordon333dil',
    'HOCPATh25',
    'Juelich',
    'PALS_B12_Brodmann',
    'Schaefer2018_1000Parcels_7Networks_order',
    'Schaefer2018_100Parcels_7Networks_order',
    'Schaefer2018_200Parcels_7Networks_order',
    'Schaefer2018_300Parcels_7Networks_order',
    'Schaefer2018_400Parcels_7Networks_order',
    'Schaefer2018_500Parcels_7Networks_order',
    'Schaefer2018_600Parcels_7Networks_order',
    'Schaefer2018_700Parcels_7Networks_order',
    'Schaefer2018_800Parcels_7Networks_order',
    'Schaefer2018_900Parcels_7Networks_order',
    'Slab',
    'Yeo2011_17Networks_N1000',
    'Yeo2011_7Networks_N1000',
]

# Atlases that come from freesurfer and are already in fsnative
NATIVE_PARCELLATIONS = ['aparc.DKTatlas', 'aparc.a2009s', 'aparc', 'BA_exvivo']


def build_workflow(
    subject_id: str,
    session_id: str | None,
    subject_freesurfer_dir: str | Path,
    output_dir: str | Path,
    working_dir: str | Path,
):
    subject_freesurfer_dir = Path(subject_freesurfer_dir)
    subjects_dir = str(subject_freesurfer_dir.parent)
    output_dir = Path(output_dir)
    working_dir = Path(working_dir)

    workflow = pe.Workflow(name=f'freesurfer_post_{subject_id}')
    workflow.base_dir = working_dir
    workflow.config['execution'] = {'crashdump_dir': output_dir / 'crash'}
    workflow.config['execution']['crashdump_dir'] = output_dir / 'crash'
    workflow.config['execution']['crashdump_dir'] = output_dir / 'crash'

    inputnode = pe.Node(
        niu.IdentityInterface(
            fields=['subject_id', 'session_id', 'fs_subjects_dir', 'output_dir'],
        ),
        name='inputnode',
    )
    inputnode.inputs.subject_id = subject_id
    inputnode.inputs.session_id = session_id if session_id else traits.Undefined
    inputnode.inputs.fs_subjects_dir = subjects_dir
    inputnode.inputs.output_dir = output_dir

    for parc_name in AVAILABLE_PARCELLATIONS + NATIVE_PARCELLATIONS:
        parc_wf = init_parcellation_wf(
            subject_id=subject_id,
            subject_freesurfer_dir=subject_freesurfer_dir,
            parc_name=parc_name,
        )
        workflow.connect([
            (inputnode, parc_wf, [
                ('subject_id', 'inputnode.subject_id'),
                ('session_id', 'inputnode.session_id'),
                ('fs_subjects_dir', 'inputnode.fs_subjects_dir'),
                ('output_dir', 'inputnode.output_dir'),
            ]),
        ])  # fmt:skip

    # Get the segmentation stats and euler number
    fs_stats = pe.Node(FSStats(), name='fs_stats')
    workflow.connect([
        (inputnode, fs_stats, [
            ('subject_id', 'subject_id'),
            ('session_id', 'session_id'),
            ('fs_subjects_dir', 'subjects_dir'),
            ('output_dir', 'output_dir'),
        ]),
    ])  # fmt:skip

    return workflow


def init_parcellation_wf(
    subject_id: str, subject_freesurfer_dir: str | Path, parc_name: str
):
    """
    Initialize a workflow to process a single parcellation.

    Parameters
    ----------
    subject_id : str
        Subject ID. Needed to construct the bizarre input for SegStats.
    subject_freesurfer_dir : str | Path
        Path to the subject's FreeSurfer directory. May include session.
    parc_name : str
        Name of the parcellation to process.

    Inputs
    ------
    subject_id : str
        Subject ID.
    session_id : str | None
        Session ID.
    fs_subjects_dir : str
        Path to the subjects directory.
    output_dir : str | Path
        Path to the output directory.

    Returns
    -------
    workflow : pe.Workflow
        Workflow to process the parcellation.
    """
    inputnode = pe.Node(
        niu.IdentityInterface(
            fields=['subject_id', 'session_id', 'fs_subjects_dir', 'output_dir'],
        ),
        name='inputnode',
    )
    clean_parc_name = parc_name.replace('.', '').replace('_', '')
    workflow = pe.Workflow(name=f'parcellation_{clean_parc_name}')

    collect_stats = pe.Node(
        SummarizeRegionStats(
            atlas_name=parc_name,
        ),
        name='collect_stats',
    )
    surf_stats_metadata = pe.Node(
        SurfStatsMetadata(),
        name='surf_stats_metadata',
        always_run=True,
    )
    workflow.connect([
        (inputnode, collect_stats, [
            ('subject_id', 'subject_id'),
            ('session_id', 'session_id'),
            ('fs_subjects_dir', 'subjects_dir'),
            ('output_dir', 'output_dir'),
        ]),
        (inputnode, surf_stats_metadata, [
            ('output_dir', 'output_dir'),
            ('subject_id', 'subject_id'),
        ]),
    ])  # fmt:skip
    transform_nodes = {}
    parc_stats_nodes = {}
    gwr_seg_stats_nodes = {}
    for hemi in ['lh', 'rh']:
        fsaverage_annot = ANNOTS_DIR / f'{hemi}.{parc_name}.annot'
        # native annot is created by SurfaceTransform if it's not a NATIVE_PARCELLATION
        # otherwise it's already present in the subject's directory
        native_annot = subject_freesurfer_dir / 'label' / f'{hemi}.{parc_name}.annot'
        stats_file = subject_freesurfer_dir / 'stats' / f'{hemi}.{parc_name}.stats'
        gwr_stats_file = (
            subject_freesurfer_dir / 'stats' / f'{hemi}.{parc_name}.g-w.pct.stats'
        )
        if parc_name in AVAILABLE_PARCELLATIONS:
            transform_nodes[hemi] = pe.Node(
                fs.SurfaceTransform(
                    source_subject='fsaverage',
                    hemi=hemi,
                    source_annot_file=fsaverage_annot,
                    out_file=native_annot,
                ),
                name=f'{hemi}_{clean_parc_name}_transform',
            )
        else:
            transform_nodes[hemi] = pe.Node(
                niu.IdentityInterface(fields=['out_file']),
                name=f'{hemi}_{clean_parc_name}_transform',
            )
            transform_nodes[hemi].inputs.out_file = native_annot

        # mri_parcstats
        parc_stats_nodes[hemi] = pe.Node(
            fs.ParcellationStats(
                th3=True,
                copy_inputs=True,
                tabular_output=False,
                out_table=stats_file,
                args='-noglobal',
                # Mandatory for some reason
                hemisphere=hemi,
                wm=f'{subject_freesurfer_dir}/mri/wm.mgz',
                lh_white=f'{subject_freesurfer_dir}/surf/lh.white',
                rh_white=f'{subject_freesurfer_dir}/surf/rh.white',
                lh_pial=f'{subject_freesurfer_dir}/surf/lh.pial',
                rh_pial=f'{subject_freesurfer_dir}/surf/rh.pial',
                transform=f'{subject_freesurfer_dir}/mri/transforms/talairach.xfm',
                thickness=f'{subject_freesurfer_dir}/surf/{hemi}.thickness',
                brainmask=f'{subject_freesurfer_dir}/mri/brainmask.mgz',
                aseg=f'{subject_freesurfer_dir}/mri/aseg.presurf.mgz',
                ribbon=f'{subject_freesurfer_dir}/mri/ribbon.mgz',
                cortex_label=f'{subject_freesurfer_dir}/label/{hemi}.cortex.label',
            ),
            name=f'{hemi}_{clean_parc_name}_parcstats',
        )

        # mri_segstats
        gwr_seg_stats_nodes[hemi] = pe.Node(
            fs.SegStats(
                in_file=str(
                    subject_freesurfer_dir / 'surf' / f'{hemi}.w-g.pct.mgh',
                ),
                annot=(subject_id, hemi, parc_name),
                calc_snr=True,
                summary_file=gwr_stats_file,
            ),
            name=f'{hemi}_{clean_parc_name}_gwr_segstats',
        )

        workflow.connect([
            (inputnode, transform_nodes[hemi], [
                ('subject_id', 'target_subject'),
                ('fs_subjects_dir', 'subjects_dir'),
            ]),
            (inputnode, parc_stats_nodes[hemi], [
                ('subject_id', 'subject_id'),
                ('fs_subjects_dir', 'subjects_dir'),
            ]),
            (inputnode, gwr_seg_stats_nodes[hemi], [('fs_subjects_dir', 'subjects_dir')]),

            (transform_nodes[hemi], parc_stats_nodes[hemi], [('out_file', 'in_annotation')]),
            (parc_stats_nodes[hemi], collect_stats, [('out_table', f'{hemi}_stats_file')]),
            (gwr_seg_stats_nodes[hemi], collect_stats, [('summary_file', f'{hemi}_gwr_stats_file')]),
        ])  # fmt: skip

    return workflow
