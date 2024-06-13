import os

class ChDir:
    """A context manager for changing directories"""
    def __init__(self, path: str):
        self.path = path
        self._original_path = None

    def __enter__(self):
        assert self._original_path is None, "ChDir contexts should not be nested, create a new ChDir object if needed."
        self._original_path = os.curdir

        os.chdir(self.path)

    def __exit__(self, exc_type, exc_value, traceback):
        os.chdir(self._original_path)
        self._original_path = None