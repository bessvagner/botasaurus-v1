import time

import unittest
import threading
from unittest.mock import patch

from tests.mockers import MockWebdriver, MockWebDriverWait
from tests.anti_detect_driver.base import BaseTestAntiDetectDriver
from tests import logger

EXECUTE_SCRIPT = 'botasaurus.anti_detect_driver.Chrome.execute_script'
EXECUTE = 'botasaurus.anti_detect_driver.Chrome.execute'
WEBDRIVER_WAIT = 'botasaurus.anti_detect_driver.WebDriverWait.until'
GET = 'botasaurus.anti_detect_driver.Chrome.get'
CURRENT_URL = 'botasaurus.anti_detect_driver.Chrome.current_url'

class TestFindMethods(BaseTestAntiDetectDriver):
    
    mocker_driver = MockWebdriver()

    # @patch(EXECUTE_SCRIPT, new=mocker_driver.execute_script)
    # @patch(EXECUTE, new=mocker_driver.execute)
    # def test_get_by_current_page_referrer(self):
    #     timeout = 5
    #     url_1 = "https://example.com"
    #     url_2 = "https://different-url.com"
        
    #     self.driver.get(url_1)
        
    #     task = threading.Thread(
    #         target=self.driver.get_by_current_page_referrer,
    #         args=(url_2,)
    #     )
    #     task.start()
    #     task.join(timeout=timeout)
    #     if task.is_alive():
    #         self.fail("Method is stuck in an infinite loop")
    #     else:
    #         self.assertTrue(True, "Method completed execution")
        
    #     self.assertNotEqual(self.driver.current_url, url_1)

    # @patch(EXECUTE_SCRIPT, new=mocker_driver.execute_script)
    # @patch(EXECUTE, new=mocker_driver.execute)
    # def test_find_element(self):
    #     element = self.driver.find_element(by='id', value='id')
    #     self.assertEqual(element.by, 'css selector')
    #     self.assertEqual(element.value, '[id="id"]')

    # @patch(EXECUTE_SCRIPT, new=mocker_driver.execute_script)
    # @patch(EXECUTE, new=mocker_driver.execute)
    # def test_find_elements(self):
    #     element = self.driver.find_elements(by='class name', value='class')
    #     self.assertIsInstance(element, list)
    #     self.assertEqual(element[0].by, 'css selector')
    #     self.assertEqual(element[0].value, '.class')

    # @patch(EXECUTE_SCRIPT, new=mocker_driver.execute_script)
    # @patch(EXECUTE, new=mocker_driver.execute)
    # @patch(WEBDRIVER_WAIT, new=MockWebDriverWait(mocker_driver, 5).until)
    # def test_get_element_or_none(self):
    #     element = self.driver.get_element_or_none('//tag[@attr="value"]', wait=5)
    #     self.assertEqual(element.by, 'xpath')
    #     self.assertEqual(element.value, '//tag[@attr="value"]')

    # @patch(EXECUTE_SCRIPT, new=mocker_driver.execute_script)
    # @patch(EXECUTE, new=mocker_driver.execute)
    # @patch(WEBDRIVER_WAIT, new=MockWebDriverWait(mocker_driver, 5).until)
    # def test_get_element_or_none_by_selector(self):
    #     element = self.driver.get_element_or_none_by_selector('class', wait=5)
    #     logger.debug(element)
    #     self.assertEqual(element.by, 'css selector')
    #     self.assertEqual(element.value, 'class')

    # @patch(EXECUTE_SCRIPT, new=mocker_driver.execute_script)
    # @patch(EXECUTE, new=mocker_driver.execute)
    # @patch(WEBDRIVER_WAIT, new=MockWebDriverWait(mocker_driver, 5).until)
    # def test_get_element_by_id(self):
    #     element = self.driver.get_element_by_id('id', wait=5)
    #     self.assertEqual(element.by, 'css selector')
    #     self.assertEqual(element.value, '[id="id"]')

    # @patch(EXECUTE_SCRIPT, new=mocker_driver.execute_script)
    # @patch(EXECUTE, new=mocker_driver.execute)
    # @patch(WEBDRIVER_WAIT, new=MockWebDriverWait(mocker_driver, 5).until)
    # def test_get_element_or_none_by_text_contains(self):
    #     text = 'mock_text'
    #     element = self.driver.get_element_or_none_by_text_contains(text, wait=5)
    #     self.assertEqual(element.by, 'xpath')
    #     self.assertEqual(element.value, f'//*[contains(text(), "{text}")]')

    # @patch(EXECUTE_SCRIPT, new=mocker_driver.execute_script)
    # @patch(EXECUTE, new=mocker_driver.execute)
    # @patch(WEBDRIVER_WAIT, new=MockWebDriverWait(mocker_driver, 5).until)
    # def test_get_element_or_none_by_text(self):
    #     text = 'mock_text'
    #     element = self.driver.get_element_or_none_by_text(text, wait=5)
    #     self.assertEqual(element.by, 'xpath')
    #     self.assertEqual(element.value, f'//*[text()="{text}"]')

    # @patch(EXECUTE_SCRIPT, new=mocker_driver.execute_script)
    # @patch(EXECUTE, new=mocker_driver.execute)
    # @patch(WEBDRIVER_WAIT, new=MockWebDriverWait(mocker_driver, 5).until)
    # def test_find(self):
    #     element = self.driver.find('id')
    #     self.assertEqual(element.by, 'id')
    #     self.assertEqual(element.value, 'id')

    # @patch(EXECUTE_SCRIPT, new=mocker_driver.execute_script)
    # @patch(EXECUTE, new=mocker_driver.execute)
    # @patch(WEBDRIVER_WAIT, new=MockWebDriverWait(mocker_driver, 5).until)
    # def test_find_all(self):
    #     elements = self.driver.find_all('class', by='class name')
    #     self.assertIsInstance(elements, list)
    #     self.assertEqual(elements[0].by, 'class name')
    #     self.assertEqual(elements[0].value, 'class')

    # @patch(EXECUTE_SCRIPT, new=mocker_driver.execute_script)
    # @patch(EXECUTE, new=mocker_driver.execute)
    # @patch(WEBDRIVER_WAIT, new=MockWebDriverWait(mocker_driver, 5).until)
    # def test_find_raises_type_error(self):
    #     with self.assertRaises(TypeError):
    #         self.driver.find('class', 'class')  # ''by' is obligatory keyword

    @patch(EXECUTE_SCRIPT, new=mocker_driver.execute_script)
    @patch(EXECUTE, new=mocker_driver.execute)
    @patch(WEBDRIVER_WAIT, new=MockWebDriverWait(mocker_driver, 5).until)
    def test_send_to(self,):
        element = self.driver.find('id')
        response = self.driver.send_to(
            element,
            'key',
            expected_condition=lambda driver: lambda driver: element
        )
        self.assertEqual(response.by, 'id')
        self.assertEqual(response.value, 'id')


if __name__ == '__main__':
    unittest.main()
