import logging
from typing import List

FORMAT_STR_VERBOSE_INFO = '{ %(name)s:%(lineno)d @ %(asctime)s } -'

CLI_LOGGERS: List[logging.Logger] = []

def pit_get_logger(name: str, cli: bool = False) -> logging.Logger:
    """
    Returns a logger with some helpful presets.

    Args:
        name (str): The module name of course.

    Returns:
        logging.Logger: A python logger.
    """
    logger = logging.getLogger(name)

    handler = logging.StreamHandler()
    if cli:
        formatter = CLIFormatter()
    else:
        formatter = logging.Formatter(
            f'[pit] %(levelname)s - {FORMAT_STR_VERBOSE_INFO} %(message)s'
        )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    logger.propagate = True

    if cli:
        logger.setLevel(logging.INFO)
        CLI_LOGGERS.append(logger)

    return logger

def set_cli_level(level: int):
    """
    Set all CLI loggers to a specific logging level.

    Args:
        level (int): The logging level to set
    """
    for logger in CLI_LOGGERS:
        logger.setLevel(level)

class CLIFormatter(logging.Formatter):
    """
    Logging formatter to change format based on level
    """
    info_format = '[pit] %(message)s'
    default_format = '[pit] %(levelname)s - %(message)s'

    def __init__(self):
        super().__init__(self.default_format)

    def format(self, record: logging.LogRecord) -> str:
        if record.levelno == logging.INFO:
            self._style._fmt = self.info_format
        else:
            self._style._fmt = self.default_format

        return super().format(record)
