#!/bin/bash
# Manual smoke tests. The first invocation mounts the local checkout over the
# installed package so that edits take effect without rebuilding the image; the
# second runs whatever is baked into the image.

common_args=(
   --platform linux/amd64
   -v /Users/mcieslak/Desktop/fmriprep_anat:/data
   -v /Users/mcieslak/Desktop/freesurfer_post:/output
   -v /Users/mcieslak/Desktop/fspost_work:/work
   --mount type=bind,source=/Users/mcieslak/Desktop/license.txt,target=/opt/fs_license.txt
)

fspost_args=(
   /data
   /output
   participant
   --subjects-dir /data/sourcedata/freesurfer
   --subject-id sub-colornest001
   --fs-license-file /opt/fs_license.txt
   -w /work
)

# Run against the local checkout.
docker run --rm -ti "${common_args[@]}" \
   -v /Users/mcieslak/projects/freesurfer-post/freesurfer_post:/opt/conda/envs/freesurfer-post/lib/python3.12/site-packages/freesurfer_post \
   pennlinc/freesurfer-post:unstable \
   "${fspost_args[@]}"

# Run the packaged version.
docker run --rm -ti "${common_args[@]}" \
   pennlinc/freesurfer-post:unstable \
   "${fspost_args[@]}"

# Drop into a shell in the container to poke around.
docker run --rm -ti --entrypoint /bin/bash "${common_args[@]}" \
   pennlinc/freesurfer-post:unstable
