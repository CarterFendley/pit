import os
import subprocess
from pathlib import Path

import pytest

@pytest.fixture
def with_empty_dir(tmp_path: Path):
    original_dir = os.curdir
    os.chdir(tmp_path)

    yield

    # Restore old directory path
    os.chdir(original_dir)

@pytest.fixture
def with_empy_git_repo(with_empty_dir):
    subprocess.run(
        ['git', 'init']
    )
