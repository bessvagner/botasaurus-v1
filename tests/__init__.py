import logging
from . import anti_detect_driver
from . import constants
from . import mockers

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    "%(levelname)s - function: (%(name)s at %(funcName)s "
    "line %(lineno)d): %(message)s"
)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

logging.getLogger('urllib3').setLevel(logging.ERROR)
logging.getLogger('selenium').setLevel(logging.WARNING)
logging.getLogger('asyncio').setLevel(logging.WARNING)
logging.getLogger('httpcore').setLevel(logging.WARNING)

__all__ = [
    'anti_detect_driver',
    'constants',
    'mockers',
]
