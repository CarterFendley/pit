import subprocess
from pathlib import Path
from dataclasses import dataclass

import pytest

from point_in_time.utils.main import status_filter_pathspec

FIXTURE_FILES = {
    'file_untracked.txt',
    'file_staged.txt',
    'file_committed.txt',
    'file_ignored.txt',
    'dir/file_one.txt',
    'dir/file_two.txt',
    'ignored_dir/file_one.txt',
    'ignored_dir/file_two.txt',
    # Add name edge cases
    'white   space.txt',
    '"quotes.txt"',
    '\\\\"backslash_quotes.txt\\\\"',
    # This is added automatically when adding the `ignore` option but listing here for use in tests
    '.gitignore'
}
FIXTURE_COMMITTED = {
    'file_committed.txt',
}
FIXTURE_STAGED = {
    'file_staged.txt',
}
FIXTURE_IGNORES = {
    'file_ignored.txt',
    'ignored_dir/',
}

# TODO: Better way that manually maintaining?
FIXTURE_IGNORED_FILES = { 
    'file_ignored.txt',
    'ignored_dir/file_one.txt',
    'ignored_dir/file_two.txt',
}
FIXTURE_FILES_FOR_ITERATION = FIXTURE_FILES - (
    FIXTURE_IGNORED_FILES # Only shown when '--force'
    .union(FIXTURE_COMMITTED) # Only shown when modified
    .union({'.gitignore'}) # Delete / move operations wil return unexpected results if they modify .gitignore
)
EXPECT_CHANGED_UNTRACKED = {
    'file_untracked.txt',
    'file_staged.txt',
    'dir/',
    # Add name edge cases
    'white   space.txt',
    '"quotes.txt"',
    '\\\\"backslash_quotes.txt\\\\"',
    # This is added automatically when adding the `ignore` option but listing here for use in tests
    '.gitignore'
}



@pytest.fixture
def pathspec_fixture(with_git_repo, tmp_path) -> Path:
    def inner():
        pathspec_file = tmp_path / 'pathspec.txt'

        with_git_repo(
            files=FIXTURE_FILES,
            ignore=FIXTURE_IGNORES
        )

        # Commit files specified
        subprocess.run(
            ['git', 'add'] + list(FIXTURE_COMMITTED),
            check=True
        )
        subprocess.run(
            ['git', 'commit', '-m', 'Initial commit.'],
            check=True
        )

        # Stage files specifeid
        subprocess.run(
            ['git', 'add'] + list(FIXTURE_STAGED),
            check=True
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
    assert sorted(files) == sorted(EXPECT_CHANGED_UNTRACKED)

@pytest.mark.xfail
def test_pattern_dot(pathspec_fixture):
    pathspec_file = pathspec_fixture()
    with open(pathspec_file, 'w') as f:
        f.write('.')

    files = status_filter_pathspec(pathspec_file)
    assert files == FIXTURE_FILES - FIXTURE_IGNORED_FILES

@pytest.mark.xfail
def test_pattern_exclude(pathspec_fixture):
    pathspec_file = pathspec_fixture()
    with open(pathspec_file, 'w') as f:
        f.write(':(exclude)dir/file_one.txt')

    files = status_filter_pathspec(pathspec_file)
    assert sorted(files) == sorted(
        FIXTURE_FILES
        - (
            FIXTURE_IGNORED_FILES
            .union(FIXTURE_COMMITTED)
            .union({'dir/file_one.txt'})
        )
    )

def test_pattern_dir(pathspec_fixture):
    pathspec_file = pathspec_fixture()
    with open(pathspec_file, 'w') as f:
        f.write('dir/')

    files = status_filter_pathspec(pathspec_file)
    assert sorted(files) == ['dir/']

def test_pattern_ignored(pathspec_fixture):
    pathspec_file = pathspec_fixture()
    with open(pathspec_file, 'w') as f:
        for file in FIXTURE_IGNORES:
            f.write(file + '\n')

    files = status_filter_pathspec(pathspec_file, force=False)
    assert files == []

    files = status_filter_pathspec(pathspec_file, force=True)
    assert sorted(files) == sorted(FIXTURE_IGNORES)

def test_with_comments(pathspec_fixture):
    pathspec_file = pathspec_fixture()
    with open(pathspec_file, 'w') as f:
        f.write('# My comment\n')
        f.write('*\n')
        f.write('# Another comment')

    files = status_filter_pathspec(pathspec_file)
    assert sorted(files) == sorted(EXPECT_CHANGED_UNTRACKED)

@pytest.mark.xfail
@pytest.mark.parametrize("file", ['   leading.txt', 'trailing.txt   '])
def test_whitespace_failures(pathspec_fixture_all_committed, file: str):
    pathspec_file = pathspec_fixture_all_committed()

    with open(file, 'w'):
        pass
    with open(pathspec_file, 'w') as f:
        f.write(file)

    files = status_filter_pathspec(pathspec_file)
    assert files == [file]


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
    assert sorted(files) == sorted([
        file,
        f'{file}_new'
    ])