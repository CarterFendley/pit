import os
import subprocess
from typing import Callable

import pytest

from point_in_time.constants.main import (
    PIT_DIR_NAME,
    PIT_LOG_NAME
)
from point_in_time.constants.return_codes import *

from test_resources.fixtures import GitData, PitData

def test_no_git_repo(with_empty_dir):
    result = subprocess.run(
        ['pit', 'init'],
    )

    assert result.returncode == PIT_CODE_GIT_NO_REPO

@pytest.mark.parametrize('no_ignore', [True, False])
def test_valid_init(
    with_git_repo: Callable[[], GitData],
    no_ignore: bool
):
    d = with_git_repo()

    args = ['pit', 'init']
    if no_ignore:
        args.append('--no-ignore')
    result = subprocess.run(
        args,
        check=True
    )

    pit_path = os.path.join(d.path, PIT_DIR_NAME)
    pit_log = os.path.join(pit_path, PIT_LOG_NAME)

    assert os.path.isdir(pit_path)
    assert os.path.isfile(pit_log)

    if not no_ignore:
        assert os.path.isfile(d.ignore_path)
        with open(d.ignore_path, 'r') as f:
            assert f.read() == "\n# Pit repo directory\n.pit/"
    else:
        assert not os.path.isfile(d.ignore_path)

def test_existing_pit_repo(
    with_pit_repo: Callable[[], PitData]
):
    with_pit_repo()

    result = subprocess.run(
        ['pit', 'init']
    )

    assert result.returncode == PIT_CODE_REPO_EXISTS

def test_non_directory():
    result = subprocess.run(
        ['pit', 'init', '/dev/null']
    )

    assert result.returncode == PIT_CODE_INIT_FAILED