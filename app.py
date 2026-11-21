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

# --- Design tokens (light / dark follow the viewer's Streamlit theme) ---
WEATHER_ORDER = ["Clear/Dry", "Light Rain", "Heavy Rain"]

TOKENS = {
    "light": {
        "surface": "#ffffff",
        "border": "#e7e6e2",
        "grid": "#ecebe8",
        "text": "#0b0b0b",
        "text_2": "#52514e",
        "muted": "#8a8984",
        "accent": "#f2b705",
        "series": ["#2a78d6", "#eb6834", "#1baf7a"],
    },
    "dark": {
        "surface": "#1a1a19",
        "border": "#2b2b29",
        "grid": "#2a2a28",
        "text": "#f0efec",
        "text_2": "#c3c2b7",
        "muted": "#8f8e86",
        "accent": "#f2b705",
        "series": ["#3987e5", "#d95926", "#199e70"],
    },
}

mode = "dark" if st.context.theme.type == "dark" else "light"
T = TOKENS[mode]
WEATHER_COLORS = dict(zip(WEATHER_ORDER, T["series"]))

st.html(f"""
<style>
  .block-container {{ padding-top: 2.5rem; padding-bottom: 3rem; max-width: 1440px; }}
  [data-testid="stHeader"] {{ background: transparent; }}

  .hero {{ margin-bottom: 1.75rem; }}
  .hero-eyebrow {{
    display: inline-flex; align-items: center; gap: .5rem;
    padding: .3rem .75rem; border: 1px solid {T["border"]}; border-radius: 999px;
    background: {T["surface"]}; color: {T["text_2"]};
    font-size: .75rem; font-weight: 500; letter-spacing: .02em;
  }}
  .hero-eyebrow .dot {{ width: .5rem; height: .5rem; border-radius: 50%; background: {T["accent"]}; }}
  .hero h1 {{
    margin: .9rem 0 .4rem; padding: 0; color: {T["text"]};
    font-size: 2.25rem; font-weight: 700; letter-spacing: -.03em; line-height: 1.15;
  }}
  .hero p {{ margin: 0; color: {T["text_2"]}; font-size: 1rem; }}

  .section-label {{
    margin: 1.75rem 0 .75rem; color: {T["muted"]};
    font-size: .75rem; font-weight: 600; letter-spacing: .08em; text-transform: uppercase;
  }}

  .kpi-grid {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 1rem; }}
  @media (max-width: 1000px) {{ .kpi-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }} }}
  .kpi {{
    padding: 1.1rem 1.25rem; border: 1px solid {T["border"]}; border-radius: .9rem;
    background: {T["surface"]};
  }}
  .kpi-label {{ color: {T["text_2"]}; font-size: .8rem; font-weight: 500; }}
  .kpi-value {{
    margin: .35rem 0 .2rem; color: {T["text"]};
    font-size: 1.75rem; font-weight: 600; letter-spacing: -.02em; line-height: 1.2;
  }}
  .kpi-value .unit {{ margin-left: .2rem; color: {T["muted"]}; font-size: 1rem; font-weight: 500; }}
  .kpi-foot {{ color: {T["muted"]}; font-size: .75rem; }}

  [class*="st-key-card-"] {{
    padding: 1.25rem 1.25rem .5rem; border: 1px solid {T["border"]}; border-radius: .9rem;
    background: {T["surface"]};
  }}
  .card-title {{ margin: 0; color: {T["text"]}; font-size: 1rem; font-weight: 600; letter-spacing: -.01em; }}
  .card-sub {{ margin: .2rem 0 0; color: {T["muted"]}; font-size: .8rem; }}
</style>
""")

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

# --- Header ---
st.html("""
<div class="hero">
  <span class="hero-eyebrow"><span class="dot"></span>NYC Yellow Taxi · 2022–2023</span>
  <h1>Mobility &amp; Weather Intelligence</h1>
  <p>Out-of-Core Local Analytics over 78M rides powered by DuckDB &amp; Streamlit</p>
</div>
""")

# --- Filter Controls ---
weather_options = [w for w in WEATHER_ORDER if w in set(df["weather_condition"].dropna())]
selected_weather = st.pills(
    "Weather conditions",
    options=weather_options,
    selection_mode="multi",
    default=weather_options,
)

# Filter application
filtered_df = df[df["weather_condition"].isin(selected_weather)]

# Guard clause for empty selections
if filtered_df.empty:
    st.warning("Select at least one weather condition above to display metrics.", icon=":material/filter_alt:")
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

# Each row is a (zone, day, weather) group average; weight by trip count for per-trip figures.
trips = filtered_df["total_trips"]
fare_sum = (filtered_df["avg_fare"] * trips).sum()
avg_fare = fare_sum / total_trips
avg_distance = (filtered_df["avg_distance"] * trips).sum() / total_trips
avg_duration = (filtered_df["avg_duration_min"] * trips).sum() / total_trips
# avg_tip_pct is a ratio of sums (tips / fares), so weight it by fare dollars.
avg_tip = (filtered_df["avg_tip_pct"] * filtered_df["avg_fare"] * trips).sum() / fare_sum

# Derived operational rates
avg_speed_mph = (avg_distance / (avg_duration / 60)) if avg_duration > 0 else 0
rev_per_min = (avg_fare / avg_duration) if avg_duration > 0 else 0

# --- KPI Cards (2x4 Grid) ---
def kpi_row(title, cards):
    items = "".join(
        f'<div class="kpi"><div class="kpi-label">{label}</div>'
        f'<div class="kpi-value">{value}</div>'
        f'<div class="kpi-foot">{foot}</div></div>'
        for label, value, foot in cards
    )
    st.html(f'<div class="section-label">{title}</div><div class="kpi-grid">{items}</div>')

