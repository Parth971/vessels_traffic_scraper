import argparse
from typing import Any, Dict, List, Optional

from logger import ScraperLog
from marinetraffic import scrape_marinetraffic
from utils import timetracker
from vesselfinder import scrape_vesselfinder


def run_vesselfinder(terms: List[str]) -> List[Dict[str, Any]]:
    ScraperLog.info("Running vesselfinder")
    link = "https://www.vesselfinder.com/"
    data_items = [{"link": link, "search_text": term} for term in terms]

    return scrape_vesselfinder(data_items)


def run_marinetraffic(terms: List[str]) -> List[Dict[str, Any]]:
    ScraperLog.info("Running marinetraffic")
    # link = "https://www.marinetraffic.com/en/ais/home/centerx:-12.0/centery:25.0/zoom:4"
    link = "https://www.marinetraffic.com/en/ais/details/ships/shipid:202330/mmsi:235335000/imo:9241310/vessel:EVER_EAGLE"  # noqa
    data_items = [{"link": link, "search_text": term} for term in terms]

    return scrape_marinetraffic(data_items)


@timetracker
def main(terms: List[str], script: str) -> Optional[List[Dict[str, Any]]]:
    if script == "vesselfinder":
        result = run_vesselfinder(terms)
        return result

    if script == "marinetraffic":
        result = run_marinetraffic(terms)
        return result

    return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run vessel tracking scrapers.")

    parser.add_argument(
        "--name",
        choices=["vesselfinder", "marinetraffic"],
        required=True,
        help="Specify which script to run (vesselfinder or marinetraffic).",
    )
    parser.add_argument(
        "--terms",
        nargs="+",  # Accept multiple terms as a list
        required=True,
        help="List of search terms to use.",
    )

    args = parser.parse_args()
    result = main(args.terms, args.name)
    assert result is not None
    ScraperLog.info(f"Total Results: {len(result)}")
