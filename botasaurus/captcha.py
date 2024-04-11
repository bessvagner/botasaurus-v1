import re
import logging
import json
import random
import asyncio
from io import BytesIO
from typing import Union, Tuple, List

import requests

from PIL import Image
from bs4 import BeautifulSoup
from selenium.common.exceptions import ElementClickInterceptedException

from aigents.core import AsyncGoogleVision

from .anti_detect_driver import AntiDetectDriver

from .constants import RANDOM_SLEEP_INTERVAL
from .constants import JSON_MARKDOWN_PATTERN
from .constants import PROMPT_GUESS_IMAGE

Number = Union[int, float]
logger = logging.getLogger()


def split_image(img: Image, x, y):
    """
    Splits an image into a grid of tiles.

    Parameters
    ----------
    img : Image
        The image to be split.
    x : int
        The number of columns in the grid.
    y : int
        The number of rows in the grid.

    Returns
    -------
    List[List[Image]]
        A list of lists containing the tiles of the image.
    """
    # Open the image
    width, height = img.size

    # Calculate the size of each tile
    tile_width = width // x
    tile_height = height // y

    # Initialize an empty matrix to hold the tiles
    tiles_matrix = []

    for i in range(y):
        row = []
        for j in range(x):
            # Calculate the position of the tile
            left = j * tile_width
            top = i * tile_height
            right = left + tile_width
            bottom = top + tile_height

            # Extract the tile
            tile = img.crop((left, top, right, bottom))
            row.append(tile)
        tiles_matrix.append(row)

    return tiles_matrix

def random_sleep_interval(minimum: Number, maximum: Number) -> float:
    """
    Generates a random sleep interval between the specified minimum and
    maximum values.

    Parameters
    ----------
    minimum : Number
        The minimum value for the sleep interval.
    maximum : Number
        The maximum value for the sleep interval.

    Returns
    -------
    float
        A random float between the minimum and maximum values.
    """
    return (maximum - minimum)*random.random() + minimum

def sleep(driver: AntiDetectDriver,
          minimum: Number = RANDOM_SLEEP_INTERVAL[0],
          maximum: Number = RANDOM_SLEEP_INTERVAL[1]) -> None:
    driver.sleep(random_sleep_interval(minimum, maximum))

def flip_coin():
    return random.choice((False, True))

def go_to_challenge_frame(driver: AntiDetectDriver):
    """
    Switches the driver's focus to the challenge frame within a web page.

    This function first switches the driver's focus to the default content of
    the page, then finds all iframe elements on the page, and finally switches
    the driver's focus to the third iframe found. This is typically used in web
    scraping or automation tasks where the challenge frame is the target for
    interaction.

    Parameters
    ----------
    driver : AntiDetectDriver
        The driver instance to use for switching focus.

    Returns
    -------
    None
        This function does not return any value.

    Notes
    -----
    This function assumes that the third iframe on the page is the challenge
    frame. If the structure of the web page changes, this function may need to
    be updated.
    """
    driver.switch_to.default_content()
    frames = driver.find_all('iframe', by='tag name')
    driver.switch_to.frame(frames[2])

def reload_challenge(driver: AntiDetectDriver):
    """
    Reloads the captcha challenge by clicking the reload button.

    This function navigates to the challenge frame, attempts to click the
    reload button, and then navigates back to the challenge frame. It is useful
    for refreshing the captcha challenge in case the initial challenge was
    not solvable or to attempt a new challenge.

    Parameters
    ----------
    driver : AntiDetectDriver
        The driver instance to use for interacting with the captcha.

    Returns
    -------
    None

    Notes
    -----
    This function assumes that the reload button can be found by the selector
    'recaptcha-reload-button'. If the structure of the web page changes,
    this function may need to be updated.

    Exceptions
    ----------
    ElementClickInterceptedException
        If the reload button cannot be clicked due to another element
        overlaying it.
    """
    go_to_challenge_frame(driver)
    try:
        driver.find('recaptcha-reload-button').click()
    except ElementClickInterceptedException:
        pass
    go_to_challenge_frame(driver)

