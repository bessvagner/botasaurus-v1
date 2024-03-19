import re
import logging
import uuid
from dataclasses import dataclass, field
from typing import Union, List, Dict, Callable, Any

from .constants import (
    LOGOUT_OUTPUT,
    TEST_URL,
    EXECUTABLE_PATH,
    PORT,
    RETURN_EXECUTE_SCRIPT,
    MOCK_ID,
    MOCK_TAG_NAME,
    MOCK_TEXT,
    MOCK_IS_DISPLAYED,
    MOCK_IS_ENABLED,
    MOCK_IS_SELECTED,
)

logger = logging.getLogger()


@dataclass
class DesiredCapabilities:
    
    CHROME = {"browserName": "chrome"}


@dataclass
class MockService:

    path: str = EXECUTABLE_PATH
    port: int = PORT
    service_args: List[str] = field(default_factory=list)
    log_output: str = LOGOUT_OUTPUT
    service_url: str = "http://127.0.0.1:8000"

    def start(self,):
        self.service_url = f"http://127.0.0.1:{self.port}"
        return "Service started!"

    def stop(Self,):
        return "Service stoped!"

@dataclass
class MockOptions:

    default_capabilities: dict = field(
        default_factory=lambda: DesiredCapabilities().CHROME
    )
    capabilities: dict = default_capabilities
    _ignore_local_proxy: str = ""

    def set_capability(self, name, value) -> None:
        self.capabilities[name] = value

    def to_capabilities(self,) -> None:
        return self.capabilities


@dataclass
class MockWebElement:
    by: str
    value: str
    id: str = MOCK_ID
    tag_name: str = MOCK_TAG_NAME
    text: str = MOCK_TEXT
    __is_displayed: bool = MOCK_IS_DISPLAYED
    __is_enabled: bool = MOCK_IS_ENABLED
    __is_selected: bool = MOCK_IS_SELECTED

    def click(self):
        return True

    def submit(self):
        return True

    def clear(self):
        return True

    def send_keys(self, *value):
        return True

    def get_attribute(self, name):
        return True

    def is_displayed(self,):
        return self.__is_displayed

    def is_enabled(self,):
        return self.__is_enabled

    def is_selected(self,):
        return self.__is_selected


@dataclass
class MockWebdriver:
    
    options: MockOptions = MockOptions()
    service: MockService = MockService()
    keep_alive: bool = True
    sessionId: str = str(uuid.uuid4()).replace('-', '')
    
    current_url: str = TEST_URL

    def get(self, url):
        self.current_url = url
        return url

    def execute(self, script, *args):
        args = list(args)
        value = None
        if 'window.location.href = ' in script:
            match = re.findall(r'"(.*?)"', script)
            if match:
                value = self.get(match[0])
        elif script == "getCurrentUrl":
            value = self.current_url
        elif 'findElement' in script:
            if args and isinstance(args[0], dict):
                value = args[0]
                if set(('using', 'value')).issubset(args[0]):
                    element = MockWebElement(
                        by=args[0]['using'], value=args[0]['value']
                    )
                    value = element
                    if 'findElements' in script:
                        value = [element]
        return {"script": script, "args": args, "value": value}

    def execute_script(self, script, *args):
        return self.execute(script, *args)

    def find_element(self, by, value) -> MockWebElement:
        return MockWebElement(by=by, value=value)

    def find_elements(self, by, value) -> List[MockWebElement]:
        return [MockWebElement(by=by, value=value)]


@dataclass
class MockWebDriverWait:
    _driver: MockWebdriver
    timeout: float
    poll_frequency: float = 0.5
    ignored_exceptions: tuple = ()

    def until(self, method: Callable, message: str = "") -> Any:
        """Mock of the until method.
        
        This method simulates waiting until a condition is met.
        In this mock, it simply calls the provided method and returns its result.
        """
        try:
            return method(self._driver)
        except Exception as e:
            if not isinstance(e, self.ignored_exceptions):
                raise
            return None

    def until_not(self, method: Callable, message: str = "") -> Any:
        """Mock of the until_not method.
        
        This method simulates waiting until a condition is not met.
        In this mock, it simply calls the provided method and returns its result.
        """
        try:
            return not method(self._driver)
        except Exception as e:
            if not isinstance(e, self.ignored_exceptions):
                raise
            return None
