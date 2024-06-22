class PITBaseException(Exception):
    def __init__(self, msg: str):
        super().__init__(msg)
        self.msg = msg

class PITInternalError(PITBaseException):
    """Internal error wrapper"""
    pass

class PITRepoExistsError(PITBaseException):
    """When preforming pit initialization but repo already exists for git repo."""
    def __init__(self):
        super().__init__("Pit does not currently support reinitialization: Path already contains a '.pit' directory")

class PITRepoLoadError(PITBaseException):
    """Base class for repo load errors"""
    pass

class PITLogLoadError(PITRepoLoadError):
    """When loading log file fails"""
    pass

class PITIncludeLoadError(PITBaseException):
    """When loading include file fails"""
    pass