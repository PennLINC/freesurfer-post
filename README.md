# FreeSurfer Post-processing Tools

A Python package for post-processing FreeSurfer outputs. 


## Combining FreeSurfer data with XCP-D results

To perform exciting cross-modality comparisons with BOLD and structural data,
you can combine tabular outputs from `freesurfer-post` and XCP-D.
Here we will combine ReHo estimates with the surface stats for the Schaefer 100 parcellation.

### Finding matching files

In XCP-D the Schaefer atlases are included in the [`4S` parcellations](https://github.com/pennlinc/atlaspack).
In `4S` parcellations, the Schaefer parcellations are combined with 56 subcortical regions.
Therefore to get the Schaefer 100 parcellation we need to look for the `seg-4S156Parcels` files from XCP-D.
In this example we'll use `sub-01_task-emotion_dir-LR_run-1_space-fsLR_seg-4S156Parcels_stat-reho_bold.tsv`.

In `freesurfer-post` the parcellations come directly from the FreeSurfer annot files in the CBIG repo.
Following those naming conventions, we want to use `atlas-Schaefer2018100Parcels7Networks`.
Here we'll use `sub-01_atlas-Schaefer2018100Parcels7Networks_surfacestats.tsv`.

### Python example

Here we combine the two tsvs using Python

```python
import pandas as pd

# Load the tsvs into dataframes.
fspost_data = pd.read_csv(
    'sub-01_atlas-Schaefer2018100Parcels7Networks_surfacestats.tsv',
    sep='\t',
)
xcpd_reho = pd.read_csv(
    'sub-01_task-emotion_dir-LR_run-1_space-fsLR_seg-4S156Parcels_stat-reho_bold.tsv',
    sep='\t',
)

# Convert xcpd_reho from wide to long format
xcpd_reho_long = pd.melt(
    xcpd_reho,
    var_name='StructName',
    value_name='reho',
)
# Prepend the string "7Networks_" to match the annot StructName
xcpd_reho_long['StructName'] = '7Networks_' + xcpd_reho_long['StructName']

# Merge fspost_data with xcpd_reho_long, keeping all rows from both datasets
merged_data = pd.merge(fspost_data, xcpd_reho_long, on='StructName')
```

### R Example

To do the same thing in R 

```r
library(tidyverse)

# Load the tsvs into dataframes.
fspost_data <- read.csv(
  "sub-01_atlas-Schaefer2018100Parcels7Networks_surfacestats.tsv", 
  sep = "\t"
)
xcpd_reho <- read.csv(
  "sub-01_task-emotion_dir-LR_run-1_space-fsLR_seg-4S156Parcels_stat-reho_bold.tsv",
  sep = "\t"
)

# Convert xcpd_reho from wide to long format
xcpd_reho_long <- xcpd_reho %>%
  pivot_longer(cols = everything(), 
               names_to = "StructName", 
               values_to = "reho") %>%
  mutate(StructName = paste0("7Networks_", StructName))

# Merge fspost_data with xcpd_reho_long, keeping all rows from both datasets
merged_data <- merge(fspost_data, xcpd_reho_long, by = "StructName")
```

### Summary

In both cases you will end up with a `merged_data` dataframe with 100 rows,
containing a `reho` column and all the surface properties.


## Using with BABS

Assuming you ran an fmriprep with `--anat-only` you can use just the
outputs as the inputs for `freesurfer-post`.

inputs/data//sourcedata/freesurfer

```yaml
input_datasets:
    fmriprep_anat:
        required_files:
            - "*fmriprep_anat*.zip"
        is_zipped: true
        origin_url: "ria+file:///path/to/fmriprep_anat/output_ria#~data"
        unzipped_path_containing_subject_dirs: "fmriprep_anat"
        path_in_babs: inputs/data/fmriprep_anat

# Arguments in `singularity run`:
bids_app_args:
    $SUBJECT_SELECTION_FLAG: "--subject-id"
    $SESSION_SELECTION_FLAG: "--session-id"
    $RUN_SELECTION_FLAG: "--run-id"
    -w: "$BABS_TMPDIR"
    --subjects-dir: "${PWD}/inputs/data/fmriprep_anat/fmriprep_anat/sourcedata/freesurfer"
    --fs-license-file: "/path/to/FreeSurfer/license.txt" # [FIX ME] path to 
```



## Installation

### From Source

```bash
git clone https://github.com/yourusername/freesurfer-post.git
cd freesurfer-post
pip install -e .
```

### Development Installation

```bash
git clone https://github.com/yourusername/freesurfer-post.git
cd freesurfer-post
pip install -e ".[dev]"
```

## Usage

### Command Line Interface

The package provides a command line interface through the `freesurfer-post` command:

```bash
# Show help
freesurfer-post --help

# Process FreeSurfer data
freesurfer-post /path/to/subjects_dir /path/to/output participant --subject-id sub-01

# Process a specific session
freesurfer-post /path/to/subjects_dir /path/to/output --subject-id sub-01 --session-id ses-01

# Process a specific run (or fall back to the session/subject directory)
freesurfer-post /path/to/subjects_dir /path/to/output --subject-id sub-01 --session-id ses-01 --run-id run-01 -w /path/to/work
```

`--working-dir` is required. The subject's FreeSurfer directory is copied there
before processing starts, because every FreeSurfer step in this pipeline writes
into `$SUBJECTS_DIR`: annots are added to `label/`, tables to `stats/`, and
qcache adds roughly 100 MB of `*.fsaverage.mgh` files to `surf/`. Working on a
copy keeps the input dataset unmodified, which matters when it is read-only or a
DataLad dataset under BABS. Budget an extra 1-2 GB of working-directory space
per subject for the copy.

### Directory resolution precedence

The FreeSurfer directory name is matched against the requested entities, most
specific first:

1. `sub-XX_ses-YY_run-ZZ`
2. `sub-XX_run-ZZ`
3. `sub-XX_ses-YY`
4. `sub-XX`

Candidates for entities you did not pass are skipped. If the most specific
directory does not exist, processing falls back to the next candidate that does
and emits a warning naming both.

### CIFTI outputs

The workflow runs FreeSurfer's qcache step and converts each paired hemispheric
vertex measure to an fsLR 164k CIFTI dense scalar. The files use BIDS entities
and are written with JSON sidecars in the subject's final output directory. For
example:

```text
sub-01/sub-01_ses-01_run-01_space-fsLR_den-164k_desc-fwhm10_thickness.dscalar.nii
sub-01/sub-01_ses-01_run-01_space-fsLR_den-164k_desc-fwhm10_thickness.json
```

Every measure in recon-all's qcache `measurelist` is converted, giving the
suffixes `area`, `areaPial`, `curv`, `jacobianWhite`, `sulc`, `thickness`,
`volume`, `wgPct`, `whiteH`, and `whiteK`. Each comes in an unsmoothed variant
plus the qcache smoothing levels (`desc-fwhm0`, `desc-fwhm5`, `desc-fwhm10`,
`desc-fwhm15`, `desc-fwhm20`, and `desc-fwhm25`), for 70 dense scalars in total.
`pial_lgi` is not included, because it requires `recon-all -localGI`, which
requires MATLAB.

Resampling uses neuromaps' area-adaptive barycentric interpolation. For `area`,
`areaPial`, and `volume` this means the fsLR values are interpolated rather than
conserved — they do not sum to the native-surface total — and the JSON sidecars
say so.


## License

This project is licensed under the BSD License - see the [LICENSE](LICENSE) file for details.
