from typing import Callable, Dict

import pytest

from test_resources.fixtures import PitData
from test_resources.git_specs import (
    GIT_SPEC_ONE
)

STATUS_TEST_SPEC_ONE = {
    'git_spec': GIT_SPEC_ONE,
    'include_lines': [
        '*'
    ],
    'expected_status': [
        'Changes included in snapshots:',
    ] + [
        f'\tnew file: {file}'
        for file in GIT_SPEC_ONE.git_status_spec['A ']
    ] + [
        f'\tuntracked: {file}'
        for file in GIT_SPEC_ONE.git_status_spec['??']
    ] + ['']
}
STATUS_TEST_SPEC_TWO = {
    'git_spec': GIT_SPEC_ONE,
    'include_lines': [
        '*',
        '!file_untracked.txt'
    ],
    'expected_status': [
        'Changes included in snapshots:',
    ] + [
        f'\tnew file: {file}'
        for file in GIT_SPEC_ONE.git_status_spec['A ']
    ] + [
        f'\tuntracked: {file}'
        for file in GIT_SPEC_ONE.git_status_spec['??']
        if file != 'file_untracked.txt'
    ] + ['']
      + [
        'Changes not included in snapshots:',
        '\tuntracked: file_untracked.txt'
    ] + ['']
}

TEST_SPECS = [
    STATUS_TEST_SPEC_ONE,
    STATUS_TEST_SPEC_TWO
]

@pytest.mark.parametrize('test_spec', TEST_SPECS)
def test_repo_status(with_pit_repo: Callable[[], PitData], test_spec: Dict):
    d: PitData = with_pit_repo(
        git_spec=test_spec['git_spec'],
        include_lines=test_spec['include_lines']
    )

    assert test_spec['expected_status'] == d.pit_repo.get_snapshot_paths_status()