def get_image(url):
    """
    Downloads an image from a given URL and returns it as a PIL Image object.

    Parameters
    ----------
    url : str
        The URL of the image to download.

    Returns
    -------
    PIL.Image.Image or None
        The downloaded image as a PIL Image object, or None if the download
        fails.

    Notes
    -----
    This function logs the start of the download and the success of the
    download.
    """
    logger.info("Downloading captcha image: %s", url)
    response = requests.get(url, timeout=20)
    img = None
    if response.ok and response.content:
        img = Image.open(BytesIO(response.content))
        logger.info("\t|_ Download sucsess!")
    return img

def get_tiles_data(driver: AntiDetectDriver) -> Tuple[List[BeautifulSoup], int, int, float]:  # noqa E501
    """
    Extracts data from the captcha tiles on a webpage.

    This function navigates to the challenge frame of a webpage, locates the
    captcha tiles, and extracts relevant data such as the rows of tiles, the
    number of rows and columns, and the URL of the image used in the captcha.

    Parameters
    ----------
    driver : AntiDetectDriver
        The driver instance to use for interacting with the webpage.

    Returns
    -------
    tuple
        A tuple containing:
        - A list of BeautifulSoup objects representing the rows of tiles.
        - The number of rows in the captcha grid.
        - The number of columns in the captcha grid.
        - The URL of the image used in the captcha.

    Raises
    ------
    RuntimeError
        If the image grid cannot be selected.

    Notes
    -----
    This function assumes that the captcha tiles are located within a table
    element with a class containing "rc-imageselect-table". If the structure
    of the webpage changes, this function may need to be updated.
    """
    go_to_challenge_frame(driver)
    xpath = '//table[contains(@class, "rc-imageselect-table")]'
    table = driver.xpath(xpath)
    if not table:
        logger.debug("Selecting by xpath '%s' failed!", xpath)
        raise RuntimeError("Image grid couldn't be selected")
    table = table[0]
    table_soup = driver.soup_of(table)

    rows = table_soup.tbody.find_all('tr')
    cols = rows[0].find_all('td')
    image_url = cols[0].find('img').attrs['src']
    n_rows = len(rows)
    n_cols = len(cols)
    return rows, n_rows, n_cols, image_url


async def ask(idx, image, prompt):
    """
    Asynchronously asks a model to guess a tile based on an image and a prompt.

    Parameters
    ----------
    idx : int
        The index of the tile to be guessed.
    image : Union[str, Path, Image.Image]
        The image to analyze. Can be a file path as a string, a Path object, or
        an Image.Image object.
    prompt : str
        An optional prompt to guide the response.

    Returns
    -------
    str
        The generated response content based on the image and prompt.

    Notes
    -----
    This function uses the AsyncGoogleVision class to generate a response.
    It logs the attempt to guess the tile and the model's response.
    TODO: Allow the use of other models (APIs).
    """
    logger.info("Trying to guess tile %s", idx)
    # TODO: allow the use of other models (APIs)
    response = await AsyncGoogleVision().answer(image, prompt)
    logger.info("Model guessed tile %s: %s", idx, response)
    return response

async def get_guess_mask(target: str,
                         tiles_images: List[Image.Image]) -> List[bool]:
    """
    Asynchronously generates a mask indicating which tiles are guessed to be
    correct based on the target and images.

    This function iterates over each tile image, asks a model to guess if the
    tile is correct based on the target and the image, and appends the result
    to a mask.

    Parameters
    ----------
    target : str
        The target string to be used in the prompt for guessing the tiles.
    tiles_images : List[Image.Image]
        A list of PIL Image objects representing the tiles to be guessed.

    Returns
    -------
    List[bool]
        A list of boolean values indicating which tiles are guessed to be
        correct.

    Notes
    -----
    This function uses the `ask` function to asynchronously ask a model to
    guess each tile.
    """
    mask = []
    prompt = PROMPT_GUESS_IMAGE.format(target)
    for idx, tile_row in enumerate(tiles_images):
        tasks = []
        n_tiles = len(tile_row)
        for jdx, image in enumerate(tile_row):
            tasks.append(ask(idx*n_tiles + jdx, image, prompt))
        # TODO: improve performance
        results = await asyncio.gather(*tasks)
        for result in results:
            matches = re.findall(JSON_MARKDOWN_PATTERN, result)
            if matches and len(matches[0]) > 2:
                try:
                    if json.loads(matches[0][1])['answer']:
                        mask.append(True)
                        continue
                except json.JSONDecodeError:
                    pass
            mask.append(False)
    return mask

