from __future__ import annotations
import os
import json
from json import JSONDecodeError
from datetime import datetime
from typing import List

from pydantic import BaseModel, TypeAdapter
from pydantic_core import ValidationError

from point_in_time.constants.main import (
    PIT_LOG_NAME
)
from point_in_time.errors import (
    PITInternalError,
    PITRepoExistsError,
    PITLogLoadError
)

__all__ = ['PITRepo']

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

        log_data = []
        log_path = os.path.join(
            path,
            PIT_LOG_NAME
        )
        with open(log_path, 'w') as f:
            json.dump(log_data, f)

        return cls(path)

    def __init__(self, path: str):
        self._path = path
        self._log_path = os.path.join(
            self._path,
            PIT_LOG_NAME
        )

        self._load_log()

    def _load_log(self):
        if not os.path.isfile(self._log_path):
            raise PITLogLoadError("Malformed pit directory: Log file does not exist")

        try:
            with open(self._log_path, 'r') as f:
                log_data = json.load(f)
        except JSONDecodeError as err:
            raise PITLogLoadError("Malformed pit log: %s" % err.msg)

        try:
            ta = TypeAdapter(List[PITLogEntry])
            self.log = ta.validate_python(log_data)
        except ValidationError as err:
            raise PITLogLoadError("Malformed pit log: %s" % str(err))



class PITLogEntry(BaseModel):
    name: str
    git_hash: str
    created_at: datetime