import os
import subprocess
from typing import Optional, List
from contextlib import ExitStack

from pathspec import PathSpec
from pathspec.patterns import GitWildMatchPattern

from point_in_time.constants.main import PIT_DIR_NAME

from .os import ChDir
from .git import git_show_toplevel, git_check_ignore

def get_pit_path(git_path: Optional[str] = None) -> str:
    """
    General purpose util for locating the `.pit` directory (which is in the toplevel git folder)

    **NOTE:** This utility does not preform validation on the Pit repo, just points to where the path ~should~ exist.

    Args:
        git_path (Optional[str], optional): Optional path to a git repository, if not provided, the current working directory will be assumed.

    Returns:
        str: The path where the pit directory should ~exist~
    """
    with ExitStack() as e: # For optional ChDir manager
        if git_path is not None:
            e.enter_context(ChDir(git_path))

        git_toplevel = git_show_toplevel()

        return os.path.join(
            git_toplevel,
            PIT_DIR_NAME
        )

def is_pit_path_ignored() -> bool:
    """
    General purpose utility for checking if the pit directory is ignored by git.

    Returns:
        bool: Boolean indicating if the pit dir is ignored by git
    """
    pit_path = get_pit_path()
    return git_check_ignore(pit_path)

def find_unescaped_qoute(string: str, start: int) -> int:
    escaped = False
    for i in range(start, len(string)):
        if escaped:
            escaped = False
            continue # Ignore anything escaped
        else:
            if string[i] == '\\': # Evals to a string slash
                escaped = True
            if string[i] == '"':
                return i
    return -1

def status_filter_pathspec(path: str, force: bool = False) -> List[str]:
    status = subprocess.run(
        args=['git', 'status', '--short', '--ignored'],
        check=True,
        capture_output=True,
    )
    status = status.stdout.decode().split('\n')

    # Parse status into two lists
    changed = []
    ignored = []
    for line in status:
        if line == '':
            continue
        code, rest = line[:2], line[3:]

        if rest.startswith('"'):
            pos = find_unescaped_qoute(rest, 1)
            assert pos != -1, "Found unclosed quote in line: %s" % line
            path_one, rest = rest[1:pos], rest[pos+2:]

            # Process any escape sequences in the quoted string
            path_one = bytes(path_one, 'utf-8').decode('unicode_escape')
        else:
            pos = rest.find(' ')
            if pos == -1:
                pos = len(rest)
            path_one, rest = rest[0:pos], rest[pos+1:]

        if not rest.startswith('->'):
            path_two = None
        else:
            if rest[3] == '"':
                assert rest.endswith('"'), "Found unclosed quote on line: %s" % line
                path_two = rest[4:-1]

                # Process any escape sequences in the quoted string
                path_two = bytes(path_two, 'utf-8').decode('unicode_escape')
            else:
                path_two = rest[3:]

        if code == '!!':
            l = ignored
        else:
            l = changed

        l.append(path_one)
        if path_two is not None:
            l.append(path_two)

    if force:
        files = changed + ignored
    else:
        files = changed

    # Filter based on specified pathspec
    with open(path, 'r') as f:
        spec = PathSpec.from_lines(GitWildMatchPattern, f)
    return list(spec.match_files(files))