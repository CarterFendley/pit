import os
import subprocess
from typing import Callable, Optional, List, Dict, Set
from pathlib import Path
from dataclasses import dataclass
from functools import reduce

import pytest

@pytest.fixture
def with_empty_dir(tmp_path_factory):
    # Note: Using tmp_path_factory over tmp_path to not collide with tmp_path if used by consuming tests / fixtures
    tmp_path: Path = tmp_path_factory.mktemp("git_dir")
    original_dir = os.curdir
    os.chdir(tmp_path)

    yield tmp_path

    # Restore old directory path
    os.chdir(original_dir)


GIT_CODE_COMMITTED = '99'
"""Non-standard status code to assure allow for associated fixtures to commit files."""
@dataclass
class GitSpec:
    """
    A dataclass accepted by associated fixtures which informs the fixtures how to initialize the git repo and contains helper properties for tests utilizing those fixtures.
    """

    spec_dict: Dict[str, Set[str]]
    """
    The spec which the fixture was invoked with.
    """

    @staticmethod
    def as_git_status_would(
        paths: Set[str]
    ) -> Set[str]:
        """
        **IMPORTANT NOTE:** This method is very much a *WIP*, only built atm to work with specs known to be defined by tests in this repo.

        Utility to take a set of file paths and return a set of paths as would be returned by `git status`. Specifically, return the top level file name (dir or file) where directories with multiple files are only shown by the directory name itself.

        Args:
            paths (Set[str]): The file paths to transform.
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

    def spec_fattened(
        self,
        exclude_codes: Optional[List[str]] = None,
        exclude_paths: Optional[List[str]] = None
    ) -> Set[str]:
        """
        A flattened list of files inside of the spec.

        **NOTE:** This will not always contain the paths returned by `git status` and associated commands. The `git status` command will often truncate the file paths to the top level directory or similar. Use `expected_initial_status` instead for that use case.

        Returns:
            Set[str]: The list of file paths in `self.spec`
        """
        if exclude_codes is None:
            exclude_codes = []
        if exclude_paths is None:
            exclude_paths = []

        spec = self.spec_dict.copy()

        for code in exclude_codes:
            del spec[code]

        flattened = reduce(
            lambda a, b: a.union(b),
            spec.values(),
            set()
        )

        flattened = filter(
            lambda p: p not in exclude_paths,
            flattened
        )

        return set(flattened)

    def expected_initial_status(
        self,
        include_ignores: bool = True
    ) -> Dict[str, Set[str]]:
        """
        The expected return of `git status --short` (as parsed by utilities).

        Args:
            include_ignores (bool, optional): If the ignored files should be included

        Returns:
            Dict[str, Set[str]]: The `spec` which should be expected at the start.
        """
        expected = self.spec_dict.copy()

        # Committed code is non-standard, will never show up in the status.
        del expected[GIT_CODE_COMMITTED]

        # If ignores excluded, exclude
        if not include_ignores:
            del expected['!!']

        # Transform all paths to be listed as returned by `git status`
        for code, files in expected.items():
            expected[code] = self.as_git_status_would(files)

        return expected

@dataclass
class GitData:
    """
    A dataclass returned by the `with_git_repo` fixture containing information about the associated git repository setup by that fixture.
    """
    spec: GitSpec
    path: str
    ignore_path: str

@pytest.fixture
def with_git_repo(with_empty_dir) -> Callable[[], GitData]:
    def inner(
        spec: GitSpec = None,
    ) -> GitData:
        if spec is None:
            spec = GitSpec({})

        subprocess.run(
            ['git', 'init'],
            check=True
        )

        # Configure user email / name for any commit actions
        subprocess.run(
            ['git', 'config', 'user.email', '"fixture@pytest.com"'],
            check=True
        )
        subprocess.run(
            ['git', 'config', 'user.name', '"Pytest Fixture"'],
            check=True
        )

        # Create all files specified
        for _, files in spec.spec_dict.items():
            for file in files:
                parent = os.path.dirname(file)
                if parent != '':
                    os.makedirs(parent, exist_ok=True)

                # Create empty file
                with open(file, 'w') as f:
                    pass

        # Files which should be committed, commit
        # Note: `99` is not valid git status code, just making up one here for use with the fixture
        if '99' in spec.spec_dict:
            subprocess.run(
                ['git', 'add'] + list(spec.spec_dict['99']),
                check=True
            )
            subprocess.run(
                ['git', 'commit', '-m', 'Initial commit.'],
                check=True
            )

        # Files which should be staged, stage
        if 'A ' in spec.spec_dict:
            subprocess.run(
                ['git', 'add'] + list(spec.spec_dict['A ']),
                check=True
            )

        if '!!' in spec.spec_dict:
            with open('.gitignore', 'w') as f:
                for file in spec.spec_dict['!!']:
                    f.write(f'{file}\n')

        return GitData(
            spec=spec,
            path=str(with_empty_dir),
            ignore_path=os.path.join(str(with_empty_dir), '.gitignore'),
        )

    return inner

@dataclass
class PitData:
    path: str
    git_data: GitData

@pytest.fixture
def with_pit_repo(with_git_repo) -> Callable[[], PitData]:
    def inner(
        no_ignore: bool = False,
        *args # Git args
    ) -> PitData:
        d = with_git_repo(*args)

        args = ['pit', 'init']
        if no_ignore:
            args.append('--no-ignore')
        subprocess.run(
            args,
            check=True
        )

        return PitData(
            path=d.path,
            git_data=d
        )

    return inner
