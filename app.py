from contextlib import asynccontextmanager
import time
import asyncio
from enum import StrEnum
from typing import Any, Dict
from concurrent.futures import ProcessPoolExecutor

from pydantic import BaseModel
from main import main

from fastapi import FastAPI, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader
from fastapi.responses import RedirectResponse

executor = ProcessPoolExecutor(max_workers=2)


@asynccontextmanager
async def lifespan(app: FastAPI) -> Any:
    """Setup and cleanup executor on FastAPI startup/shutdown."""
    yield
    executor.shutdown(wait=True)


app = FastAPI(lifespan=lifespan)

API_KEY = "ilQs2UnK1AMCZfUk822OujYpzokyLtERxhC0DO5F2DlILOAKXXjRWn1ioulbkBjr"
API_KEY_NAME = "X-API-Key"


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


api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=True)


def get_api_key(api_key: str = Security(api_key_header)) -> str:
    """Validates the API key."""
    if api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return api_key


@app.post("/scrape/")
async def scrape(
    request: ScrapeRequest,
    # api_key: str = Depends(get_api_key),
) -> Dict[str, Any]:
    """Non-blocking scraper endpoint."""
    start_time = time.time()

    result = await run_scraper_async([request.search_term], request.script)

    end_time = time.time()
    elapsed_time = round(end_time - start_time, 2)

    return {
        "elapsed_time": elapsed_time,
        "result": result,
    }


@app.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    """Redirect to the API documentation."""
    return RedirectResponse(url="/docs")
