import os
from point_in_time.utils.git import (
    git_is_command,
    git_is_inside_working_tree,
    git_show_toplevel,
    git_check_ignore,
    git_parse_pathspec_from_file
)

def test_is_command_true():
    # Assumption: tests are run where git is command
    assert git_is_command() == True

def test_is_inside_repo_true(with_git_repo):
    with_git_repo()

    assert git_is_inside_working_tree() == True

def test_is_inside_repo_false(with_empty_dir):
    assert git_is_inside_working_tree() == False

def test_show_toplevel(with_git_repo):
    d = with_git_repo()

    assert git_show_toplevel() == d.path

def test_ignore_false(with_git_repo):
    with_git_repo()

    assert git_check_ignore('my_file') == False

def test_ignore_true(with_git_repo):
    with_git_repo(
        ignore=['my_file']
    )

    assert git_check_ignore('my_file') == True

def test_parse_pathspec(with_git_repo, tmp_path):
    d = with_git_repo(
        files=[
            'file.txt',
            'dir/file_one.txt',
            'dir/file_two.txt',
            'ignored_dir/file_one.txt',
            'ignored_dir/file_two.txt',
            'ignored_file',
            # This is added automatically when adding the `ignore` option but listing here to prevent confusion.
            '.gitignore'
        ],
        ignore=[
            'ignored_dir',
            'ignored_file'
        ]
    )

    # Test . file
    pathspec_file = tmp_path / 'pathspec.txt'
    with open(pathspec_file, 'w') as f:
        f.write('.')
    files = git_parse_pathspec_from_file(pathspec_file.absolute())
    assert sorted(files) == sorted([
        'file.txt',
        'dir/file_one.txt',
        'dir/file_two.txt',
        '.gitignore'
    ])

    # Test exclude pattern
    with open(pathspec_file, 'w') as f:
        f.write(':(exclude)dir/file_one.txt')
    files = git_parse_pathspec_from_file(pathspec_file.absolute())
    assert sorted(files) == sorted([
        'file.txt',
        'dir/file_two.txt',
        '.gitignore'
    ])

    # Test with dir targeting
    with open(pathspec_file, 'w') as f:
        f.write('dir/')
    files = git_parse_pathspec_from_file(pathspec_file.absolute())
    assert sorted(files) == sorted([
        'dir/file_one.txt',
        'dir/file_two.txt',
    ])

    # Test no failures: file does not exist
    with open(pathspec_file, 'w') as f:
        f.write('my_non_existing_file')
    files = git_parse_pathspec_from_file(pathspec_file.absolute())
    assert files == []

    # Test no failures: Ignored file
    with open(pathspec_file, 'w') as f:
        f.write('ignored_file')
    files = git_parse_pathspec_from_file(pathspec_file.absolute())
    assert files == []

    # Test no failures: Comments
    with open(pathspec_file, 'w') as f:
        f.write('# Comment in path spec')
    files = git_parse_pathspec_from_file(pathspec_file.absolute())
    assert files == []

    # Test with force
    with open(pathspec_file, 'w') as f:
        f.write('ignored_file')
    files = git_parse_pathspec_from_file(pathspec_file.absolute(), force=True)
    assert files == ['ignored_file']