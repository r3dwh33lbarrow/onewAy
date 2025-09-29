import logging

from uvicorn.logging import DefaultFormatter

from app.settings import settings


def get_logger() -> logging.Logger:
    log = logging.getLogger("onewAy")
    level = logging.DEBUG if settings.app.debug else logging.INFO
    log.setLevel(level)

    if not log.hasHandlers():
        handler = logging.StreamHandler()
        handler.setLevel(level)
        handler.setFormatter(DefaultFormatter(fmt="%(levelprefix)s %(message)s"))
        log.addHandler(handler)

    return log
