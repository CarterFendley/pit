from point_in_time.utils.git import (
    git_is_command,
    git_is_inside_working_tree,
    git_show_toplevel,
    git_check_ignore,
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
        spec={'!!': {'my_file'}}
    )

    assert git_check_ignore('my_file') == True