def unit(text):
    return f'<span class="unit">{text}</span>'

kpi_row("Volume & revenue", [
    ("Total Trips", f"{total_trips:,}", "Completed trips"),
    ("Gross Revenue", format_currency(total_revenue), "Fares, tips and surcharges"),
    ("Average Fare", f"${avg_fare:.2f}", "Per trip, before tips"),
    ("Avg Trip Distance", f"{avg_distance:.2f}{unit('mi')}", "Per trip"),
])

kpi_row("Pace & rider behaviour", [
    ("Avg Duration", f"{avg_duration:.1f}{unit('min')}", "Pickup to drop-off"),
    ("Avg Speed", f"{avg_speed_mph:.1f}{unit('mph')}", "Estimated average transit speed"),
    ("Revenue Rate", f"${rev_per_min:.2f}{unit('/ min')}", "Average fare generated per minute of transit"),
    ("Avg Tip %", f"{avg_tip:.2f}%", "Tips as a share of fares"),
])

# --- Chart styling ---
def style_figure(fig, height=380):
    axis = dict(
        automargin=True, gridcolor=T["grid"], linecolor=T["grid"], zeroline=False,
        tickfont=dict(color=T["muted"], size=11), title_font=dict(color=T["text_2"], size=12), title_standoff=12,
    )
    fig.update_layout(
        height=height,
        margin=dict(l=0, r=8, t=8, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color=T["text_2"], size=12),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
            title_text="", font=dict(color=T["text_2"], size=12),
        ),
        hoverlabel=dict(
            bgcolor=T["surface"], bordercolor=T["border"],
            font=dict(family="Inter, sans-serif", color=T["text"], size=12),
        ),
        barcornerradius=4,
    )
    fig.update_xaxes(**axis)
    fig.update_yaxes(**axis)
    return fig

def chart_card(key, title, subtitle, fig):
    with st.container(key=f"card-{key}"):
        st.html(f'<p class="card-title">{title}</p><p class="card-sub">{subtitle}</p>')
        st.plotly_chart(style_figure(fig), theme=None)

common = dict(
    color="weather_condition",
    color_discrete_map=WEATHER_COLORS,
    category_orders={"weather_condition": WEATHER_ORDER},
)

st.html('<div class="section-label">Weather impact</div>')

# --- Visualizations Row 1 ---
row1_left, row1_right = st.columns(2, gap="medium")

with row1_left:
    fig_hist = px.histogram(
        filtered_df,
        x="avg_duration_min",
        marginal="box",
        nbins=40,
        labels={"avg_duration_min": "Trip Duration (minutes)", "weather_condition": "Weather"},
        **common,
    )
    fig_hist.update_traces(marker_line_color=T["surface"], marker_line_width=1, selector=dict(type="histogram"))
    fig_hist.update_layout(bargap=0.08, yaxis_title="Zone-days")
    chart_card("duration", "Trip Duration Distribution by Weather",
               "Average trip duration per zone and day", fig_hist)

with row1_right:
    fig_scatter = px.scatter(
        filtered_df,
        x="avg_tip_pct",
        y="avg_fare",
        size="total_trips",
        size_max=18,
        opacity=0.7,
        hover_data={"pickup_zone": True, "trip_date": "|%b %d, %Y", "total_trips": ":,"},
        labels={"avg_tip_pct": "Avg Tip (%)", "avg_fare": "Avg Fare ($)", "weather_condition": "Weather",
                "pickup_zone": "Zone", "trip_date": "Date", "total_trips": "Trips"},
        **common,
    )
    fig_scatter.update_traces(marker_line_color=T["surface"], marker_line_width=1)
    # Frame the bulk of the data; rare extreme zone-days are still reachable by zooming out.
    fig_scatter.update_xaxes(range=[0, filtered_df["avg_tip_pct"].quantile(0.995) * 1.05])
    fig_scatter.update_yaxes(range=[0, filtered_df["avg_fare"].quantile(0.995) * 1.05])
    chart_card("tips", "Tip Percentage vs. Average Fare",
               "Each point is one zone-day; size shows trip volume", fig_scatter)

# --- Visualizations Row 2 ---
row2_left, row2_right = st.columns(2, gap="medium")

with row2_left:
    # 1. Aggregate daily trips
    daily_trend = (
        filtered_df.groupby(["trip_date", "weather_condition"])["total_trips"]
        .sum()
        .reset_index()
    )

    # 2. Build line chart
    fig_line = px.line(
        daily_trend,
        x="trip_date",
        y="total_trips",
        labels={"trip_date": "Date", "total_trips": "Completed Rides", "weather_condition": "Weather"},
        **common,
    )
    fig_line.update_traces(line_width=2, hovertemplate="%{y:,} rides")
    fig_line.update_layout(hovermode="x unified", xaxis_title=None)
    chart_card("trend", "Daily Mobility & Demand Trends",
               "Completed rides per day, split by the weather at pickup", fig_line)

with row2_right:
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
        orientation="h",
        barmode="group",
        labels={"total_trips": "Total Rides", "pickup_zone": "Zone ID", "weather_condition": "Weather"},
        **common,
    )
    fig_bar.update_traces(hovertemplate="Zone %{y}<br>%{x:,} rides")
    fig_bar.update_layout(
        yaxis={"type": "category", "categoryorder": "total ascending"},
        bargap=0.2,
        bargroupgap=0.05,
    )
    chart_card("zones", "Top 10 Pickup Hubs by Volume",
               "Rides by weather at the ten busiest pickup zones", fig_bar)
