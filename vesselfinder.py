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


js_script = """
    function getWorkerData(text, eivn, compId) {
        return new Promise((resolve, reject) => {
            const myWorker = window.__gsfworker;

            const handler = (event) => {
                myWorker.removeEventListener("message", handler); // Cleanup
                resolve(event.data);  // Resolve the Promise with the worker response
            };

            myWorker.addEventListener("message", handler);

            // Send request
            myWorker.postMessage({ cmd: "ms", text, eivn, compId });

            // Optional: Reject if no response in 5 seconds
            setTimeout(() => {
                myWorker.removeEventListener("message", handler);
                reject(new Error("Worker timeout"));
            }, 5000);
        });
    }
    return getWorkerData(args, "", 123);
"""


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
        clicked = False
        for btn in btns:
            if btn.text.lower() == "agree":
                btn.click()
                clicked = True
                break

        if clicked:
            time.sleep(sleep_time // 2)

    response_data = driver.run_js(js_script, search_text)
    results = response_data.get("list", [])
    for result in results:
        if (
            result.get("type") == "Container Ship"
            and result.get("name", "").lower() == search_text.lower()
        ):
            imo = result["imo"]
            driver.get_via(
                f"https://www.vesselfinder.com/vessels/details/{imo}",
                referer=link,
            )
            break
    else:
        ScraperLog.warning(f"Not found in result! Skipping {search_text}")
        results = [
            result.get("name", "") + " | " + result.get("type", "")
            for result in results
        ]
        filename = f"{search_text.lower().replace(' ', '_')}_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.png"
        driver.save_screenshot(filename=filename)
        ScraperLog.debug(f"Saved screenshot to {filename}")
        ScraperLog.debug(f"Other Options: {results}")
        driver.reload()
        return ""

    time.sleep(sleep_time)

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
