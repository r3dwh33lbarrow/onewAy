import inspect
import logging
from logging import config

from uvicorn.config import LOGGING_CONFIG

_logging_configured = False


def get_logger() -> logging.Logger:
    global _logging_configured
    if not _logging_configured:
        logging.config.dictConfig(LOGGING_CONFIG)

        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)

        uvicorn_logger = logging.getLogger("uvicorn")
        if uvicorn_logger.handlers:
            root_logger.addHandler(uvicorn_logger.handlers[0])

        _logging_configured = True

    frame = inspect.currentframe().f_back
    name = frame.f_globals.get("__name__", "app")
    logger = logging.getLogger(name)

    logger.setLevel(logging.INFO)

    return logger
