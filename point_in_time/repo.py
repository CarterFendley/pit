from __future__ import annotations
import os
import re
import json
import subprocess
from datetime import datetime
from dataclasses import dataclass
from json import JSONDecodeError
from tempfile import NamedTemporaryFile
from typing import Dict, List, Set, Tuple, Union, Optional, Any

from pydantic import BaseModel, TypeAdapter
from pydantic_core import ValidationError
from colorama import (
    just_fix_windows_console,
    Fore
)
from unique_names_generator import get_random_name

from point_in_time.constants.main import (
    PIT_LOG_NAME,
    PIT_INCLUDE_NAME
)
from point_in_time.errors import (
    PITInternalError,
    PITRepoExistsError,
    PITLogLoadError,
    PITIncludeLoadError,
    PITStashFailedError,
    PITStashPopFailedError,
    PITCommitParseFailed,
    PITLogCollision
)
from point_in_time.utils.main import (
    status_filter_pathspec,
    code_to_status_string
)
from point_in_time.utils.fs import WithBackUp
from point_in_time.utils.git import (
    GitCommitDetails,
    git_commit_details
)

__all__ = ['PITRepo']
just_fix_windows_console()

RE_STASH_POP_COMMIT_HASH = r"\([0-9a-z]+\)$"

class PITRepo:
    @classmethod
    def create_repo(cls, path: str) -> PITRepo:
        """
        Given a directory, this function will initialize a empty repo and return the path to the `.pit/` directory.

        Args:
            path (str): The directory to initialize as an empty Pit repository.

        Raises:
            PITInternalError: If the specified path does not exist or `.pit/` already exists under the path.

        Returns:
            PITRepo: The initialized PITRepo.
        """
        parent_dir = os.path.dirname(path)
        if not os.path.isdir(parent_dir):
            raise PITInternalError("Path specified is not a directory: %s" % parent_dir)

        if os.path.exists(path):
            raise PITRepoExistsError()
        os.mkdir(path)

        # Initialize files
        log_data = {}
        log_path = os.path.join(
            path,
            PIT_LOG_NAME
        )
        with open(log_path, 'w') as f:
            json.dump(log_data, f)

        include_path = os.path.join(
            path,
            PIT_INCLUDE_NAME
        )
        with open(include_path, 'w') as f:
            f.write('# Pit include files are treated written in the git pathspec syntax\n')
            f.write('# See more here: https://git-scm.com/docs/gitglossary#Documentation/gitglossary.txt-aiddefpathspecapathspec\n')
            f.write('*\n')

        return cls(path)

    def __init__(self, path: str):
        self._path = path
        self._log_path = os.path.join(
            self._path,
            PIT_LOG_NAME
        )
        self._include_path = os.path.join(
            self._path,
            PIT_INCLUDE_NAME
        )

    def _load_log(self) -> Dict[str, PITLogEntry]:
        if not os.path.isfile(self._log_path):
            raise PITLogLoadError("Malformed pit directory: Log file does not exist")

        try:
            with open(self._log_path, 'r') as f:
                log_data = json.load(f)
        except JSONDecodeError as err:
            raise PITLogLoadError("Malformed pit log: %s" % err.msg)

        try:
            return log_file.validate_python(log_data)
        except ValidationError as err:
            raise PITLogLoadError("Malformed pit log: %s" % str(err))

    def append_log(self, e: PITLogEntry):
        log = self._load_log()

        if e.pit_id in log:
            raise PITLogCollision("Pit name collision during log append.")

        log[e.pit_id] = e

        with WithBackUp(self._log_path):
            with open(self._log_path, 'wb') as f:
                f.write(log_file.dump_json(
                    log,
                    indent=2
                ))

    def get_details(self, e: PITLogEntry) -> SnapshotDetails:
        git_details = git_commit_details(e.git_hash)

        return SnapshotDetails(
            _log_entry=e,
            _git_details=git_details
        )

    def get_snapshot_paths(self) -> Dict[str, Set[Union[str, Tuple[str]]]]:
        with open(self._include_path, 'r') as f:
            lines = f.read()

        force_comments = list(re.finditer(r"^#\s*[fF]orce\s*$", lines))
        if len(force_comments) > 1:
            raise PITIncludeLoadError("Found multiple 'force' comments in include file. Only one 'force' section can be included.")
        elif len(force_comments) == 0:
            included = status_filter_pathspec(lines.split('\n'))

            # No force block so remove those paths
            del included['!!']
        else:
            include_lines = lines[:force_comments[0].span[0]]
            force_lines = lines[-force_comments[0].span[1]:]

            included = status_filter_pathspec(include_lines.split('\n'))

            # Replace ignored files with those matched by the force block
            del included['!!']
            included['!!'] = status_filter_pathspec(force_lines.split('\n'))['!!']

        return included

    def get_snapshot_paths_status(
        self,
        snapshot_paths: Optional[Dict[str, Set[Union[str, Tuple[str]]]]] = None,
        cli: bool = False,
    ) -> List[str]:
        if snapshot_paths is None:
            included = self.get_snapshot_paths()
        else:
            included = snapshot_paths

        # Match all paths to get a diff of paths not included
        all_paths = status_filter_pathspec(['*'])
        not_included = {}
        for code, paths in all_paths.items():
            not_included[code] = set(all_paths[code]) - set(included.get(code, []))

            if len(not_included[code]) == 0:
                del not_included[code]
        # Don't display ignored files
        if '!!' in not_included:
            del not_included['!!']

        status: List[str] = []
        if len(included) != 0:
            if cli:
                c = Fore.GREEN
            else:
                c = ''

            status.append(f'Changes included in snapshots:{c}')
            for code, paths in included.items():
                status_string = code_to_status_string(code)
                for path in sorted(paths):
                    status.append(f"\t{status_string} {path}")

            if cli:
                c = Fore.RESET
            status.append(c)
        if len(not_included) != 0:
            if cli:
                c = Fore.RED
            else:
                c = ''

            status.append(f'Changes not included in snapshots:{c}')
            for code, paths in not_included.items():
                for path in sorted(paths):
                    status.append(f"\t{status_string} {path}")

            if cli:
                c = Fore.RESET
            status.append(c)

        return status

    def snapshot(
        self,
        paths: List[str],
        metadata: Optional[dict] = None
    ):
        if metadata is None:
            metadata = {}
        with NamedTemporaryFile() as f:
            f.write('\n'.join(paths).encode())
            f.seek(0)

            result = subprocess.run(
                [
                    'git',
                    'stash',
                    'push',
                    '--include-untracked',
                    f'--pathspec-from-file={f.name}'
                ],
                capture_output=True
            )
            if result.returncode != 0:
                raise PITStashFailedError(result.stderr.decode())

            result = subprocess.run(
                ['git', 'stash', 'pop'],
                capture_output=True
            )
            if result.returncode != 0:
                raise PITStashPopFailedError(result.stderr.decode())

            commit = re.findall(RE_STASH_POP_COMMIT_HASH, result.stdout.decode())
            if len(commit) == 0:
                raise PITCommitParseFailed("No commit hash found during 'git stash drop'")
            elif len(commit) > 1:
                raise PITCommitParseFailed("Multiple matches found for commit during 'git stash drop'")

            # Note: [1:-1] removes the leading / trailing '(' and ')' to leave just the hash
            commit = commit[0][1:-1]


            s = PITLogEntry(
                pit_id=get_random_name(separator='-', style='lowercase')+f'-{commit[:7]}',
                git_hash=commit,
                metadata=metadata
            )

            self.append_log(s)

            return s

