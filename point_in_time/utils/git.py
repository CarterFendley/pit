import os
import subprocess
from typing import List

from .os import ChDir

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

def git_parse_pathspec_from_file(path: str, force: bool = False) -> List[str]:
    """
    Utility for parsing a git [pathspec](https://git-scm.com/docs/gitglossary#Documentation/gitglossary.txt-aiddefpathspecapathspec) file into the list of matched paths. This is used primarily to use the list of matched paths to confirm with users before continuing.

    This utility is implemented through the use of `git add --dry-run` to delegate interpreting of pathspec files to git itself.

    Args:
        path (str): The path the file containing the pathspec.
        force (bool, optional): Allows addition of `--force` if that is needed. Defaults to False.

    Returns:
        List[str]: The parsed list of paths which match the pathspec.
    """
    with ChDir(git_show_toplevel()):
        assert os.path.isfile(path), "Path provided does not point to a file"

        args = [
            'git', 'add',
            '--dry-run',
            '--ignore-missing', # In case paths don't exist
            f'--pathspec-from-file={path}'
        ]
        if force:
            args.append('--force')

        result = subprocess.run(
            args,
            # Check is intentionally false
            # When ignored files are added without --force, return will be 1
            check=False,
            capture_output=True
        )

        # Little hacky at the moment, want to capture staged files too, so need to do it with `--renormalize` but renormalize will cause issues with repos without commits in them.
        args.append('--renormalize')
        result.stdout += subprocess.run(
            args,
            # Check is intentionally false
            # When ignored files are added without --force, return will be 1
            check=False,
            capture_output=True
        ).stdout

        paths = set()
        stdout_lines = result.stdout.decode().split('\n')
        for line in stdout_lines:
            if line == '':
                continue
            assert line.startswith("add '"), "Found unexpected prefix when reading output from 'git add'"
            assert line.endswith("'"), "Found unexpected suffix when reading output from 'git add'"

            line = line[5:-1]
            paths.add(line)

        return paths