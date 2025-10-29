import logging, os
from logging.handlers import RotatingFileHandler
from .config import LOGS_DIR

def setup_logging(app_name: str = "FBHunter", level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(app_name)
    logger.setLevel(level)
    if logger.handlers:
        return logger
    os.makedirs(LOGS_DIR, exist_ok=True)
    fmt_console = logging.Formatter("[%(asctime)s][%(levelname)s] %(message)s", "%H:%M:%S")
    ch = logging.StreamHandler(); ch.setLevel(level); ch.setFormatter(fmt_console)
    fmt_file = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s", "%Y-%m-%d %H:%M:%S")
    fh = RotatingFileHandler(os.path.join(LOGS_DIR, "app.log"), maxBytes=2*1024*1024, backupCount=5, encoding="utf-8")
    fh.setLevel(level); fh.setFormatter(fmt_file)
    logger.addHandler(ch); logger.addHandler(fh)
    return logger
