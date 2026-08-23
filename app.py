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

# KPI Cards
kpi1, kpi2, kpi3, kpi4 = st.columns(4)
kpi1.metric("Total Trips", f"{filtered_df['total_trips'].sum():,}")
kpi2.metric("Total Revenue", f"${filtered_df['total_revenue'].sum():,.2f}")
kpi3.metric("Avg Tip %", f"{filtered_df['avg_tip_pct'].mean():.2f}%")
kpi4.metric("Avg Duration", f"{filtered_df['avg_duration_min'].mean():.1f} min")

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