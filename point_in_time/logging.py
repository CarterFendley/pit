import logging

FORMAT_STR_VERBOSE_INFO = '{ %(name)s:%(lineno)d @ %(asctime)s } -'

def pit_get_logger(name: str) -> logging.Logger:
    """
    Returns a logger with some helpful presets.

    Args:
        name (str): The module name of course.

    Returns:
        logging.Logger: A python logger.
    """
    logger = logging.getLogger(name)

    handler = logging.StreamHandler()
    formatter = logging.Formatter(f'[pit] {FORMAT_STR_VERBOSE_INFO} %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger