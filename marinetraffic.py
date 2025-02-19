import time
import traceback
import pytz
from datetime import datetime
from typing import Any, Dict, List, Tuple
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
            key_replaced = (
                content.replace("autoSubmitForms: false,", "autoSubmitForms: true,")
                .replace("autoSolveTurnstile: false,", "autoSolveTurnstile: true,")
                .replace("repeatOnErrorTimes: 0,", "repeatOnErrorTimes: 5,")
            )

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
    reuse_driver=settings.reuse_browser,
    extensions=[TwoCaptchaExtended(api_key=settings.captcha_solver_api_key)],
    proxy=settings.proxy,
    close_on_crash=True,
    raise_exception=False,
    headless=settings.headless,
    user_agent=UserAgent.RANDOM,
    block_images_and_css=True,
)  # type: ignore
def scrape_html(driver: Driver, data: Dict[str, Any]) -> Tuple[str, str]:
    detail_page_url = ""
    link = data["link"]
    search_text = data["search_text"]
    wait_time = 10
    sleep_time = 2

    referer = (
        "https://www.marinetraffic.com/en/ais/home/centerx:-12.0/centery:25.0/zoom:4"
    )

    if driver.config.is_new:
        ScraperLog.debug(f"Opening new driver for search term {search_text}")
        time.sleep(0.2)
        driver.get_via("https://www.marinetraffic.com", referer=referer)
        # driver._tab = driver._browser.tabs[0]
        # time.sleep(sleep_time * 2)

        # btns = driver.select_all(".qc-cmp2-footer button")
        # if len(btns) == 0:
        #     time.sleep(sleep_time * 2)

        # btns = driver.select_all(".qc-cmp2-footer button", wait=wait_time)
        # for btn in btns:
        #     if btn.text.lower() == "agree":
        #         ScraperLog.debug("Found Cookie consent button")
        #         btn.click()
        #         time.sleep(sleep_time // 2)
        #         break

        # driver.reload()

    headers = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "en-US,en;q=0.9",
        "priority": "u=1, i",
        "sec-ch-ua": '"Not A(Brand";v="8", "Chromium";v="132", "Google Chrome";v="132"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Linux"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "x-newrelic-id": "undefined",
        "x-requested-with": "XMLHttpRequest",
    }
    url = f"https://www.marinetraffic.com/en/global_search/search?term={search_text}"
    ScraperLog.debug("Requesting...")
    response = driver.requests.get(url=url, headers=headers, referer=referer)
    ScraperLog.debug("Request completed...")
    response.raise_for_status()

    response_data = response.json()
    results = response_data.get("results", [])
    for result in results:
        if "Container Ship" in result.get("desc", ""):
            endpoint = result["url"]
            detail_page_url = f"https://www.marinetraffic.com{endpoint}"
            driver.get_via(detail_page_url, referer=link)
            break
    else:
        ScraperLog.warning(f"Not found in result! Skipping {search_text}")
        results = [
            result.get("value", "") + " | " + result.get("desc", "")
            for result in results
        ]
        ScraperLog.debug(f"Other Options: {results}")
        return "", detail_page_url

    time.sleep(sleep_time)

    if driver.title == "Just a moment...":
        time.sleep(sleep_time)

        while driver.title == "Just a moment...":
            ScraperLog.debug("Captcha not solved yet!")
            time.sleep(3)

        time.sleep(sleep_time * 2)

    driver.wait_for_element("#vesselDetails_voyageSection > div", wait=wait_time)
    html: str = driver.page_html
    return html, detail_page_url


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
    html, detail_page_url = scrape_html(data)
    try:
        if html == "":
            return {}
        return {**extract_data(soupify(html)), "url": detail_page_url}
    except Exception:
        ScraperLog.error(traceback.format_exc())
        ScraperLog.error(f"Failed to extract data for {search_text}")
        return {}


def scrape_marinetraffic(data: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    result: List[Dict[str, Any]] = scrape_data(data)
    return result
