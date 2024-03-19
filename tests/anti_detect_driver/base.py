import unittest
from botasaurus import AntiDetectDriver
from botasaurus.decorators import browser

from tests import logger

@browser(output=None)
def driver_initializer(driver: AntiDetectDriver, data):
    return driver

class BaseTestAntiDetectDriver(unittest.TestCase):
    driver = None
    # setUp runs before each test case
    def setUp(self):
        self.driver = driver_initializer()
        logger.debug("Driver started!")

    def tearDown(self):
        self.driver.quit()
        logger.debug("Driver closed!")
