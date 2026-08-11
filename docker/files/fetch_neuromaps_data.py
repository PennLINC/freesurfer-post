"""Pre-fetch the neuromaps atlases needed for fsaverage -> fsLR 164k.

neuromaps downloads its spheres, vertex-area and medial-wall files from OSF the
first time a transform runs. Doing that at build time means the pipeline needs
no network access, and keeps the data out of ``$HOME``, which is not writable
under ``apptainer --containall``.

Run with ``NEUROMAPS_DATA`` already set to the target directory. Exits non-zero
if the download did not produce the files the transform will look for, so that a
broken fetch fails the image build rather than every subject.
"""

import sys
from pathlib import Path

from neuromaps.datasets import fetch_atlas, get_atlas_dir

DENSITY = '164k'
SPACES = ('fsaverage', 'fsLR')

for space in SPACES:
    fetch_atlas(space, DENSITY)

missing = []
for space in SPACES:
    atlas_dir = Path(get_atlas_dir(space))
    for hemi in ('L', 'R'):
        # _surf_to_surf needs a sphere, a vertex-area midthickness and a medial
        # wall label per hemisphere. Match on the parts of the names that are
        # stable across neuromaps versions.
        patterns = [
            f'*_den-{DENSITY}_hemi-{hemi}_sphere.surf.gii',
            f'*_den-{DENSITY}_hemi-{hemi}_desc-vaavg_midthickness.shape.gii',
            f'*_den-{DENSITY}_hemi-{hemi}_desc-nomedialwall_dparc.label.gii',
        ]
        for pattern in patterns:
            if not list(atlas_dir.glob(pattern)):
                missing.append(f'{atlas_dir}/{pattern}')

if missing:
    sys.exit(
        'neuromaps pre-fetch did not produce the expected files:\n  '
        + '\n  '.join(missing)
    )

print(f'Pre-fetched neuromaps {DENSITY} atlases for: {", ".join(SPACES)}')
