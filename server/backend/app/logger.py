import logging


def get_logger() -> logging.Logger:
    logging.getLogger("uvicorn.error").setLevel(logging.DEBUG)
    return logging.getLogger("uvicorn.error")
