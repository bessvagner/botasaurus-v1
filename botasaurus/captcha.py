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
    return (maximum - minimum)*random.random() + minimum

def sleep(driver: AntiDetectDriver,
          minimum: Number = RANDOM_SLEEP_INTERVAL[0],
          maximum: Number = RANDOM_SLEEP_INTERVAL[1]) -> None:
    driver.sleep(random_sleep_interval(minimum, maximum))

def flip_coin():
    return random.choice((False, True))

def go_to_challenge_frame(driver: AntiDetectDriver):
    driver.switch_to.default_content()
    frames = driver.find_all('iframe', by='tag name')
    driver.switch_to.frame(frames[2])

def reload_challenge(driver: AntiDetectDriver):
    go_to_challenge_frame(driver)
    try:
        driver.find('recaptcha-reload-button').click()
    except ElementClickInterceptedException:
        pass
    go_to_challenge_frame(driver)

def get_image(url):
    logger.info("Downloading captcha image: %s", url)
    response = requests.get(url, timeout=20)
    img = None
    if response.ok and response.content:
        img = Image.open(BytesIO(response.content))
        logger.info("\t|_ Download sucsess!")
    return img

def get_tiles_data(driver: AntiDetectDriver) -> Tuple[List[BeautifulSoup], int, int, float]:  # noqa E501
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
    logger.info("Trying to guess tile %s", idx)
    # TODO: allow the use of other models (APIs)
    response = await AsyncGoogleVision().answer(image, prompt)
    logger.info("Model guessed tile %s: %s", idx, response)
    return response

async def get_guess_mask(target: str,
                         tiles_images: List[Image.Image]) -> List[bool]:
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

def detected_captcha(driver: AntiDetectDriver):
    driver.switch_to.default_content()
    # rc_anchor = driver.find('rc-anchor-container')
    # 'recaptcha-checkbox goog-inline-block recaptcha-checkbox-unchecked rc-anchor-checkbox recaptcha-checkbox-expired'
    # 'recaptcha-checkbox goog-inline-block recaptcha-checkbox-unchecked rc-anchor-checkbox'
    # 'recaptcha-checkbox goog-inline-block recaptcha-checkbox-unchecked rc-anchor-checkbox recaptcha-checkbox-checked'
    frames = driver.find_all('iframe', by='tag name')
    if frames and len(frames) > 1:
        return 'reCAPTCHA' in frames[0].get_attribute('title')
    return False

def was_solved(driver: AntiDetectDriver):
    driver.switch_to.default_content()
    driver.switch_to_frame(value="//iframe[@title='reCAPTCHA']", by='xpath')
    rc_anchor = driver.find('recaptcha-anchor')
    return 'recaptcha-checkbox-checked' in rc_anchor.get_attribute('class')

def click_captcha_checkbox(driver: AntiDetectDriver):
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
    rows, n_rows, n_cols, image_url = get_tiles_data(driver)
    img = get_image(image_url)
    if not img:
        logger.warning("Failed getting challenge image: %s", image_url)
        reload_challenge(driver)
        return None, None, None
    tiles = split_image(img, n_rows, n_cols)

    return rows, tiles, image_url

async def get_rows_and_mask_and_target_and_image_url(driver: AntiDetectDriver):

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
    """Images can change while trying to solve challenge.
    This method redo the 'guessing' procedure for the new tiles
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

async def solve_recaptcha2(driver: AntiDetectDriver):

    if not detected_captcha(driver):
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
