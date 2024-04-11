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


class BaseTestAntiDetectDriverWithCapabilities(BaseTestAntiDetectDriver):

    def setUp(self):

        capabilities = {'thisCapability': 'cap'}

        @browser(output=None, capabilities=capabilities)
        def driver_initializer_with_capabilities(driver: AntiDetectDriver, data):
            return driver
        self.driver = driver_initializer_with_capabilities()
        logger.debug("Driver started!")
