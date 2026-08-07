"""Workflow construction tests."""

from freesurfer_post import workflows


def _touch(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()


def test_build_workflow_adds_run_aware_cifti_nodes(tmp_path, monkeypatch):
    subjects_dir = tmp_path / 'subjects'
    freesurfer_id = 'sub-01_ses-02_run-03'
    subject_dir = subjects_dir / freesurfer_id
    annots_dir = tmp_path / 'annots'
    output_dir = tmp_path / 'output'
    working_dir = tmp_path / 'work'
    output_dir.mkdir()
    working_dir.mkdir()

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
    assert workflow.get_node('inputnode').inputs.freesurfer_id == freesurfer_id
    assert workflow.get_node('qcache').interface.inputs.directive == 'qcache'
    assert workflow.get_node('qcache').interface.force_run is True
    assert workflow.get_node('qcache_to_cifti') is not None
