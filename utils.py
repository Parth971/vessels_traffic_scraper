import csv
from pathlib import Path
import time
from typing import Any, List

from logger import ScraperLog


def get_search_terms(filepath: Path) -> List[str]:
    with filepath.open(newline="", encoding="utf-8") as file:
        reader = csv.reader(file)
        first_column = [row[0] for row in reader]

    return first_column[1:]


def timetracker(func: Any) -> Any:
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        ScraperLog.debug(
            f"Function {func.__name__} took {round(end_time - start_time, 2)} seconds"
        )

        return result

    return wrapper