def detected_captcha(driver: AntiDetectDriver,
                     timeout_to_detect_captcha_iframe=0.5):
    """
    Checks if a captcha challenge has been detected on the webpage.

    This function switches the driver's focus to the default content of the
    page, finds all iframe elements on the page, and checks if the first
    iframe's title contains the string 'reCAPTCHA'. If so, it returns True,
    indicating that a captcha challenge has been detected.

    Parameters
    ----------
    driver : AntiDetectDriver
        The driver instance to use for interacting with the webpage.

    Returns
    -------
    bool
        True if a captcha challenge is detected, False otherwise.

    Notes
    -----
    This function assumes that the captcha challenge is contained within an
    iframe.
    If the structure of the webpage changes, this function may need to be
    updated.
    """
    driver.switch_to.default_content()
    frames = driver.find_all(
        'iframe', by='tag name', timeout=timeout_to_detect_captcha_iframe
    )
    if frames and len(frames) > 1:
        return 'reCAPTCHA' in frames[0].get_attribute('title')
    return False

def was_solved(driver: AntiDetectDriver):
    """
    Checks if the reCAPTCHA challenge has been solved.

    This function switches the driver's focus to the default content, then to
    the reCAPTCHA iframe, and checks if the reCAPTCHA checkbox has been checked.

    Parameters
    ----------
    driver : AntiDetectDriver
        The driver instance to use for interacting with the webpage.

    Returns
    -------
    bool
        True if the reCAPTCHA challenge has been solved, False otherwise.
    """
    driver.switch_to.default_content()
    driver.switch_to_frame(value="//iframe[@title='reCAPTCHA']", by='xpath')
    rc_anchor = driver.find('recaptcha-anchor')
    return 'recaptcha-checkbox-checked' in rc_anchor.get_attribute('class')

def click_captcha_checkbox(driver: AntiDetectDriver):
    """
    Clicks the reCAPTCHA checkbox to start the challenge.

    This function switches the driver's focus to the default content, then to
    the reCAPTCHA iframe, and attempts to click the reCAPTCHA checkbox. If the
    click is intercepted, it reloads the challenge.

    Parameters
    ----------
    driver : AntiDetectDriver
        The driver instance to use for interacting with the webpage.
    """
    driver.switch_to.default_content()
    driver.switch_to_frame(value="//iframe[@title='reCAPTCHA']", by='xpath')
    recaptcha_anchor = driver.find('recaptcha-anchor')
    class_list = (  # effect of hovering 'I'm not a robot' click button
        "recaptcha-checkbox goog-inline-block recaptcha-checkbox-unchecked "
        "rc-anchor-checkbox recaptcha-checkbox-hover"
    )
    driver.set_class_to(recaptcha_anchor, class_list=class_list)
    sleep(driver, minimum=0.3, maximum=0.5)
    try:
        recaptcha_anchor.click()
    except ElementClickInterceptedException:
        reload_challenge(driver)

def get_rows_and_tiles_and_image_url(driver):
    """
    Retrieves the rows of tiles, the tiles themselves, and the image URL from
    a captcha challenge.

    This function extracts the necessary data from the captcha challenge on a
    webpage, including the rows of tiles, the tiles as images, and the URL of
    the image used in the captcha.

    Parameters
    ----------
    driver : AntiDetectDriver
        The driver instance to use for interacting with the webpage.

    Returns
    -------
    tuple
        A tuple containing:
        - A list of BeautifulSoup objects representing the rows of tiles.
        - A list of lists containing the tiles of the image.
        - The URL of the image used in the captcha.

    Notes
    -----
    If the image cannot be retrieved, the function logs a warning, reloads the
    challenge, and returns None for the image-related values.
    """
    rows, n_rows, n_cols, image_url = get_tiles_data(driver)
    img = get_image(image_url)
    if not img:
        logger.warning("Failed getting challenge image: %s", image_url)
        reload_challenge(driver)
        return None, None, None
    tiles = split_image(img, n_rows, n_cols)

    return rows, tiles, image_url

