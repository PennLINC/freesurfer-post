# FreeSurfer Post-processing Tools

A Python package for post-processing FreeSurfer outputs with modern neuroimaging analysis capabilities, including integration with fMRIPrep and neuromaps.

## Features

- **Command Line Interface**: Easy-to-use CLI for common FreeSurfer post-processing tasks
- **fMRIPrep Integration**: Seamless integration with fMRIPrep outputs
- **Neuromaps Support**: Surface-to-surface transformations using the neuromaps package
- **Modern Python Packaging**: Built with modern Python packaging standards using pyproject.toml
- **Extensible Architecture**: Modular design for easy extension and customization

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

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes and ensure they pass linting and tests
4. Commit your changes (`git commit -m 'Add some amazing feature'`)
5. Push to the branch (`git push origin feature/amazing-feature`)
6. Open a Pull Request

All pull requests are automatically tested with GitHub Actions, including:
- Code linting with Ruff
- Type checking with MyPy
- Code formatting checks

## License

This project is licensed under the BSD License - see the [LICENSE](LICENSE) file for details.