import streamlit as st
import duckdb
import pandas as pd
import plotly.express as px

# Page configuration
st.set_page_config(
    page_title="NYC Mobility Analytics",
    page_icon="🚖",
    layout="wide"
)

st.title("🚖 NYC Mobility & Weather Intelligence Dashboard")
st.caption("Out-of-Core Local Analytics over 100M+ rides powered by DuckDB & Streamlit")

# Ingestion via DuckDB with caching
con = duckdb.connect()

@st.cache_data
def load_data():
    query = """
        SELECT 
            pickup_zone,
            trip_date::DATE AS trip_date,
            weather_condition,
            total_trips,
            avg_distance,
            avg_duration_min,
            avg_fare,
            avg_tip_pct,
            median_tip_pct,
            total_revenue
        FROM read_parquet('data/processed/weather_impact_summary.parquet')
    """
    return con.execute(query).df()

df = load_data()

# --- Sidebar Controls ---
st.sidebar.header("Filter Options")
weather_options = df["weather_condition"].dropna().unique().tolist()
selected_weather = st.sidebar.multiselect(
    "Select Weather Conditions:",
    options=weather_options,
    default=weather_options
)

# Filter application
filtered_df = df[df["weather_condition"].isin(selected_weather)]

# Guard clause for empty selections
if filtered_df.empty:
    st.warning("⚠️ Please select at least one weather condition from the sidebar to display metrics.")
    st.stop()

# Currency formatting helper
def format_currency(val):
    if pd.isna(val) or val == 0:
        return "$0.00"
    if val >= 1e9:
        return f"${val / 1e9:.2f}B"
    elif val >= 1e6:
        return f"${val / 1e6:.2f}M"
    return f"${val:,.2f}"

# --- KPI Calculations ---
total_trips = filtered_df["total_trips"].sum()
total_revenue = filtered_df["total_revenue"].sum()
avg_fare = filtered_df["avg_fare"].mean()
avg_distance = filtered_df["avg_distance"].mean()
avg_duration = filtered_df["avg_duration_min"].mean()
avg_tip = filtered_df["avg_tip_pct"].mean()

# Derived operational rates
avg_speed_mph = (avg_distance / (avg_duration / 60)) if avg_duration > 0 else 0
rev_per_min = (avg_fare / avg_duration) if avg_duration > 0 else 0

# --- KPI Metric Cards (2x4 Grid) ---
st.subheader("Key Performance Indicators")

# Row 1: Volume & Revenue
r1_c1, r1_c2, r1_c3, r1_c4 = st.columns(4)
r1_c1.metric("Total Trips", f"{total_trips:,}")
r1_c2.metric("Gross Revenue", format_currency(total_revenue))
r1_c3.metric("Average Fare", f"${avg_fare:.2f}")
r1_c4.metric("Avg Trip Distance", f"{avg_distance:.2f} mi")

# Row 2: Operational Pace & Rider Behavior
r2_c1, r2_c2, r2_c3, r2_c4 = st.columns(4)
r2_c1.metric("Avg Duration", f"{avg_duration:.1f} min")
r2_c2.metric("Avg Speed", f"{avg_speed_mph:.1f} mph", help="Estimated average transit speed")
r2_c3.metric("Revenue Rate", f"${rev_per_min:.2f} / min", help="Average fare generated per minute of transit")
r2_c4.metric("Avg Tip %", f"{avg_tip:.2f}%")

st.divider()

# --- Visualizations Row 1 ---
row1_left, row1_right = st.columns(2)

with row1_left:
    st.subheader("Trip Duration Distribution by Weather")
    fig_hist = px.histogram(
        filtered_df,
        x="avg_duration_min",
        color="weather_condition",
        marginal="box",
        nbins=40,
        labels={"avg_duration_min": "Trip Duration (minutes)", "weather_condition": "Weather"}
    )
    fig_hist.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    st.plotly_chart(fig_hist, use_container_width=True)

with row1_right:
    st.subheader("Tip Percentage vs. Average Fare")
    fig_scatter = px.scatter(
        filtered_df,
        x="avg_tip_pct",
        y="avg_fare",
        color="weather_condition",
        size="total_trips",
        hover_data=["pickup_zone", "trip_date"],
        labels={"avg_tip_pct": "Avg Tip (%)", "avg_fare": "Avg Fare ($)", "weather_condition": "Weather"}
    )
    fig_scatter.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    st.plotly_chart(fig_scatter, use_container_width=True)

st.divider()

# --- Visualizations Row 2 ---
row2_left, row2_right = st.columns(2)

with row2_left:
    st.subheader("Daily Mobility & Demand Trends")
    
    # 1. Filter out erroneous outlier years (keep only 2021 to 2025)
    trend_data = filtered_df[
        (pd.to_datetime(filtered_df["trip_date"]) >= "2021-01-01") & 
        (pd.to_datetime(filtered_df["trip_date"]) <= "2025-12-31")
    ]
    
    # 2. Aggregate daily trips
    daily_trend = (
        trend_data.groupby(["trip_date", "weather_condition"])["total_trips"]
        .sum()
        .reset_index()
    )
    
    # 3. Build line chart
    fig_line = px.line(
        daily_trend,
        x="trip_date",
        y="total_trips",
        color="weather_condition",
        labels={"trip_date": "Date", "total_trips": "Completed Rides", "weather_condition": "Weather"}
    )
    
    # 4. Set explicit X-axis display bounds and horizontal legend
    fig_line.update_layout(
        xaxis_range=["2021-01-01", "2025-12-31"],
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig_line, use_container_width=True)

with row2_right:
    st.subheader("Top 10 Pickup Hubs by Volume")
    top_10_zones = (
        filtered_df.groupby("pickup_zone")["total_trips"]
        .sum()
        .nlargest(10)
        .index.tolist()
    )
    zone_df = filtered_df[filtered_df["pickup_zone"].isin(top_10_zones)]
    zone_summary = (
        zone_df.groupby(["pickup_zone", "weather_condition"])["total_trips"]
        .sum()
        .reset_index()
    )
    fig_bar = px.bar(
        zone_summary,
        x="total_trips",
        y="pickup_zone",
        color="weather_condition",
        orientation="h",
        barmode="group",
        labels={"total_trips": "Total Rides", "pickup_zone": "Zone ID", "weather_condition": "Weather"}
    )
    fig_bar.update_layout(
        yaxis={"type": "category", "categoryorder": "total ascending"},
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig_bar, use_container_width=True)