async def get_rows_and_mask_and_target_and_image_url(driver: AntiDetectDriver):
    """
    Asynchronously retrieves the rows of tiles, a mask indicating the correct 
    iles, the target object text, and the image URL from a captcha challenge.

    This function calls `get_rows_and_tiles_and_image_url` to get the necessary
    data, then uses the `get_guess_mask` function to generate a mask indicating
    which tiles are guessed to be correct based on the target and images.

    Parameters
    ----------
    driver : AntiDetectDriver
        The driver instance to use for interacting with the webpage.

    Returns
    -------
    tuple
        A tuple containing:
        - A list of BeautifulSoup objects representing the rows of tiles.
        - A list of boolean values indicating which tiles are guessed to be
        correct.
        - The text of the target object.
        - The URL of the image used in the captcha.

    Notes
    -----
    If the tiles cannot be retrieved, the function returns None for the tiles
    and mask.
    """
    rows, tiles, image_url = get_rows_and_tiles_and_image_url(driver)
    target_object = driver.find(
        '//div[contains(@class, "rc-imageselect-desc")]//strong',
        by='xpath'
    )
    if tiles is None:
        return None, None, target_object.text, image_url
    mask = await get_guess_mask(target_object.text, tiles)
    return rows, mask, target_object.text, image_url

def check_tile(driver: AntiDetectDriver, tabindex: int):
    """
    Checks a captcha tile by changing its class and clicking the checkbox.

    This function finds the tile element by its tabindex, changes its class to
    indicate it is selected, and clicks the checkbox within the tile to select
    it.

    Parameters
    ----------
    driver : AntiDetectDriver
        The driver instance to use for interacting with the webpage.
    tabindex : int
        The tabindex of the tile to be checked.

    Returns
    -------
    WebElement
        The tile element that was checked.
    """
    tile_element = driver.find(
        f"//td[@tabindex='{tabindex}']", by='xpath'
    )
    # besides of clicking, we have to change the class
    driver.set_class_to(
        tile_element,
        class_list='rc-imageselect-tile rc-imageselect-tileselected'
    )
    tile_checkbox = driver.child(
        tile_element,
        value='rc-imageselect-checkbox', by='class name'
    )
    driver.set_attribute_to(tile_checkbox, attribute="style", value="")
    tile_checkbox.click()
    return tile_element

def uncheck_tile(driver: AntiDetectDriver, tabindex: int):
    """
    Unchecks a captcha tile by changing its class and clicking the checkbox.

    This function finds the tile element by its tabindex, changes its class to
    indicate it is not selected, and clicks the checkbox within the tile to
    deselect it.

    Parameters
    ----------
    driver : AntiDetectDriver
        The driver instance to use for interacting with the webpage.
    tabindex : int
        The tabindex of the tile to be unchecked.

    Returns
    -------
    WebElement
        The tile element that was unchecked.
    """
    tile_element = driver.find(
        f"//td[@tabindex='{tabindex}']", by='xpath'
    )
    tile_checkbox = driver.child(
        tile_element,
        value='rc-imageselect-checkbox', by='class name'
    )
    tile_checkbox.click()
    driver.set_attribute_to(
        tile_checkbox, attribute="style", value="display: none;"
    )
    driver.set_class_to(
        tile_element,
        class_list='rc-imageselect-tile'
    )
    return tile_element

def click_verify(driver: AntiDetectDriver):
    """
    Clicks the 'verify' button on the captcha challenge page.

    This function switches the driver's focus to the challenge frame, attempts
    to click the 'verify' button, and returns True if the click is successful.
    If the click is intercepted, it returns False.

    Parameters
    ----------
    driver : AntiDetectDriver
        The driver instance to use for interacting with the webpage.

    Returns
    -------
    bool
        True if the 'verify' button was clicked successfully, False otherwise.
    """
    go_to_challenge_frame(driver)
    try:
        driver.click('recaptcha-verify-button')
        logger.debug("Clicked 'verify'!")
        sleep(driver, minimum=0.8, maximum=1.3)
        return True
    except ElementClickInterceptedException:
        return False