@dataclass
class SnapshotDetails:
    _log_entry: PITLogEntry
    _git_details: GitCommitDetails

    @property
    def pit_id(self) -> str:
        return self._log_entry.pit_id

    @property
    def git_hash(self) -> str:
        return self._log_entry.git_hash

    @property
    def metadata(self) -> Dict[str, Any]:
        return self._log_entry.metadata

    @property
    def date(self) -> datetime:
        return self._git_details.date

    @property
    def files_changed(self) -> List[str]:
        return self._git_details.files_changed

    def format(self, cli=False, verbose=True) -> str:
        details = []

        if cli:
            c = Fore.YELLOW
        else:
            c = ''
        details.append(f'{c}snapshot {self.pit_id}{Fore.RESET}')

        if 'username' in self.metadata and 'hostname' in self.metadata:
            details.append(f'Origin: {self.metadata["username"]}@{self.metadata["hostname"]}')

        details.append(f'Commit: {self.git_hash}')
        details.append(f'Date: {self.date.strftime('%d/%m/%Y, %H:%M:%S')}')

        if verbose:
            details.append('')

            details.append('Files changes:')
            for file in self.files_changed:
                details.append(f'\t{file}')

        return '\n'.join(details)

class PITLogEntry(BaseModel):
    pit_id: str
    git_hash: str
    metadata: Dict[str, Any]

log_file = TypeAdapter(Dict[str, PITLogEntry])
