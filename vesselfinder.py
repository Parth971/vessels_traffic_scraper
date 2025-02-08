import re
import time
import traceback
from datetime import datetime, timezone
from typing import Any, Dict, List
from bs4 import BeautifulSoup

from botasaurus import bt
from botasaurus.task import task
from botasaurus.browser import browser, Driver
from botasaurus.soupify import soupify
from botasaurus.user_agent import UserAgent

from logger import ScraperLog
from settings import settings


def convert_time_format(datetime_str: str) -> str:
    match = re.search(r"([A-Za-z]+ \d{1,2}), (\d{2}:\d{2})", datetime_str)
    if not match:
        ScraperLog.info(f"Date format not able to match pattern: {datetime_str}")
        return ""

    date_part, time_part = match.groups()

    dt = datetime.strptime(f"{date_part}, {time_part}", "%b %d, %H:%M")
    dt = dt.replace(year=datetime.now(timezone.utc).year)

    return dt.strftime("%Y-%m-%d %H:%M")


@browser(
    max_retry=1,
    output=None,
    reuse_driver=settings.reuse_browser,
    proxy=settings.proxy,
    close_on_crash=True,
    raise_exception=False,
    block_images_and_css=True,
    wait_for_complete_page_load=False,
    headless=settings.headless,
    user_agent=UserAgent.RANDOM,
)  # type: ignore
def scrape_html(driver: Driver, data: Dict[str, Any]) -> str:
    link = data["link"]
    search_text = data["search_text"]
    wait_time = 5
    sleep_time = 2

    if driver.config.is_new:
        ScraperLog.debug(f"Opening new driver for search term {search_text}")
        driver.get(link)
        time.sleep(sleep_time)

        btns = driver.select_all(".qc-cmp2-footer button", wait=wait_time)
        for btn in btns:
            if btn.text.lower() == "agree":
                btn.click()
                time.sleep(sleep_time // 2)
                break

    search_tag = driver.select('input[name="tsf"]')
    if search_tag is None:
        driver.save_screenshot()
        raise Exception("Search tag is missing!")

    search_tag.click()
    time.sleep(sleep_time)
    for idx in range(0, len(search_text), 2):
        chars = search_text[idx : idx + 2]  # noqa
        search_tag.type(chars, wait=wait_time)
        time.sleep(0.4)

    time.sleep(sleep_time)

    result_elements = driver.select_all("div.E5ZNs.xaBpY._-0TrM > div > div")

    for result_element in result_elements:
        if (
            result_element.select("div.Qr4sP")
            and result_element.select("div.Qr4sP").text.lower().strip()
            == search_text.lower().strip()
            and "Container Ship" in result_element.select("div.-JP51").text
        ):
            result_element.click()
            time.sleep(sleep_time * 2)
            break
    else:
        ScraperLog.warning(f"Not found in result! Skipping {search_text}")
        results = [
            [result_element.select("span").text, result_element.select("p").text]
            for result_element in result_elements
            if result_element.select("span") and result_element.select("p")
        ]
        filename = f"{search_text.lower().replace(' ', '_')}_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.png"
        driver.save_screenshot(filename=filename)
        ScraperLog.debug(f"Saved screenshot to {filename}")
        ScraperLog.debug(f"Other Options: {results}")
        driver.reload()
        return ""

    html: str = driver.page_html
    return html


def extract_data(soup: BeautifulSoup) -> Dict[str, Any]:
    last_port_name = None
    next_port_name = None
    last_port_code = None
    next_port_code = None
    last_port_time = None
    next_port_time = None
    status = None

    next_port_parent = soup.select_one("div.s0 > .flx.vcenter")
    last_port_parent = soup.select_one("div.s0 > div.flx.vcenter._rLk01")

    if last_port_parent:
        last_port_tag = last_port_parent.select_one("a._npNa")
        if last_port_tag is None:
            last_port_tag = last_port_parent.select_one("._3-Yih")

        if last_port_tag:
            last_port_name = last_port_tag.text if last_port_tag else None

    if next_port_parent:
        next_port_tag = next_port_parent.select_one("a._npNa")
        if next_port_tag is None:
            next_port_tag = next_port_parent.select_one("._3-Yih")

        if next_port_tag:
            next_port_name = next_port_tag.text if next_port_tag else None

    if last_port_parent:
        last_port_time_tag = last_port_parent.select_one("div._value")
        if last_port_time_tag:
            last_port_time = convert_time_format(last_port_time_tag.text.strip())

    if next_port_parent:
        next_port_time_tag = next_port_parent.select_one("div._value")
        if next_port_time_tag:
            if "ARRIVED" in next_port_time_tag.text:
                status = "Arrived"
            else:
                status = "Estimated"
            next_port_time = convert_time_format(next_port_time_tag.text.strip())

    return {
        "last_port_name": last_port_name,
        "last_port_code": last_port_code,
        "last_port_etd": last_port_time,
        "next_port_name": next_port_name,
        "next_port_code": next_port_code,
        "next_port_date": next_port_time,
        "next_port_date_status": status,
    }


def write_to_file(data: List[Dict[str, Any]], result: List[Dict[str, Any]]) -> None:
    for d, r in zip(data, result):
        r["search_text"] = d["search_text"]

    settings.output_dir.mkdir(parents=True, exist_ok=True)

    bt.write_json(result, settings.output_dir / "vesselfinder.json")


@task(
    output=write_to_file,
    close_on_crash=True,
    create_error_logs=False,
    parallel=settings.parallel,
    raise_exception=True,
)  # type: ignore
def scrape_data(data: Dict[str, Any]) -> Dict[str, Any]:
    search_text = data["search_text"]
    ScraperLog.info(f"Scraping vesselfinder for {search_text}")
    html = scrape_html(data)
    try:
        if html == "":
            return {}
        return extract_data(soupify(html))
    except Exception:
        ScraperLog.error(traceback.format_exc())
        ScraperLog.error(f"Failed to extract data for {search_text}")
        return {}


def scrape_vesselfinder(data: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    result: List[Dict[str, Any]] = scrape_data(data)
    return result
