import streamlit as st
import duckdb
import plotly.express as px

st.set_page_config(page_title="NYC Mobility Analytics", layout="wide")
st.title("🚖 NYC Mobility & Weather Impact Dashboard")
st.caption("Aggregated analytics over 100M+ rides processed locally via DuckDB")

con = duckdb.connect()

@st.cache_data
def load_data():
    return con.execute("""
        SELECT * FROM read_parquet('data/processed/weather_impact_summary.parquet')
    """).df()

df = load_data()

# Sidebar Controls
st.sidebar.header("Filter Options")
weather_options = df["weather_condition"].dropna().unique().tolist()
selected_weather = st.sidebar.multiselect(
    "Select Weather Conditions:",
    options=weather_options,
    default=weather_options
)

filtered_df = df[df["weather_condition"].isin(selected_weather)]

# --- Helper function to format large revenue numbers cleanly ---
def format_currency(val):
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

# Derived operational metrics
avg_speed_mph = (avg_distance / (avg_duration / 60)) if avg_duration > 0 else 0
rev_per_min = (avg_fare / avg_duration) if avg_duration > 0 else 0

# --- Row 1: High-Level Volume & Revenue ---
st.subheader("Key Performance Indicators")
r1_c1, r1_c2, r1_c3, r1_c4 = st.columns(4)

r1_c1.metric("Total Trips", f"{total_trips:,}")
r1_c2.metric("Total Revenue", format_currency(total_revenue))
r1_c3.metric("Average Fare", f"${avg_fare:.2f}")
r1_c4.metric("Avg Trip Distance", f"{avg_distance:.2f} mi")

# --- Row 2: Operational Pace & Passenger Behavior ---
r2_c1, r2_c2, r2_c3, r2_c4 = st.columns(4)

r2_c1.metric("Avg Duration", f"{avg_duration:.1f} min")
r2_c2.metric("Avg Speed", f"{avg_speed_mph:.1f} mph", help="Estimated average transit speed")
r2_c3.metric("Revenue Rate", f"${rev_per_min:.2f} / min", help="Average fare generated per minute of transit")
r2_c4.metric("Avg Tip %", f"{avg_tip:.2f}%")

st.divider()

# Charts
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Trip Duration Distribution by Weather")
    fig_hist = px.histogram(
        filtered_df,
        x="avg_duration_min",
        color="weather_condition",
        marginal="box",
        nbins=40,
        labels={"avg_duration_min": "Trip Duration (minutes)"}
    )
    st.plotly_chart(fig_hist, use_container_width=True)

with col_right:
    st.subheader("Tip Percentage vs. Fare")
    fig_scatter = px.scatter(
        filtered_df,
        x="avg_tip_pct",
        y="avg_fare",
        color="weather_condition",
        size="total_trips",
        hover_data=["pickup_zone", "trip_date"],
        labels={"avg_tip_pct": "Avg Tip (%)", "avg_fare": "Avg Fare ($)"}
    )
    st.plotly_chart(fig_scatter, use_container_width=True)