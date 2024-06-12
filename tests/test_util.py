from point_in_time.util import (
    git_is_command,
    git_is_inside_working_tree
)

def test_git_is_command_true():
    # Assumption: tests are run where git is command
    assert git_is_command() == True

def test_git_is_inside_repo_true(with_empy_git_repo):
    assert git_is_inside_working_tree() == True

def test_git_is_inside_repo_false(with_empty_dir):
    assert git_is_inside_working_tree() == False