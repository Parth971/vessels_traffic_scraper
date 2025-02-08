from enum import StrEnum
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict
from fastapi import FastAPI
from pydantic import BaseModel
from main import main

app = FastAPI()
executor = ThreadPoolExecutor(max_workers=5)


async def run_scraper_async(terms: list[str], script: str) -> Dict[str, Any]:
    """Run the scraper asynchronously using ThreadPoolExecutor."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(executor, main, terms, script)


class Script(StrEnum):
    vesselfinder = "vesselfinder"
    marinetraffic = "marinetraffic"


class ScrapeRequest(BaseModel):
    script: Script
    search_term: str = "INTERSEA TRAVELER"


@app.post("/scrape/")
async def scrape(request: ScrapeRequest) -> Dict[str, Any]:
    """Non-blocking scraper endpoint."""
    start_time = time.time()

    result = await run_scraper_async([request.search_term], request.script)

    end_time = time.time()
    elapsed_time = round(end_time - start_time, 2)

    return {
        "elapsed_time": elapsed_time,
        "result": result,
    }
