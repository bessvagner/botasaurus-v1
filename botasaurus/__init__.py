import logging

from .decorators import RetryException,browser, request, AsyncQueueResult, AsyncResult
from .anti_detect_driver import AntiDetectDriver
from .anti_detect_requests import AntiDetectRequests
import botasaurus.bt as bt

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')  # noqa E501
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

logging.getLogger('urllib3').setLevel(logging.ERROR)
logging.getLogger('selenium').setLevel(logging.WARNING)
logging.getLogger('asyncio').setLevel(logging.WARNING)
logging.getLogger('httpcore').setLevel(logging.WARNING)
