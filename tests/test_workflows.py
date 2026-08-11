"""Workflow construction tests."""

from freesurfer_post import workflows


def _touch(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()


def _build_subject_tree(subject_dir):
    """Create the inputs nipype validates when the workflow is constructed."""
    for relative_path in (
        'mri/wm.mgz',
        'mri/brainmask.mgz',
        'mri/aseg.presurf.mgz',
        'mri/ribbon.mgz',
        'mri/transforms/talairach.xfm',
        'surf/lh.white',
        'surf/rh.white',
        'surf/lh.pial',
        'surf/rh.pial',
        'surf/lh.thickness',
        'surf/rh.thickness',
        'surf/lh.w-g.pct.mgh',
        'surf/rh.w-g.pct.mgh',
        'label/lh.cortex.label',
        'label/rh.cortex.label',
    ):
        _touch(subject_dir / relative_path)


def test_build_workflow_adds_run_aware_cifti_nodes(tmp_path, monkeypatch):
    subjects_dir = tmp_path / 'subjects'
    freesurfer_id = 'sub-01_ses-02_run-03'
    subject_dir = subjects_dir / freesurfer_id
    annots_dir = tmp_path / 'annots'
    output_dir = tmp_path / 'output'
    working_dir = tmp_path / 'work'
    output_dir.mkdir()
    working_dir.mkdir()

    _build_subject_tree(subject_dir)

    for parc_name in workflows.AVAILABLE_PARCELLATIONS:
        for hemi in ('lh', 'rh'):
            _touch(annots_dir / f'{hemi}.{parc_name}.annot')

    for parc_name in workflows.NATIVE_PARCELLATIONS:
        for hemi in ('lh', 'rh'):
            _touch(subject_dir / 'label' / f'{hemi}.{parc_name}.annot')

    monkeypatch.setattr(workflows, 'ANNOTS_DIR', annots_dir)

    workflow = workflows.build_workflow(
        subject_id='sub-01',
        session_id='ses-02',
        run_id='run-03',
        subject_freesurfer_dir=subject_dir,
        output_dir=output_dir,
        working_dir=working_dir,
    )

    assert workflow.name == f'freesurfer_post_{freesurfer_id}'
    inputnode = workflow.get_node('inputnode')
    assert inputnode.inputs.freesurfer_id == freesurfer_id
    assert inputnode.inputs.subject_id == 'sub-01'
    assert inputnode.inputs.run_id == 'run-03'
    assert workflow.get_node('qcache').interface.inputs.directive == 'qcache'
    assert workflow.get_node('qcache').interface.force_run is True
    assert workflow.get_node('qcache_to_cifti') is not None


def test_parcellation_wf_gives_freesurfer_commands_the_directory_name(tmp_path):
    """FreeSurfer commands need the directory name, not the BIDS subject ID.

    ``SegStats``'s annot tuple is baked in at construction time, so a session-
    or run-organized directory would be looked up under the wrong name if the
    BIDS ``subject_id`` were used.
    """
    freesurfer_id = 'sub-01_ses-02_run-03'
    subject_dir = tmp_path / 'subjects' / freesurfer_id
    _build_subject_tree(subject_dir)
    for hemi in ('lh', 'rh'):
        _touch(subject_dir / 'label' / f'{hemi}.aparc.annot')

    workflow = workflows.init_parcellation_wf(
        freesurfer_id=freesurfer_id,
        subject_freesurfer_dir=subject_dir,
        parc_name='aparc',
    )

    segstats = workflow.get_node('lh_aparc_gwr_segstats')
    assert segstats.interface.inputs.annot == (freesurfer_id, 'lh', 'aparc')

    # The BIDS subject_id and the directory name are separate inputnode fields.
    inputnode = workflow.get_node('inputnode')
    field_names = inputnode.interface._fields
    assert 'subject_id' in field_names
    assert 'freesurfer_id' in field_names
