import duckdb
import time

print("Connecting to DuckDB engine...")
con = duckdb.connect(database="mobility.duckdb")

# Safety configurations tailored for an 8 GB M1 Mac
con.execute("SET memory_limit = '4GB';")
con.execute("SET threads TO 6;")

print("Executing SQL transformation over ~18 GB of data...")
start_time = time.time()

# 1. Parse weather data using exact quoted column headers from Open-Meteo
con.execute("""
    CREATE OR REPLACE TABLE weather AS 
    SELECT 
        "time"::TIMESTAMP AS weather_time,
        "temperature_2m (°C)" AS temp_c,
        "precipitation (mm)" AS rain_mm,
        "windspeed_10m (km/h)" AS wind_speed
    FROM read_csv_auto('data/weather/nyc_hourly_weather.csv', skip=3);
""")

# 2. Process ~100M taxi trips & join with hourly weather
con.execute("""
    CREATE OR REPLACE TABLE aggregated_metrics AS
    WITH clean_trips AS (
        SELECT 
            tpep_pickup_datetime AS pickup_time,
            date_trunc('hour', tpep_pickup_datetime) AS pickup_hour,
            PULocationID AS pickup_zone,
            DOLocationID AS dropoff_zone,
            trip_distance,
            fare_amount,
            tip_amount,
            total_amount,
            date_diff('minute', tpep_pickup_datetime, tpep_dropoff_datetime) AS trip_duration_min
        FROM read_parquet('data/raw/*.parquet')
        WHERE trip_distance > 0 
          AND fare_amount > 0 
          AND trip_duration_min BETWEEN 1 AND 180
    )
    SELECT 
        t.pickup_zone,
        date_trunc('day', t.pickup_hour) AS trip_date,
        CASE 
            WHEN w.rain_mm > 5.0 THEN 'Heavy Rain'
            WHEN w.rain_mm > 0.5 THEN 'Light Rain'
            ELSE 'Clear/Dry'
        END AS weather_condition,
        COUNT(*) AS total_trips,
        ROUND(AVG(t.trip_distance), 2) AS avg_distance,
        ROUND(AVG(t.trip_duration_min), 2) AS avg_duration_min,
        ROUND(AVG(t.fare_amount), 2) AS avg_fare,
        ROUND(AVG(t.tip_amount / NULLIF(t.fare_amount, 0)) * 100, 2) AS avg_tip_pct,
        ROUND(SUM(t.total_amount), 2) AS total_revenue
    FROM clean_trips t
    LEFT JOIN weather w 
        ON t.pickup_hour = w.weather_time
    GROUP BY 1, 2, 3;
""")

# 3. Export condensed output to Parquet for instant dashboard loading
con.execute("""
    COPY (SELECT * FROM aggregated_metrics) 
    TO 'data/processed/weather_impact_summary.parquet' (FORMAT PARQUET);
""")

duration = round(time.time() - start_time, 2)
print(f"Pipeline executed successfully in {duration} seconds!")