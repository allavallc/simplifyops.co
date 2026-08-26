"""Repo-local logging for the gateway.

Replaces the former host-global `/home/pi/pi_logging.py` import so the repo is
self-contained (checkout/CI can import the gateway without host state).

Behavior is unchanged from the old host module: a rotating file handler
(`{LOG_DIR}/{name}.log`, 5 MB x 3 backups, DEBUG) plus an INFO stderr handler,
format "%(asctime)s %(name)s %(levelname)s %(message)s". The log directory
defaults to the historical `/home/pi/logs` and can be overridden with the
`SIMPLIFYOPS_LOG_DIR` env var.
"""

import logging
import logging.handlers
import os

LOG_DIR = os.environ.get("SIMPLIFYOPS_LOG_DIR", "/home/pi/logs")


def get_logger(name, stderr=True):
    os.makedirs(LOG_DIR, exist_ok=True)
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s")

    fh = logging.handlers.RotatingFileHandler(
        os.path.join(LOG_DIR, f"{name}.log"),
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    if stderr:
        sh = logging.StreamHandler()
        sh.setLevel(logging.INFO)
        sh.setFormatter(fmt)
        logger.addHandler(sh)

    return logger
