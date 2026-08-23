

import os
import requests

os.makedirs("data/raw", exist_ok=True)
os.makedirs("data/weather", exist_ok=True)

# 1. Download NYC TLC Yellow Taxi Data (2022-2023 Parquet files)
years = [2022, 2023]
months = [f"{m:02d}" for m in range(1, 13)]

print(" == Starting NYC TLC Data Download == ")
for year in years:
    for month in months:
        url = f"https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_{year}-{month}.parquet"
        file_path = f"data/raw/yellow_{year}_{month}.parquet"
        
        if not os.path.exists(file_path):
            print(f"Downloading: {file_path}")
            res = requests.get(url, stream=True)
            if res.status_code == 200:
                with open(file_path, "wb") as f:
                    for chunk in res.iter_content(chunk_size=1024 * 1024):
                        f.write(chunk)
            else:
                print(f"Failed to download: {url}")

# 2. Download NYC Hourly Weather (Open-Meteo Archive API)
weather_file = "data/weather/nyc_hourly_weather.csv"
if not os.path.exists(weather_file):
    print(" == Downloading NYC Historical Weather Data == ")
    weather_url = (
        "https://archive-api.open-meteo.com/v1/archive?"
        "latitude=40.7128&longitude=-74.0060&"
        "start_date=2022-01-01&end_date=2023-12-31&"
        "hourly=temperature_2m,precipitation,windspeed_10m&"
        "format=csv"
    )
    res = requests.get(weather_url)
    if res.status_code == 200:
        with open(weather_file, "w") as f:
            f.write(res.text)
        print("Weather data saved successfully.")

print("All downloads complete.")