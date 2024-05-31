import logging

from .decorators import RetryException,browser, request, AsyncQueueResult, AsyncResult
from .anti_detect_driver import AntiDetectDriver
from .anti_detect_driver import AntiDetectDriverRemote
from .anti_detect_requests import AntiDetectRequests
import botasaurus.bt as bt

formatter = logging.Formatter(
    "%(levelname)s - function: (%(name)s at %(funcName)s "
    "line %(lineno)d): %(message)s"
)

logger = logging.getLogger("botasaurus")
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)

logger.setLevel(logging.DEBUG)
logger.addHandler(console_handler)
