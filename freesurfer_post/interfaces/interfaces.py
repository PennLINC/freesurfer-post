import json
from importlib import resources
from pathlib import Path

from nipype.interfaces.base import SimpleInterface, TraitedSpec, traits


class _SurfStatsMetadataInputSpec(TraitedSpec):
    output_dir = traits.Directory(
        desc='Output directory',
        mandatory=True,
    )
    subject_id = traits.Str(
        desc='Subject ID',
        mandatory=True,
    )


class _SurfStatsMetadataOutputSpec(TraitedSpec):
    out_file = traits.File(
        desc='Output file',
        mandatory=True,
    )


class SurfStatsMetadata(SimpleInterface):
    input_spec = _SurfStatsMetadataInputSpec
    output_spec = _SurfStatsMetadataOutputSpec

    def _run_interface(self, runtime):
        output_dir = self.inputs.output_dir
        out_file = (
            Path(output_dir)
            / self.inputs.subject_id
            / f'{self.inputs.subject_id}_surfacestats.json'
        )

        with (
            resources.files('freesurfer_post.data')
            .joinpath('surfacestats.json')
            .open('r') as f
        ):
            data = json.load(f)
            with open(out_file, 'w') as out_f:
                json.dump(data, out_f, indent=2, sort_keys=True)
        self._results['out_file'] = str(out_file)

        return runtime
