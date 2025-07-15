from . import setup
from .config import QkJson
from .data import Positions, Date

__version__ = '0.0.1'


from loguru import logger
from pathlib import Path

APP_DIR = Path(__file__).parent
DATA_DIR = APP_DIR / "data"
LOG_FILE = DATA_DIR / f"{Date}.log"
logger.add(
    LOG_FILE,
    rotation="1 MB",
    retention="10 days",
    encoding="utf-8",
    backtrace=True,
    diagnose=True,
    enqueue=True,
    catch=True)
logger.info("ReasonData loaded.")

__all__ = ['config', 'Positions', 'setup']
