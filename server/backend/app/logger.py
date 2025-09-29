import logging

from app.settings import settings


def get_logger() -> logging.Logger:
    logging.getLogger("uvicorn.debug").setLevel(
        logging.DEBUG if settings.app.debug else logging.INFO
    )
    return logging.getLogger("uvicorn.debug")
