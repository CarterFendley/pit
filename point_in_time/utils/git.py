import subprocess

def git_is_command() -> bool:
    """
    Utility for assuring that `git` is a valid command.

    Returns:
        bool: Boolean indicating if git is resolved via `which`
    """
    result = subprocess.run(
        ['git'],
        stderr=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL
    )

    return result.returncode != 127 # Command not found


def git_is_inside_working_tree() -> bool:
    """
    Utility for determining if current working directory is a git repository.

    Returns:
        bool: Boolean indicating if the current working directory is a repository.
    """
    result = subprocess.run(
        ['git', 'rev-parse', '--is-inside-work-tree'],
        capture_output=True,
    )

    return result.stdout.decode() == 'true\n'

def git_show_toplevel() -> str:
    """
    Utility for getting the toplevel directory of the current git repository.

    Returns:
        str: The absolute path of the top level directory
    """
    assert git_is_inside_working_tree(), "Not inside working directory"

    result = subprocess.run(
        ['git', 'rev-parse', '--show-toplevel'],
        check=True,
        capture_output=True
    )

    return result.stdout.decode().replace('\n', '')

def git_check_ignore(path: str) -> bool:
    """
    Utility for determining if specified path is ignored by git.

    Returns:
        bool: Boolean indicating if the specific path is ignored by git.
    """
    result = subprocess.run(
        ['git', 'check-ignore', path, '-q'],
        stderr=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL
    )

    assert result.returncode != 128, "Specified path is outside of git repository"

    return result.returncode == 0