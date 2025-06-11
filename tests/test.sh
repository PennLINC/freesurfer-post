docker run --rm -ti --entrypoint /bin/bash \
   --platform linux/amd64 \
   -v /Users/mcieslak/Desktop/fmriprep_anat:/data \
   -v /Users/mcieslak/Desktop/freesurfer_post:/output \
   -v /Users/mcieslak/Desktop/fspost_work:/work \
   --mount type=bind,source=/Users/mcieslak/Desktop/license.txt,target=/opt/freesurfer/license.txt \
   -v /Users/mcieslak/projects/freesurfer-post/freesurfer_post:/opt/conda/envs/freesurfer-post/lib/python3.12/site-packages/freesurfer_post \
   pennlinc/freesurfer-post:unstable \
       /data \
       /output \
       participant \
       --subjects-dir /data/sourcedata/freesurfer \
       --subject-id sub-colornest001

freesurfer-post \
       /data \
       /output \
       participant \
       --subjects-dir /data/sourcedata/freesurfer \
       --subject-id sub-colornest001 \
       -w /work
    
