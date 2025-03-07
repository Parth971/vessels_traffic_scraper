# from contextlib import asynccontextmanager
import time
import asyncio
from enum import StrEnum
from typing import Any, Dict, List, Optional
from concurrent.futures import ProcessPoolExecutor

import psutil
from pydantic import BaseModel
from logger import ScraperLog
from main import main

from fastapi import FastAPI, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader
from fastapi.responses import RedirectResponse


# @asynccontextmanager
# async def lifespan(app: FastAPI) -> Any:
#     """Setup and cleanup executor on FastAPI startup/shutdown."""
#     yield
#     executor.shutdown(wait=True)


def kill_bridge_js_processes() -> None:
    """Find and terminate Node.js processes running bridge.js specifically."""
    for proc in psutil.process_iter(attrs=["pid", "name", "cmdline"]):
        try:
            cmdline = proc.info["cmdline"]
            if cmdline and any("bridge.js" in arg for arg in cmdline):
                proc.terminate()  # Graceful shutdown
                proc.wait(timeout=5)  # Wait up to 5 seconds before force-killing
                if proc.is_running():  # If still running, force kill
                    proc.kill()
                print(f"Killed bridge.js process (PID: {proc.info['pid']})")
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue  # Process already gone or no permission to access


app = FastAPI()

API_KEY = "ilQs2UnK1AMCZfUk822OujYpzokyLtERxhC0DO5F2DlILOAKXXjRWn1ioulbkBjr"
API_KEY_NAME = "X-API-Key"


async def run_scraper_async(
    terms: list[str], script: str, executor: ProcessPoolExecutor
) -> Optional[List[Dict[str, Any]]]:
    """Run the scraper asynchronously using ProcessPoolExecutor."""
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
    executor = ProcessPoolExecutor(max_workers=1)

    try:
        result = await run_scraper_async(
            [request.search_term], request.script, executor
        )
        end_time = time.time()
        elapsed_time = round(end_time - start_time, 2)

        return {
            "elapsed_time": elapsed_time,
            "result": result,
        }
    except Exception as e:
        raise e
    finally:
        ScraperLog.debug("Shutting down executor")
        kill_bridge_js_processes()
        executor.shutdown(wait=True)
        ScraperLog.debug("Executor shut down")


@app.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    """Redirect to the API documentation."""
    return RedirectResponse(url="/docs")
