import pytest
from typing import Callable
import subprocess

from test_resources.fixtures import GitData

@pytest.mark.parametrize('verbose_flag', ['-v', '--verbose'])
def test_verbose(
    with_git_repo: Callable[[], GitData],
    verbose_flag: str
):
    """
    Dummy test to make sure some known debug statements show up when verbose is on.

    # Note: caplog does not work with subshells, more info here: https://github.com/pytest-dev/pytest/issues/3037
    """
    d = with_git_repo()

    result = subprocess.run(
        ['pit', verbose_flag, 'init'],
        capture_output=True
    )

    assert f"Adding .pit to {d.ignore_path}" in result.stderr.decode()