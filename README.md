# Point In Time (pit)

Lightweight tooling for tracking experiment state in git based repositories.

### Install for development

Clone this repository

```bash
git clone https://github.com/CarterFendley/pit.git
```

**(Optional)** Create a virtual environment for testing
```bash
# Via conda (but use whatever you like)
conda create --name pit python
conda activate pit
```

Install in editable mode with development dependencies.
```bash
python -m pip install '.[dev]'
```

Verify correct install by running tests.
```bash
python -m pytest tests
```