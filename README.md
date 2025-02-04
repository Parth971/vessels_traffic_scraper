# Vessel Tracking Scraper

This project scrapes vessel tracking data from MarineTraffic and VesselFinder using Python.

## Requirements
- **Python Version**: 3.12

## Setup Instructions

### 1. Create a Virtual Environment
```sh
python3.12 -m venv venv
```

### 2. Activate Virtual Environment
#### On macOS/Linux:
```sh
source venv/bin/activate
```
#### On Windows:
```sh
venv\Scripts\activate
```

### 3. Install Dependencies
```sh
pip install -r requirements.txt
```

## Configuration
This project uses a `.env` file to manage various settings and credentials. Example:
```ini
CAPTCHA_SOLVER_API_KEY="xxx"
PARALLEL=4
# OUTPUT_DIR="/..path to dir.../output2"
# SEARCH_TERMS_FILEPATH="/..path to dir.../sample_data.csv"
# PROXY=["https://13.34.23.23:90", "https://13.34.23.23:9000"]
```


## Usage
Run the script with the desired argument:
```sh
python main.py --name vesselfinder --terms "EVER EAGLE" "INTERSEA TRAVELER" "W KITHIRA"
python main.py --name marinetraffic --terms "EVER EAGLE" "INTERSEA TRAVELER" "W KITHIRA"
```

- `vesselfinder` - Runs only the VesselFinder scraper.
- `marinetraffic` - Runs only the MarineTraffic scraper.

## Notes
- Ensure you have internet access to fetch data.
- Logs will indicate where the scraped data is saved.

## License
This project is for personal or educational use. Modify and use as needed!