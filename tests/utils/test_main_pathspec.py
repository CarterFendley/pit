import os
import subprocess
from typing import Set
from pathlib import Path
from functools import reduce

import pytest

from point_in_time.utils.main import status_filter_pathspec

from test_resources.fixtures import GitSpec, GIT_CODE_COMMITTED
from test_resources.git_specs import GIT_SPEC_ONE

FIXTURE_FILES_FOR_ITERATION = GIT_SPEC_ONE.spec_fattened(
    exclude_codes=['!!', GIT_CODE_COMMITTED],
    exclude_paths=['.gitignore'] # Delete / move operations wil return unexpected results if they modify .gitignore
)

@pytest.fixture
def pathspec_fixture(with_git_repo, tmp_path) -> Path:
    def inner():
        with_git_repo(
            git_spec=GIT_SPEC_ONE
        )
    return inner

@pytest.fixture
def pathspec_fixture_all_committed(pathspec_fixture) -> Path:
    def inner():
        pathspec_fixture() 
        subprocess.run(
            ['git', 'add', '-A'],
            check=True
        )
        subprocess.run(
            ['git', 'commit', '-m', '"Second commit"'],
            check=True
        )

    return inner

def test_pattern_star(pathspec_fixture):
    pathspec_fixture()

    files = status_filter_pathspec(['*'])
    assert files == GIT_SPEC_ONE.expected_initial_status()

@pytest.mark.xfail
def test_pattern_dot(pathspec_fixture):
    pathspec_fixture()

    files = status_filter_pathspec(['.'])
    assert files == GIT_SPEC_ONE.expected_initial_status()

@pytest.mark.xfail
def test_pattern_exclude(pathspec_fixture):
    pathspec_fixture()

    files = status_filter_pathspec([':(exclude)dir/file_one.txt'])

    expected = GIT_SPEC_ONE.expected_initial_status().copy()
    expected['??'] -= {'dir/file_one.txt'}
    assert files == expected

def test_pattern_dir(pathspec_fixture):
    pathspec_fixture()

    files = status_filter_pathspec(['dir'])
    assert files == {
        '??': ['dir/']
    }

def test_with_comments(pathspec_fixture):
    pathspec_fixture()

    files = status_filter_pathspec([
        '# My comment',
        '*',
        '# Another comment'
    ])
    assert files == GIT_SPEC_ONE.expected_initial_status()

@pytest.mark.xfail
@pytest.mark.parametrize("file", ['   leading.txt', 'trailing.txt   '])
def test_whitespace_failures(pathspec_fixture_all_committed, file: str):
    pathspec_fixture_all_committed()

    with open(file, 'w'):
        pass

    files = status_filter_pathspec([file])
    assert files == {
        '??': {file}
    }


@pytest.mark.parametrize('file', FIXTURE_FILES_FOR_ITERATION)
def test_with_move(pathspec_fixture_all_committed, file: str):
    pathspec_fixture_all_committed()

    # Move a file
    # NOTE: Using `git mv` to assure git picks it up.
    subprocess.run(
        ['git', 'mv', file, f'{file}_new'],
        check=True
    )

    files = status_filter_pathspec(['*'])
    # NOTE: Expect based from ignore b/c ignores will not be committed
    expect = {
        '!!': GIT_SPEC_ONE.git_status_spec['!!'],
        'R ': [
            (file, f'{file}_new')
        ]
    }
    assert files == expect

@pytest.mark.parametrize('file', FIXTURE_FILES_FOR_ITERATION)
def test_with_rm(pathspec_fixture_all_committed, file: str):
    pathspec_fixture_all_committed()

    # Move a file
    # NOTE: Using `git mv` to assure git picks it up.
    subprocess.run(
        ['git', 'rm', file],
        check=True
    )

    files = status_filter_pathspec(['*'])
    # NOTE: Expect based from ignore b/c ignores will not be committed
    expect = {
        '!!': GIT_SPEC_ONE.git_status_spec['!!'],
        'D ': [file]
    }
    assert files == expect