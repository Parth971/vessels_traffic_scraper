import time
import traceback
import pytz
from datetime import datetime
from typing import Any, Dict, List
from bs4 import BeautifulSoup

from botasaurus import bt
from botasaurus.task import task
from botasaurus.browser import browser, Driver
from botasaurus.soupify import soupify
from botasaurus.user_agent import UserAgent

from logger import ScraperLog
from settings import settings

from twocaptcha_extension_python import TwoCaptcha


class TwoCaptchaExtended(TwoCaptcha):  # type: ignore
    def update_files(self, api_key: str) -> None:
        super().update_files(api_key)

        def update_config_contents(content: str) -> str:
            key_replaced = content.replace(
                "autoSubmitForms: false,", "autoSubmitForms: true,"
            ).replace("autoSolveTurnstile: false,", "autoSolveTurnstile: true,")

            return key_replaced

        self.get_file("/common/config.js").update_contents(update_config_contents)


def convert_time_format(datetime_str: str) -> str:
    dt_part, tz_part = datetime_str.split(" (UTC")
    timezone_offset = int(tz_part.rstrip(")"))
    dt = datetime.strptime(dt_part, "%Y-%m-%d %H:%M")
    tz = pytz.FixedOffset(timezone_offset * 60)
    return dt.replace(tzinfo=tz).strftime("%Y-%m-%d %H:%M")


@browser(
    max_retry=1,
    output=None,
    reuse_driver=True,
    extensions=[TwoCaptchaExtended(api_key=settings.captcha_solver_api_key)],
    proxy=settings.proxy,
    close_on_crash=True,
    raise_exception=False,
    headless=settings.headless,
    user_agent=UserAgent.RANDOM,
    block_images_and_css=True,
)  # type: ignore
def scrape_html(driver: Driver, data: Dict[str, Any]) -> str:
    link = data["link"]
    search_text = data["search_text"]
    wait_time = 10
    sleep_time = 2

    if driver.config.is_new:
        ScraperLog.debug(f"Opening new driver for search term {search_text}")
        time.sleep(0.2)
        driver.get_via(
            link,
            referer="https://www.marinetraffic.com/en/ais/home/centerx:-12.0/centery:25.0/zoom:4",
        )
        driver._tab = driver._browser.tabs[0]
        time.sleep(sleep_time * 2)

        btns = driver.select_all(".qc-cmp2-footer button")
        if len(btns) == 0:
            time.sleep(sleep_time * 2)

        btns = driver.select_all(".qc-cmp2-footer button", wait=wait_time)
        for btn in btns:
            if btn.text.lower() == "agree":
                ScraperLog.debug("Found Cookie consent button")
                btn.click()
                time.sleep(sleep_time // 2)
                break

    search_tag = driver.select("#searchMarineTraffic")
    if search_tag is None:
        driver.save_screenshot()
        raise Exception("Search tag is missing!")
    search_tag.click()
    search_tag = driver.select("#searchMT")
    for idx in range(0, len(search_text), 2):
        chars = search_text[idx : idx + 2]  # noqa
        search_tag.type(chars, wait=wait_time)
        time.sleep(0.5)

    result_elements = driver.select_all(
        "div.MuiList-root.MuiList-padding.css-2bw15n li a"
    )
    for result_element in result_elements:
        if (
            result_element.select("span")
            and result_element.select("span").text.lower().strip()
            == search_text.lower().strip()
            and "Container Ship" in result_element.text
        ):
            result_element.click()
            break
    else:
        time.sleep(sleep_time * 2)

        result_elements = driver.select_all(
            "div.MuiList-root.MuiList-padding.css-2bw15n li a"
        )
        for result_element in result_elements:
            if (
                result_element.select("span")
                and result_element.select("span").text.lower().strip()
                == search_text.lower().strip()
                and "Container Ship" in result_element.text
            ):
                result_element.click()
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

    driver.wait_for_element("#mainSection", wait=wait_time)
    time.sleep(sleep_time)

    if driver.title == "Just a moment...":
        time.sleep(sleep_time)

        while driver.title == "Just a moment...":
            ScraperLog.debug("Captcha not solved yet!")
            time.sleep(3)

        time.sleep(sleep_time * 2)

    driver.wait_for_element("#vesselDetails_voyageSection > div", wait=wait_time)
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

    parent = soup.select_one(
        "#vesselDetails_voyageSection > div > div.css-qxl29p > div"
    )
    if parent is None:
        raise Exception("No Parent Container found")

    name_cols = parent.select("div.css-j5005a > div.css-v8enum > div")

    for col in name_cols:
        if "departure from" in col.text.lower():
            span = col.select_one("span")
            anchor = col.select_one("a")
            if span:
                last_port_name = span.text.replace("Departure from ", "").strip()
            if anchor:
                last_port_code = anchor.text.strip()
        elif "arrival at" in col.text.lower():
            span = col.select_one("span")
            anchor = col.select_one("a")
            if span:
                next_port_name = span.text.replace("Arrival at ", "").strip()
            if anchor:
                next_port_code = anchor.text.strip()

    time_cols = parent.select("div.css-j5005a > div.css-bhljxn > div")
    for col in time_cols:
        if "departure" in col.text.lower():
            span = col.select_one("span.css-ypywbf")
            if span:
                last_port_time = convert_time_format(span.text.strip())
        elif "arrival" in col.text.lower():
            span = col.select_one("span.css-ypywbf")
            if span:
                next_port_time = convert_time_format(span.text.strip())
                if "estimated" in col.text.lower():
                    status = "Estimated"
                elif "actual" in col.text.lower():
                    status = "Actual"

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

    bt.write_json(result, settings.output_dir / "marinetraffic.json")


@task(
    output=write_to_file,
    close_on_crash=True,
    create_error_logs=False,
    parallel=settings.parallel,
    raise_exception=False,
)  # type: ignore
def scrape_data(data: Dict[str, Any]) -> Dict[str, Any]:
    search_text = data["search_text"]
    ScraperLog.info(f"Scraping marinetraffic for {search_text}")
    html = scrape_html(data)
    try:
        if html == "":
            return {}
        return extract_data(soupify(html))
    except Exception:
        ScraperLog.error(traceback.format_exc())
        ScraperLog.error(f"Failed to extract data for {search_text}")
        return {}


def scrape_marinetraffic(data: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    result: List[Dict[str, Any]] = scrape_data(data)
    return result
