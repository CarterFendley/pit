import os
import subprocess
from typing import Set
from pathlib import Path
from functools import reduce

import pytest

from point_in_time.utils.main import status_filter_pathspec

# Only top level directories will show
def as_git_status_would(paths: Set[str]) -> Set[str]:
    """
    Utility to take a set of file paths and return a set of paths as would be returned by `git status`. Specifically, return the top level file name (dir or file) where directories with multiple files are only shown by the directory name itself.

    Args:
        paths (Set[str]): _description_
    Returns:
        Set[str]: The paths that `git status` would return given input files.
    """
    def top_level_only(path):
        s = os.path.split(path)
        if s[0] != '':
            return s[0] + '/'
        return s[1]
    return set(map(
        top_level_only,
        paths
    ))

FIXTURE_FILES = {
    # Committed files
    # Note: `99` is not valid git status code, just making up one here for use with the fixture
    '99': {
        'file_committed.txt',
    },
    # Untracked files
    '??': {
        'file_untracked.txt',
        'dir/file_one.txt',
        'dir/file_two.txt',
        # Add name edge cases
        'white   space.txt',
        '"quotes.txt"',
        '\\\\"backslash_quotes.txt\\\\"',
        # This is added automatically when adding the `ignore` option but listing here for use in tests
        '.gitignore'
    },
    # Newly added files
    'A ': {
        'file_staged.txt',
    },
    # Ignored files
    '!!': {
        'file_ignored.txt',
        'ignored_dir/file_one.txt',
        'ignored_dir/file_two.txt',
    }
}
FIXTURE_FILES_FLAT = reduce(
    lambda a, b: a.union(b),
    FIXTURE_FILES.values(),
    set()
)

# A set of files for parameterized tests
FIXTURE_FILES_FOR_ITERATION = FIXTURE_FILES_FLAT - (
    FIXTURE_FILES['!!'] # Ignored
    .union(FIXTURE_FILES['99']) # Committed
    .union({'.gitignore'}) # Delete / move operations wil return unexpected results if they modify .gitignore
)

# Anything that will show up by default in git status
EXPECT_CHANGED_UNTRACKED = FIXTURE_FILES.copy()
del EXPECT_CHANGED_UNTRACKED['99']
for code, files in EXPECT_CHANGED_UNTRACKED.items():
    EXPECT_CHANGED_UNTRACKED[code] = as_git_status_would(
        EXPECT_CHANGED_UNTRACKED[code]
    )



@pytest.fixture
def pathspec_fixture(with_git_repo, tmp_path) -> Path:
    def inner():
        pathspec_file = tmp_path / 'pathspec.txt'

        with_git_repo(
            spec=FIXTURE_FILES
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
    assert files == EXPECT_CHANGED_UNTRACKED

@pytest.mark.xfail
def test_pattern_dot(pathspec_fixture):
    pathspec_file = pathspec_fixture()
    with open(pathspec_file, 'w') as f:
        f.write('.')

    files = status_filter_pathspec(pathspec_file)
    assert files == EXPECT_CHANGED_UNTRACKED

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
    assert files == EXPECT_CHANGED_UNTRACKED

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
        '!!': as_git_status_would(FIXTURE_FILES['!!']),
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
        '!!': as_git_status_would(FIXTURE_FILES['!!']),
        'D ': {file}
    }
    assert files == expect