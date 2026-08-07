"""Interfaces for converting FreeSurfer qcache metrics to CIFTI files."""

import json
import os
from pathlib import Path
from subprocess import run as run_command

from nipype.interfaces.base import (
    File,
    OutputMultiPath,
    SimpleInterface,
    TraitedSpec,
    isdefined,
    traits,
)

from ..utils import (
    build_cifti_metadata,
    build_cifti_output_name,
    build_cifti_sidecar_name,
    build_output_prefix,
    find_qcache_metric_pairs,
)


class _QcacheToCiftiInputSpec(TraitedSpec):
    subject_id = traits.Str(desc='BIDS subject ID', mandatory=True)
    session_id = traits.Str(desc='BIDS session ID', mandatory=False)
    run_id = traits.Str(desc='BIDS run ID', mandatory=False)
    freesurfer_id = traits.Str(desc='FreeSurfer directory name', mandatory=True)
    subjects_dir = traits.Directory(
        desc='Path to the FreeSurfer subjects directory',
        exists=True,
        mandatory=True,
    )
    output_dir = traits.Directory(
        desc='Path to the final output directory',
        exists=True,
        mandatory=True,
    )


class _QcacheToCiftiOutputSpec(TraitedSpec):
    out_files = OutputMultiPath(
        File(exists=True),
        desc='fsLR 164k CIFTI dense scalar files',
    )
    out_jsons = OutputMultiPath(
        File(exists=True),
        desc='JSON sidecars for the fsLR 164k CIFTI dense scalar files',
    )


def _get_fsaverage_white(subjects_dir: Path, hemi: str) -> Path:
    """Locate the fsaverage white surface used by ``mris_convert``."""
    candidates = [subjects_dir / 'fsaverage' / 'surf' / f'{hemi}.white']
    freesurfer_home = os.getenv('FREESURFER_HOME')
    if freesurfer_home:
        candidates.append(
            Path(freesurfer_home) / 'subjects' / 'fsaverage' / 'surf' / f'{hemi}.white'
        )

    for candidate in candidates:
        if candidate.exists():
            return candidate

    searched = ', '.join(str(candidate) for candidate in candidates)
    raise FileNotFoundError(
        f'Could not find the fsaverage {hemi} white surface: {searched}'
    )


def _resample_to_fslr(in_file: Path, out_file: Path, hemi: str) -> None:
    """Resample one fsaverage metric to fsLR 164k with neuromaps."""
    from neuromaps.transforms import fsaverage_to_fslr

    (resampled_image,) = fsaverage_to_fslr(
        str(in_file),
        target_density='164k',
        hemi=hemi,
        method='linear',
    )
    resampled_image.to_filename(out_file)


class QcacheToCifti(SimpleInterface):
    """Convert paired FreeSurfer qcache metrics to fsLR 164k CIFTIs."""

    input_spec = _QcacheToCiftiInputSpec
    output_spec = _QcacheToCiftiOutputSpec

    def _run_interface(self, runtime):
        subjects_dir = Path(self.inputs.subjects_dir)
        surface_dir = subjects_dir / self.inputs.freesurfer_id / 'surf'
        metric_pairs = find_qcache_metric_pairs(surface_dir)

        session_id = (
            self.inputs.session_id if isdefined(self.inputs.session_id) else None
        )
        run_id = self.inputs.run_id if isdefined(self.inputs.run_id) else None
        output_prefix = build_output_prefix(
            self.inputs.subject_id,
            session_id,
            run_id,
        )
        output_dir = Path(self.inputs.output_dir) / self.inputs.subject_id
        output_dir.mkdir(parents=True, exist_ok=True)

        work_dir = Path(runtime.cwd)
        fsaverage_surfaces = {
            hemi: _get_fsaverage_white(subjects_dir, hemi) for hemi in ('lh', 'rh')
        }
        out_files = []
        out_jsons = []
        for metric, lh_mgh, rh_mgh in metric_pairs:
            resampled_metrics = {}
            for hemi, mgh_file, neuromaps_hemi in (
                ('lh', lh_mgh, 'L'),
                ('rh', rh_mgh, 'R'),
            ):
                fsaverage_gii = work_dir / f'{hemi}.{metric}.fsaverage.shape.gii'
                fslr_gii = work_dir / f'{hemi}.{metric}.fsLR_den-164k.shape.gii'
                run_command(
                    [
                        'mris_convert',
                        '-c',
                        str(mgh_file),
                        str(fsaverage_surfaces[hemi]),
                        str(fsaverage_gii),
                    ],
                    check=True,
                )
                _resample_to_fslr(fsaverage_gii, fslr_gii, neuromaps_hemi)
                resampled_metrics[hemi] = fslr_gii

            cifti_file = output_dir / build_cifti_output_name(output_prefix, metric)
            run_command(
                [
                    'wb_command',
                    '-cifti-create-dense-scalar',
                    str(cifti_file),
                    '-left-metric',
                    str(resampled_metrics['lh']),
                    '-right-metric',
                    str(resampled_metrics['rh']),
                ],
                check=True,
            )
            out_files.append(str(cifti_file))

            sidecar_file = output_dir / build_cifti_sidecar_name(cifti_file.name)
            with sidecar_file.open('w') as sidecar:
                json.dump(build_cifti_metadata(metric), sidecar, indent=2)
                sidecar.write('\n')
            out_jsons.append(str(sidecar_file))

        self._results['out_files'] = out_files
        self._results['out_jsons'] = out_jsons
        return runtime
