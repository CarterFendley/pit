import os
import subprocess
from typing import Callable, List, Dict, Set
from pathlib import Path
from dataclasses import dataclass

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

@dataclass
class GitData:
    spec: Dict[str, Set[str]]
    path: str
    ignore_path: str

@pytest.fixture
def with_git_repo(with_empty_dir) -> Callable[[], GitData]:
    def inner(
        spec: Dict[str, Set[str]] = None,
    ) -> GitData:
        if spec is None:
            spec = {}

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
        for _, files in spec.items():
            for file in files:
                parent = os.path.dirname(file)
                if parent != '':
                    os.makedirs(parent, exist_ok=True)

                # Create empty file
                with open(file, 'w') as f:
                    pass

        # Files which should be committed, commit
        # Note: `99` is not valid git status code, just making up one here for use with the fixture
        if '99' in spec:
            subprocess.run(
                ['git', 'add'] + list(spec['99']),
                check=True
            )
            subprocess.run(
                ['git', 'commit', '-m', 'Initial commit.'],
                check=True
            )

        # Files which should be staged, stage
        if 'A ' in spec:
            subprocess.run(
                ['git', 'add'] + list(spec['A ']),
                check=True
            )

        if '!!' in spec:
            with open('.gitignore', 'w') as f:
                for file in spec['!!']:
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
