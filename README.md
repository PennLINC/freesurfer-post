# FreeSurfer Post-processing Tools

A Python package for post-processing FreeSurfer outputs. 


## Using with BABS

Assuming you ran an fmriprep with `--anat-only` you can use just the
outputs as the inputs for `freesurfer-post`.

inputs/data//sourcedata/freesurfer

```yaml
input_datasets:
    FreeSurfer:
        required_files:
            - "*freesuefer*.zip"
        is_zipped: true
        origin_url: "/path/to/FreeSurfer"
        unzipped_path_containing_subject_dirs: "fmriprep_anat"
        path_in_babs: inputs/data/freesurfer

# Arguments in `singularity run`:
bids_app_args:
    $SUBJECT_SELECTION_FLAG: "--subject-id"
    -w: "$BABS_TMPDIR"
    --stop-on-first-crash: ""
    --subjects-dir: "inputs/data/fmriprep_anat/fmriprep_anat/sourcedata/freesurfer"
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
```


## Development

### Setup Development Environment

```bash
# Clone repository
git clone https://github.com/yourusername/freesurfer-post.git
cd freesurfer-post

# Install in development mode with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Code formatting and linting
ruff check .                 # Lint code
ruff check . --fix          # Lint and auto-fix issues
ruff format .               # Format code

# Type checking
mypy freesurfer_post/
```

### Code Quality

This project uses several tools to maintain code quality:

- **Ruff**: Fast linting and formatting (replaces flake8, isort, and more)
- **Black**: Code formatting (as backup/alternative to ruff format)
- **MyPy**: Static type checking
- **Pytest**: Testing framework

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=freesurfer_post

# Run specific test file
pytest tests/test_core.py
```

### Pre-commit Hooks (Optional)

You can set up pre-commit hooks to automatically run linting before commits:

```bash
pip install pre-commit
# Create .pre-commit-config.yaml (see example below)
pre-commit install
```

Example `.pre-commit-config.yaml`:
```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.6
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
  - repo: https://github.com/psf/black
    rev: 23.11.0
    hooks:
      - id: black
```

## License

This project is licensed under the BSD License - see the [LICENSE](LICENSE) file for details.