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
        pathspec_file = tmp_path / 'pathspec.txt'

        with_git_repo(
            spec=GIT_SPEC_ONE
        )

        return pathspec_file
    return inner

@pytest.fixture
def pathspec_fixture_all_committed(pathspec_fixture) -> Path:
    def inner():
        pathspec_file = pathspec_fixture()
        subprocess.run(
            ['git', 'add', '-A'],
            check=True
        )
        subprocess.run(
            ['git', 'commit', '-m', '"Second commit"'],
            check=True
        )

        return pathspec_file
    return inner

def test_pattern_star(pathspec_fixture):
    pathspec_file = pathspec_fixture()
    with open(pathspec_file, 'w') as f:
        f.write('*')

    files = status_filter_pathspec(pathspec_file)
    assert files == GIT_SPEC_ONE.expected_initial_status()

@pytest.mark.xfail
def test_pattern_dot(pathspec_fixture):
    pathspec_file = pathspec_fixture()
    with open(pathspec_file, 'w') as f:
        f.write('.')

    files = status_filter_pathspec(pathspec_file)
    assert files == GIT_SPEC_ONE.expected_initial_status()

@pytest.mark.xfail
def test_pattern_exclude(pathspec_fixture):
    pathspec_file = pathspec_fixture()
    with open(pathspec_file, 'w') as f:
        f.write(':(exclude)dir/file_one.txt')

    files = status_filter_pathspec(pathspec_file)

    expected = EXPECT_CHANGED_UNTRACKED.copy()
    expected['??'] -= {'dir/file_one.txt'}
    assert files == expected

def test_pattern_dir(pathspec_fixture):
    pathspec_file = pathspec_fixture()
    with open(pathspec_file, 'w') as f:
        f.write('dir/')

    files = status_filter_pathspec(pathspec_file)
    assert files == {
        '??': {'dir/'}
    }

def test_with_comments(pathspec_fixture):
    pathspec_file = pathspec_fixture()
    with open(pathspec_file, 'w') as f:
        f.write('# My comment\n')
        f.write('*\n')
        f.write('# Another comment')

    files = status_filter_pathspec(pathspec_file)
    assert files == GIT_SPEC_ONE.expected_initial_status()

@pytest.mark.xfail
@pytest.mark.parametrize("file", ['   leading.txt', 'trailing.txt   '])
def test_whitespace_failures(pathspec_fixture_all_committed, file: str):
    pathspec_file = pathspec_fixture_all_committed()

    with open(file, 'w'):
        pass
    with open(pathspec_file, 'w') as f:
        f.write(file)

    files = status_filter_pathspec(pathspec_file)
    assert files == {
        '??': {file}
    }


@pytest.mark.parametrize('file', FIXTURE_FILES_FOR_ITERATION)
def test_with_move(pathspec_fixture_all_committed, file: str):
    pathspec_file = pathspec_fixture_all_committed()

    # Move a file
    # NOTE: Using `git mv` to assure git picks it up.
    subprocess.run(
        ['git', 'mv', file, f'{file}_new'],
        check=True
    )

    with open(pathspec_file, 'w') as f:
        f.write('*')
    files = status_filter_pathspec(pathspec_file)

    # NOTE: Expect based from ignore b/c ignores will not be committed
    expect = {
        '!!': GitSpec.as_git_status_would(GIT_SPEC_ONE.spec_dict['!!']),
        'R ': {
            (file, f'{file}_new')
        }
    }
    assert files == expect

@pytest.mark.parametrize('file', FIXTURE_FILES_FOR_ITERATION)
def test_with_rm(pathspec_fixture_all_committed, file: str):
    pathspec_file = pathspec_fixture_all_committed()

    # Move a file
    # NOTE: Using `git mv` to assure git picks it up.
    subprocess.run(
        ['git', 'rm', file],
        check=True
    )

    with open(pathspec_file, 'w') as f:
        f.write('*')
    files = status_filter_pathspec(pathspec_file)

    # NOTE: Expect based from ignore b/c ignores will not be committed
    expect = {
        '!!': GitSpec.as_git_status_would(GIT_SPEC_ONE.spec_dict['!!']),
        'D ': {file}
    }
    assert files == expect