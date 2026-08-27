import duckdb
import time

print("Connecting to DuckDB engine...")
con = duckdb.connect(database="mobility.duckdb")

# Safety configurations tailored for an 8 GB M1 Mac
con.execute("SET memory_limit = '4GB';")
con.execute("SET threads TO 6;")

print("Executing SQL transformation over ~18 GB of data...")
start_time = time.time()

# 1. Parse weather data
con.execute("""
    CREATE OR REPLACE TABLE weather AS 
    SELECT 
        "time"::TIMESTAMP AS weather_time,
        "temperature_2m (°C)" AS temp_c,
        "precipitation (mm)" AS rain_mm,
        "windspeed_10m (km/h)" AS wind_speed
    FROM read_csv_auto('data/weather/nyc_hourly_weather.csv', skip=3);
""")

# 2. Process taxi trips applying the 5 data-cleaning & weighting rules
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
            payment_type,
            date_diff('minute', tpep_pickup_datetime, tpep_dropoff_datetime) AS trip_duration_min
        FROM read_parquet('data/raw/*.parquet')
        WHERE trip_distance > 0 
          AND fare_amount >= 2.50              -- Rule 2: Exclude corrupt & sub-minimum fares
          AND tip_amount >= 0                  -- Rule 2: Exclude negative chargebacks
          AND tip_amount <= fare_amount * 1.5  -- Rule 3: Cap input/terminal typos
          AND trip_duration_min BETWEEN 1 AND 180
          AND payment_type = 1                 -- Rule 4: Credit card transactions only
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
        -- Rule 1: Ratio of sums (weighted average tip %)
        ROUND((SUM(t.tip_amount) / NULLIF(SUM(t.fare_amount), 0)) * 100, 2) AS avg_tip_pct,
        -- Rule 5: Median tip % for non-parametric distribution
        ROUND(MEDIAN(t.tip_amount / t.fare_amount) * 100, 2) AS median_tip_pct,
        ROUND(SUM(t.total_amount), 2) AS total_revenue
    FROM clean_trips t
    LEFT JOIN weather w 
        ON t.pickup_hour = w.weather_time
    GROUP BY 1, 2, 3;
""")

# 3. Export cleaned summary to Parquet for instant dashboard loading
con.execute("""
    COPY (SELECT * FROM aggregated_metrics) 
    TO 'data/processed/weather_impact_summary.parquet' (FORMAT PARQUET);
""")

duration = round(time.time() - start_time, 2)
print(f"Pipeline executed successfully in {duration} seconds!")