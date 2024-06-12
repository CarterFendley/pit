import subprocess

def git_is_command() -> bool:
    """
    Utility for assuring that `git` is a valid command.

    Returns:
        bool: Boolean indicating if git is resolved via `which`
    """
    result = subprocess.run(
        ['git']
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
        capture_output=True
    )

    return result.stdout.decode() == 'true\n'