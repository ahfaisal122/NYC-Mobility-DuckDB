# 🚖 NYC Mobility & Weather Intelligence Engine
*Out-of-Core Analytical Pipeline Processing 100M+ Taxi Rides on Consumer Hardware (8 GB RAM)*

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square&logo=python)
![DuckDB](https://img.shields.io/badge/Engine-DuckDB-FFF000?style=flat-square&logo=duckdb)
![Streamlit](https://img.shields.io/badge/BI-Streamlit-FF4B4B?style=flat-square&logo=streamlit)
![Platform](https://img.shields.io/badge/Hardware-Apple%20M1%208GB-lightgrey?style=flat-square)

---

## 📌 Executive Summary
Cloud warehouses (Snowflake, BigQuery) are often treated as default requirements for multi-gigabyte datasets. This project demonstrates a **local-first analytics architecture** capable of cleaning, joining, and aggregating over **100 million NYC taxi records (~18 GB uncompressed)** against historical hourly weather data on a standard **8 GB M1 MacBook Pro** without cloud costs or memory crashes.

---

## ⚡ Performance Benchmarks: DuckDB vs. Pandas

| Metric | Traditional Pandas Workflow | DuckDB Local-First Engine |
| :--- | :--- | :--- |
| **Dataset Scale** | 24 Monthly Parquet Files (~18 GB uncompressed) | 24 Monthly Parquet Files (~18 GB uncompressed) |
| **Peak RAM Usage** | 💥 **Crashed (OOM > 8 GB)** | 🟢 **1.4 GB – 2.8 GB** |
| **Execution Time** | N/A (Process Killed by OS) | 🟢 **~32 seconds** |
| **Spill-to-Disk Handling**| ❌ None (Requires RAM > Data Size) | 🟢 Automatic Vectorized Streaming |
| **Compute Cost** | Cloud Server Required ($$) | **$0.00 (Local Execution)** |

---

## 🔍 Key Analytical & Business Findings

* **Weather Surge Demand Elasticity:** During heavy rain (>5mm/hr), overall completed taxi volume decreases by **14.2%** across outer boroughs due to traffic gridlock, while airport corridors (JFK/LGA) experience a **22% spike in demand**.
* **Trip Duration & Congestion:** Average Manhattan transit times increase by **31.8%** during rain events, shifting the median trip duration from 12.4 minutes to 16.3 minutes.
* **Tipping Behavior:** Passengers tip an average of **1.8% to 2.4% higher** during severe precipitation on credit transactions, partially offsetting lost driver throughput caused by congestion.

---

## 🛠️ Data Integrity & Edge Case Investigation

During exploratory pipeline runs, initial scatter plots showed anomalous average tip percentages reaching **37,500%**. Root-cause investigation revealed:

* **The Micro-Fare Glitch:** Terminal testing or payment disputes generated records with a `$0.01` base fare paired with standard `$30.00` tips ($$\frac{30.00}{0.01} \times 100 = 300,000\%$$).
* **Arithmetic Mean Distortion:** Averaging individual ratios gave equal weight to micro-fares and full-price rides.

**Engineering Fix Applied:**
1. **Weighted Ratio of Sums:** Replaced `AVG(tip / fare)` with `SUM(tip_amount) / SUM(fare_amount)` to weight tips proportionally by total dollar volume.
2. **Regulatory Sanity Bounds:** Filtered records to legal NYC minimum base meter drops (`fare_amount >= 2.50`) and excluded terminal typo errors (`tip_amount <= fare_amount * 1.5`).
3. **Electronic Tender Filtering:** Restricted tip analysis to credit transactions (`payment_type = 1`), preventing cash trips ($0.00 recorded tip) from deflating metrics.

---

## 🏗️ Architecture & Data Flow

```text
NYC TLC (Parquet) [~18 GB] ──┐
                             ├─► DuckDB Vectorized SQL Engine ──► Processed Summary ──► Streamlit BI Dashboard
Open-Meteo Weather [CSV]    ──┘    (Filtered, Cleaned, Joined)        (Parquet)
