import functools
import logging
import time


def log(func):
    logger = logging.getLogger(func.__module__)

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        try:
            func(*args, **kwargs)
        finally:
            duration = time.perf_counter() - start
            logger.debug(f'Executed {func.__qualname__} in {duration:.4f}s')

    return wrapper
