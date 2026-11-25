# este file es para manejar los print cuando se pasa por terminal el modo quiet, verboso o normal


import logging


def setup_logger(verbose, quiet):
    if quiet:
        level = logging.ERROR
    elif verbose:
        level = logging.DEBUG
    else:  # modo normal
        level = logging.INFO

    log_format = "%(asctime)s [%(levelname)s] [%(threadName)s] %(message)s"
    logging.basicConfig(level=level, format=log_format)
