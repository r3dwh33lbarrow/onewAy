import inspect
import logging
from logging import config

from uvicorn.config import LOGGING_CONFIG

_logging_configured = False


def get_logger() -> (logging.Logger, logging.Formatter):
    """
    Retrieves a logger instance and its associated formatter.

    This function ensures that logging is configured only once globally.
    It sets up the root logger with the `uvicorn` logger's handler and formatter,
    and configures the logger for the calling module.

    Returns:
        tuple: A tuple containing:
            - logging.Logger: The logger instance for the calling module.
            - logging.Formatter: The formatter used by the logger.
    """
    global _logging_configured
    formatter = logging.Formatter()
    if not _logging_configured:
        logging.config.dictConfig(LOGGING_CONFIG)

        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)

        uvicorn_logger = logging.getLogger("uvicorn")
        if uvicorn_logger.handlers:
            root_logger.addHandler(uvicorn_logger.handlers[0])
            formatter = uvicorn_logger.handlers[0].formatter

        _logging_configured = True

    frame = inspect.currentframe().f_back
    name = frame.f_globals.get("__name__", "app")
    logger = logging.getLogger(name)

    logger.setLevel(logging.DEBUG)

    return logger, formatter


def logger_fix(log: logging.Logger, formatter: logging.Formatter) -> None:
    """
    Retrieves a logger instance and its associated formatter.

    This function ensures that logging is configured only once globally.
    It sets up the root logger with the `uvicorn` logger's handler and formatter,
    and configures the logger for the calling module.

    Returns:
        tuple: A tuple containing:
            - logging.Logger: The logger instance for the calling module.
            - logging.Formatter: The formatter used by the logger.
    """
    log.disabled = False
    frame = inspect.currentframe().f_back
    name = frame.f_globals.get("__name__", "app")
    log = logging.getLogger(name)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)
    log.addHandler(console_handler)
    log.propagate = False
    log.disabled = False
