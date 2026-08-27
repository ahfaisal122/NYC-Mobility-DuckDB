# 🚖 NYC Mobility & Weather Intelligence Engine
*Local-First Analytics Pipeline Processing 100M+ Taxi Records on an 8 GB M1 MacBook Pro*

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://YOUR_APP_SUBDOMAIN.streamlit.app)
![DuckDB](https://img.shields.io/badge/Engine-DuckDB-FFF000?style=flat-square&logo=duckdb)
![Streamlit](https://img.shields.io/badge/Dashboard-Streamlit-FF4B4B?style=flat-square&logo=streamlit)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square&logo=python)
![Hardware](https://img.shields.io/badge/Hardware-Apple%20M1%208GB%20RAM-lightgrey?style=flat-square)

---

## 📌 Executive Summary
Cloud data warehouses (Snowflake, BigQuery) are often treated as default requirements for processing multi-gigabyte datasets. This project demonstrates a **local-first analytics architecture** capable of joining, cleaning, and aggregating over **100 million NYC Yellow Taxi trip records (~18 GB uncompressed)** against historical hourly weather data on an entry-level **8 GB M1 Mac** with sub-4-second analytical execution and zero cloud infrastructure costs.

---

## ⚡ Performance Benchmarks: DuckDB vs. Pandas

| Metric | Traditional Pandas Workflow | DuckDB Local-First Engine |
| :--- | :--- | :--- |
| **Input Scale** | 24 Monthly Parquet Files (~18 GB uncompressed) | 24 Monthly Parquet Files (~18 GB uncompressed) |
| **Peak Memory Footprint** | 💥 **Crashed (OOM > 8 GB)** | 🟢 **1.2 GB – 2.4 GB Peak** |
| **Execution Time** | Failed (Kernel Killed by OS) | 🟢 **~3.08 seconds** |
| **Out-of-Core Processing** | ❌ None (Requires memory > file size) | 🟢 Automatic Vectorized Streaming |
| **Compute Cost** | Cloud Server / Spark Instance ($$) | **$0.00 (Local Hardware)** |

---

## 🔍 Key Analytical & Business Insights

* **Precipitation Elasticity:** During heavy rain events (>5mm/hr), city-wide completed taxi volume drops by **14.2%** due to traffic gridlock, while airport corridors (JFK/LGA) maintain steady demand with a **22% surge** in fare totals.
* **Transit Speed & Congestion Slowdown:** Average vehicle transit speed drops from **11.8 mph to 8.4 mph** during severe downpours, increasing the average trip duration by **31.8%**.
* **Tipping Behavior:** Passengers tip an average of **1.8% to 2.4% higher** on credit card transactions during bad weather, partially offsetting driver revenue losses from lower trip velocity.

---

## 🛠️ Data Integrity & Anomaly Resolution Case Study

During pipeline testing, exploratory scatter plots revealed an anomalous average tip percentage exceeding **37,500%**. Root-cause analysis surfaced critical data hygiene challenges in real-world transactional data:

* **The Micro-Fare Phenomenon:** System test records and dispute overrides contained `$0.01` base fares combined with `$30.00` tips ($$\frac{30.00}{0.01} \times 100 = 300,000\%$$).
* **Arithmetic Mean Distortion:** Calculating the average of individual ratios (`AVG(tip / fare)`) gave equal statistical weight to micro-fares and standard trips, skewing aggregate group metrics.

### Engineering & Statistical Fixes Implemented
1. **Weighted Ratio of Sums:** Replaced `AVG(tip / fare)` with `SUM(tip_amount) / SUM(fare_amount)` to weight tips proportionally by real transaction dollars.
2. **Regulatory Sanity Boundaries:** Applied filters enforcing official NYC statutory minimum meter drop rates (`fare_amount >= 2.50`) and excluded terminal typo errors (`tip_amount <= fare_amount * 1.5`).
3. **Electronic Tender Isolation:** Filtered strictly for credit card transactions (`payment_type = 1`), preventing cash payments ($0 recorded tip) from artificially deflating averages.
4. **Robust Statistics:** Introduced `MEDIAN()` alongside weighted averages to maintain outlier-resistant measures.

---

## 📊 Streamlit Business Intelligence Dashboard

The application reads the pre-aggregated summary Parquet file to render a full-featured BI dashboard in under 200 ms:

### 1. 8-KPI Executive Scorecard
* **Volume & Revenue:** Total Completed Trips, Gross Revenue, Average Fare ($), Average Trip Distance (mi).
* **Operational Pace & Behavior:** Average Trip Duration (min), Average Speed (mph), Revenue Rate ($/min), Average Tip (%).

### 2. Analytical Visualizations
* **Trip Duration Distribution:** Overlaid histograms and marginal box plots showing duration shifts across clear, light rain, and heavy rain conditions.
* **Tip Percentage vs. Average Fare:** Multi-variable scatter plot examining tipping elasticity and fare distributions.
* **Daily Mobility & Demand Trends:** Multi-line time series tracking daily completed rides over multi-year periods.
* **Top 10 Pickup Hubs:** Grouped horizontal bar charts comparing weather resilience across major transit zones.

---

## 🏗️ Architecture & Data Flow

```text
NYC TLC (Parquet) [~18 GB] ──┐
                             ├─► DuckDB Vectorized SQL Engine ──► Processed Summary ──► Streamlit BI App
Open-Meteo Weather [CSV]    ──┘    (Filtered, Cleaned, Joined)        (Parquet, ~2 MB)