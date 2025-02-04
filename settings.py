from pathlib import Path
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    captcha_solver_api_key: str = Field(default="", description="2captcha API key")
    parallel: int = Field(default=3, description="Number of parallel browsers")
    output_dir: Path = Field(
        default=BASE_DIR / "output", description="Output directory"
    )
    search_terms_filepath: Path = Field(
        default=BASE_DIR / "sample_data.csv",
        description="Filepath of a CSV with first column as vessel names",
    )
    proxy: Optional[List[str] | str] = Field(default=None, description="Proxy as List")
    headless: bool = Field(default=True, description="Run in headless mode")
    logs_directory: Path = Field(default=BASE_DIR / "logs")
    debug: bool = Field(default=False)

    class Config:
        env_file = ".env"


settings = Settings()
