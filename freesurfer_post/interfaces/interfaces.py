from nipype.interfaces.base import SimpleInterface, TraitedSpec, traits


class _WaitingInputSpec(TraitedSpec):
    inputs = traits.Any(
        desc='Inputs to wait for',
        mandatory=True,
    )

class _WaitingOutputSpec(TraitedSpec):
    no_args = traits.Str(
        desc='No args',
        mandatory=True,
    )

class Waiting(SimpleInterface):
    # Force a bunch of nodes to finish and then retuen an empty string
    # to put in "args" of the dependent workflow
    input_spec = _WaitingInputSpec
    output_spec = _WaitingOutputSpec

    def _run_interface(self, runtime):
        self._results['no_args'] = ''
        return runtime