async def check_changed_tile(driver: AntiDetectDriver,
                             target: str,
                             table_data: BeautifulSoup):
    """
    Checks if a captcha tile has changed and performs a click action
    accordingly.

    This function attempts to guess the image of a tile and performs a click
    action if the uess is correct. If the tile is already selected and the
    guess is incorrect, or if the tile is not selected and the guess is
    correct, it performs the opposite action.

    Parameters
    ----------
    driver : AntiDetectDriver
        The driver instance to use for interacting with the webpage.
    target : str
        The target string to be used in the prompt for guessing the tiles.
    table_data : BeautifulSoup
        The BeautifulSoup object containing the data of the table, including
        the tile's image.

    Returns
    -------
    None
        This function does not return any value.
    """
    """Try to guess image and perform click"""
    img = get_image(table_data.img.attrs['src'])
    mask = await get_guess_mask(target, [[img]])
    tabindex = table_data.attrs['tabindex']
    class_list = table_data.attrs['class']
    if mask[0]:
        if 'rc-imageselect-tileselected' not in class_list:
            check_tile(driver, tabindex)
        return
    if 'rc-imageselect-tileselected' in class_list:
        uncheck_tile(driver, tabindex)

async def reperform_guess(driver, target, image_url):
    """
    Repeats the 'guessing' procedure for new tiles in a captcha challenge.

    This method scans all images, checks for changes, and performs a click
    action accordingly. It continues to scan until no changes are detected.

    Parameters
    ----------
    driver : AntiDetectDriver
        The driver instance to use for interacting with the webpage.
    target : str
        The target string to be used in the prompt for guessing the tiles.
    image_url : str
        The URL of the image used in the captcha.

    Returns
    -------
    None
        This function does not return any value.
    """

    # First scan on all images
    rows, _, __, ___ = get_tiles_data(driver)
    table_data = []
    for row in rows:
        table_data.extend(row.find_all('td'))
    for td in table_data:
        if td.img.attrs['src'] != image_url:
            await check_changed_tile(driver, target, td)
    sleep(driver, minimum=0.3, maximum=0.6)

    # Scan over again until detects no change
    # NOTE: this might be sensitive to sleeping interval, i.e.,
    # if interpreter sleeps quick enough, it might skip some
    # tile changes
    this_keep_on = True
    while this_keep_on:
        new_rows, _, __, ___ = get_tiles_data(driver)
        new_table_data = []
        for row in new_rows:
            new_table_data.extend(row.find_all('td'))
        this_keep_on = False
        for td, td_new in zip(table_data, new_table_data):
            if td.img.attrs['src'] != td_new.img.attrs['src']:
                await check_changed_tile(driver, target, td_new)
                table_data = new_table_data
                this_keep_on = True
                break

async def perform_guess(driver):
    """
    Performs a guessing procedure for the captcha tiles.

    This function retrieves the rows of tiles, a mask indicating the correct
    tiles, the target object text, and the image URL from a captcha challenge.
    It then checks or unchecks the tiles based on the mask and performs a
    click action if there are tile changes.

    Parameters
    ----------
    driver : AntiDetectDriver
        The driver instance to use for interacting with the webpage.

    Returns
    -------
    tuple
        A tuple containing:
        - A list of BeautifulSoup objects representing the rows of tiles.
        - A list of boolean values indicating which tiles are guessed to be
        correct.
        - The text of the target object.
        - The URL of the image used in the captcha.
    """
    (
        rows, mask, target, image_url
    ) = await get_rows_and_mask_and_target_and_image_url(driver)
    if (rows, mask) == (None, None):
        return None, None, None, None
    table_data = []
    for row in rows:
        table_data.extend(row.find_all('td'))
    for select, td in zip(mask, table_data):
        tabindex = td.attrs['tabindex']
        class_list = td.attrs['class']
        if 'rc-imageselect-tileselected' in class_list:
            if not select:
                uncheck_tile(driver, tabindex)
                sleep(driver, minimum=0.3, maximum=0.6)
            continue
        if select:
            check_tile(driver, tabindex)
            sleep(driver, minimum=0.6, maximum=0.9)
    sleep(driver, minimum=1.2, maximum=2.5)
    # in case there are tiles changes:
    await reperform_guess(driver, target, image_url)
    return rows, mask, target, image_url

