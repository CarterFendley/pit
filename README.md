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

**NOTE:** You can view the html coverage report by opening `<path-to-repo>/htmlcov/index.html` in the browser.

```bash
python -m pytest
```

### Releasing

Update the version in `pyproject.toml`
```
version='X.Y.Z'
```

Create a git tag and push
```
git tag vX.Y.Z
git push --tags
```

Then create a release via github.

#### If you mess up and need to edit things

Remove old tag and re-tag
```
git tag -d vX.Y.Z
git tag vX.Y.Z

git push -f --tags
```

Delete previous github release and re-create.