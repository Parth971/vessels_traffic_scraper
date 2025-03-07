# type: ignore
import csv
import requests

# API endpoint
API_URL = "https://scrapper.citrusfreight.com/scrape/"


# Read vessels.csv and extract vessel names
def read_vessels(filename):
    vessels = []
    with open(filename, mode="r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            vessels.append(row["vessel"])  # Extract vessel column
    return vessels


# Send synchronous API request
def fetch_vessel_data(vessel_name):
    payload = {"script": "marinetraffic", "search_term": vessel_name}
    headers = {"accept": "application/json", "Content-Type": "application/json"}

    response = requests.post(API_URL, json=payload, headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        return {"error": f"Request failed with status {response.status_code}"}


# Main function
def main():
    vessels = read_vessels(
        "/home/parth971/Downloads/vessels.csv"
    )  # Read vessel names from CSV
    for vessel in vessels:
        print(f"Fetching data for: {vessel}")
        result = fetch_vessel_data(vessel)
        print(result)  # Print API response


# Run script
if __name__ == "__main__":
    main()