async def solve_recaptcha2(driver: AntiDetectDriver,
                           timeout_to_detect_captcha_iframe=0.5):
    """
    Attempts to solve a reCAPTCHA v2 challenge on a webpage.

    This function checks if a captcha challenge is detected, clicks the captcha
    checkbox to start the challenge, and then enters a loop where it attempts
    to solve the challenge by guessing the tiles. It continues to attempt
    solutions until the challenge is solved or the process is
    interrupted.

    Parameters
    ----------
    driver : AntiDetectDriver
        The driver instance to use for interacting with the webpage.

    Returns
    -------
    bool
        True if the reCAPTCHA challenge was successfully solved, False
        otherwise.

    Notes
    -----
    This function assumes that the captcha challenge is contained within an
    iframe. If the structure of the webpage changes, this function may need to
    be updated.
    """
    if not detected_captcha(driver, timeout_to_detect_captcha_iframe):
        return True

    click_captcha_checkbox(driver)
    go_to_challenge_frame(driver)

    keep_on = True
    while keep_on:

        if flip_coin():
            reload_challenge(driver)

        sleep(driver)
        rows, mask, target, image_url = await perform_guess(driver)
        if (rows, mask) == (None, None):
            continue
        
        sleep(driver, minimum=0.5, maximum=0.8)
        # We decided to put this outside 'perform_guess' logic,
        # since recaptcha2 might raise 'try again' prior to
        # clicking 'verify'.
        # Also, the model might guess wrongly, even guessing none
        # are the correct image. Anyways, the following logic
        # is a callback-like
        if not click_verify(driver):
            reload_challenge(driver)
            continue
        if was_solved(driver):
            keep_on = False
            continue
        if detected_captcha(driver):
            go_to_challenge_frame(driver)
            verify_select_more = driver.find(
                value='rc-imageselect-error-select-more', by='class name'
            )
            verify_dynamic_more = driver.find(
                value='rc-imageselect-error-dynamic-more', by='class name'
            )
            verify_select_something = driver.find(
                value='rc-imageselect-error-select-more', by='class name'
            )
            if verify_select_more.get_attribute('style') == '':
                driver.set_attribute_to(
                    verify_select_more,
                    attribute="style",
                    value="display: none;"
                )
                reload_challenge(driver)
                continue
            elif verify_dynamic_more.get_attribute('style') == '':
                sleep(driver, minimum=1.5, maximum=3)
                _, __, ___, new_image_url = get_tiles_data(driver)
                if new_image_url != image_url:
                    reload_challenge(driver)
                    continue
                await reperform_guess(driver, target, image_url)
                click_verify(driver)
                if was_solved(driver):
                    keep_on = False
                    continue
                reload_challenge(driver)
                continue
            elif verify_select_something.get_attribute('style') == '':
                reload_challenge(driver)
                continue
            # TODO: handle 'select all'
            reload_challenge(driver)
            continue

        keep_on = False

    return True

def solve_captcha(driver: AntiDetectDriver):
    """
    Solves a captcha challenge using the provided driver.

    This function attempts to solve a captcha challenge by interacting with the
    captcha elements on the page. It uses various helper functions to perform
    the necessary actions, such as clicking on elements, scrolling, and sending
    keys.

    Parameters
    ----------
    driver : AntiDetectDriver
        The driver instance to use for interacting with the captcha.

    Returns
    -------
    bool
        True if the captcha was successfully solved, False otherwise.
    """
    # NOTE: in future, we might implement other solvers.
    challenge = 'recaptcha2'
    task = None
    try:
        loop = asyncio.get_running_loop()
        task = loop.create_task(solve_recaptcha2(driver))
    except RuntimeError:
        if challenge == 'recaptcha2':
            task = solve_recaptcha2(driver)
    try:
        asyncio.run(task)
    except RuntimeError:
        try:
            # NOTE: this allows running in jupyter without using 'await'
            import nest_asyncio  # pylint --disable=import-outside-toplevel
            nest_asyncio.apply()
            asyncio.run(task)
        except (ImportError, ModuleNotFoundError) as err:
            logger.error(err)
            logger.warning("Must install nest_asyncio for running in Jupyter")
            raise err
    return task.result()
