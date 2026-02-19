import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import os
from st_aggrid import AgGrid, GridOptionsBuilder

# =========================
# CONFIG
# =========================

LOCAL_TZ = "Europe/Madrid"

st.set_page_config(page_title="Last.fm Stats", layout="wide")

DATA_PATH = "data/scrobbles.csv"
DURATIONS_PATH = "data/durations.csv"

# =========================
# LOAD DATA
# =========================

@st.cache_data
def load_data():
    scrobbles = pd.read_csv(DATA_PATH)

    # Convertir timestamp a hora local correcta
    scrobbles["datetime"] = (
        pd.to_datetime(scrobbles["uts"], unit="s", utc=True)
        .dt.tz_convert(LOCAL_TZ)
    )

    if os.path.exists(DURATIONS_PATH):
        durations = pd.read_csv(DURATIONS_PATH, sep=";", engine="python")
        durations["duration"] = pd.to_numeric(
            durations.get("duration", pd.Series()),
            errors="coerce"
        )
    else:
        durations = pd.DataFrame(columns=["artist", "track", "duration"])

    df = scrobbles.merge(durations, on=["artist", "track"], how="left")
    return df


df = load_data()

# =========================
# TIME FILTER (CENTRALIZADO)
# =========================

def apply_time_filter(df, filter_name):
    if filter_name == "Morning":
        return df[(df["datetime"].dt.hour >= 6) & (df["datetime"].dt.hour < 12)]
    elif filter_name == "Afternoon":
        return df[(df["datetime"].dt.hour >= 12) & (df["datetime"].dt.hour < 21)]
    elif filter_name == "Night":
        return df[(df["datetime"].dt.hour >= 21) | (df["datetime"].dt.hour < 6)]
    return df


# =========================
# SUMMARY FUNCTIONS
# =========================

def safe_top_by_minutes(df, col):
    if col not in df.columns or df.empty:
        return None
    summary = df.groupby(col)["duration"].sum()
    if summary.empty:
        return None
    return summary.idxmax()


def get_listening_summary(df, period="month"):
    df = df.copy()
    if df.empty:
        return pd.DataFrame()

    if period == "week":
        df["period"] = df["datetime"].dt.to_period("W").apply(lambda r: r.start_time.date())
    elif period == "day":
        df["period"] = df["datetime"].dt.floor("D").dt.date
    elif period == "month":
        df["period"] = df["datetime"].dt.to_period("M").apply(lambda r: r.start_time.date())
    elif period == "year":
        df["period"] = df["datetime"].dt.to_period("Y").apply(lambda r: r.start_time.date())

    rows = []

    for period_val, group in df.groupby("period"):
        rows.append({
            "period": str(period_val),
            "total_minutes": round(group["duration"].sum() / 60, 2),
            "top_artist": safe_top_by_minutes(group, "artist"),
            "top_track": safe_top_by_minutes(group, "track"),
            "top_album": safe_top_by_minutes(group, "album") if "album" in group.columns else None,
            "n_scrobbles": len(group)
        })

    return pd.DataFrame(rows).sort_values("period")


def summarize(df, col):
    return (
        df.groupby(col)
        .agg(
            total_minutes=("duration", lambda x: round(x.sum() / 60, 2)),
            n_scrobbles=(col, "count")
        )
        .sort_values("total_minutes", ascending=False)
        .reset_index()
    )


# =========================
# AGGRID DISPLAY
# =========================

def display_aggrid(df_summary):
    if df_summary.empty:
        st.write("No data")
        return

    for c in df_summary.select_dtypes(include=["datetime"]):
        df_summary[c] = df_summary[c].dt.strftime("%Y-%m-%d")

    for c in df_summary.select_dtypes(include=["float", "int"]):
        df_summary[c] = df_summary[c].round(2)

    height = max(200, len(df_summary) * 35)

    gb = GridOptionsBuilder.from_dataframe(df_summary)
    gb.configure_default_column(filter=True, sortable=True, resizable=True)

    for c in df_summary.select_dtypes(include=["number"]).columns:
        gb.configure_column(c, filter="agNumberColumnFilter")

    for c in df_summary.select_dtypes(include=["object"]).columns:
        gb.configure_column(c, filter="agTextColumnFilter")

    AgGrid(
        df_summary,
        gridOptions=gb.build(),
        fit_columns_on_grid_load=True,
        height=height
    )


# =========================
# TIME PATTERNS
# =========================

def time_of_hour(df, start_date, end_date, period_filter):
    df_filtered = df[(df["datetime"] >= start_date) & (df["datetime"] <= end_date)]
    df_filtered = apply_time_filter(df_filtered, period_filter)

    df_filtered["hour"] = df_filtered["datetime"].dt.hour
    summary = df_filtered.groupby("hour")["duration"].sum() / 60
    summary = summary.round(2).reset_index()

    fig = px.bar(
        summary,
        x="hour",
        y="duration",
        labels={"duration": "Minutes", "hour": "Hour"},
        title=f"Listening Time by Hour ({period_filter})"
    )
    st.plotly_chart(fig, use_container_width=True)


def time_of_weekday(df, start_date, end_date, period_filter):
    df_filtered = df[(df["datetime"] >= start_date) & (df["datetime"] <= end_date)]
    df_filtered = apply_time_filter(df_filtered, period_filter)

    df_filtered["weekday"] = df_filtered["datetime"].dt.day_name()
    order = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]

    summary = df_filtered.groupby("weekday")["duration"].sum() / 60
    summary = summary.round(2).reindex(order).reset_index()

    fig = px.bar(
        summary,
        x="weekday",
        y="duration",
        labels={"duration": "Minutes", "weekday": "Weekday"},
        title=f"Listening Time by Weekday ({period_filter})"
    )
    st.plotly_chart(fig, use_container_width=True)


# =========================
# UI
# =========================

st.title("🎧 Last.fm Advanced Stats")

tab1, tab2, tab3 = st.tabs([
    "📊 Listening Summary",
    "📋 Full Data Viewer",
    "🕒 Time Patterns"
])

# =========================
# TAB 1
# =========================

with tab1:
    period = st.selectbox("Select period", ["day","week","month","year"])
    time_filter = st.selectbox("Filter by time of day", ["All","Morning","Afternoon","Night"])

    start_date = pd.to_datetime(st.date_input("Start Date", datetime(2025,1,1))).tz_localize(LOCAL_TZ)
    end_date   = pd.to_datetime(st.date_input("End Date", datetime.now())).tz_localize(LOCAL_TZ)

    df_filtered = df[(df["datetime"] >= start_date) & (df["datetime"] <= end_date)]
    df_filtered = apply_time_filter(df_filtered, time_filter)

    summary = get_listening_summary(df_filtered, period)
    display_aggrid(summary.tail(10))

    fig = px.bar(
        summary,
        x="period",
        y="total_minutes",
        labels={"total_minutes":"Minutes","period":"Date"},
        title="Total Listening Time Over Time"
    )
    st.plotly_chart(fig, use_container_width=True)


# =========================
# TAB 2
# =========================

with tab2:
    st.subheader("Tracks / Artists / Albums")

    start_fd = pd.to_datetime(
        st.date_input("Start Date", datetime(2025,1,1), key="fd_start")
    ).tz_localize(LOCAL_TZ)

    end_fd = pd.to_datetime(
        st.date_input("End Date", datetime.now(), key="fd_end")
    ).tz_localize(LOCAL_TZ)

    time_filter_fd = st.selectbox(
        "Filter by time of day",
        ["All","Morning","Afternoon","Night"],
        key="fd_time"
    )

    # 🔢 NUEVO: número de filas a mostrar
    top_n = st.selectbox(
        "Number of rows to display",
        [10, 25, 50, 100, 200],
        index=1  # default 25
    )

    df_fd = df[(df["datetime"] >= start_fd) & (df["datetime"] <= end_fd)]
    df_fd = apply_time_filter(df_fd, time_filter_fd)

    # TRACKS
    st.markdown("### 🎵 Tracks")
    tracks_summary = summarize(df_fd, "track").head(top_n)
    display_aggrid(tracks_summary)

    # ARTISTS
    st.markdown("### 🎤 Artists")
    artists_summary = summarize(df_fd, "artist").head(top_n)
    display_aggrid(artists_summary)

    # ALBUMS
    if "album" in df_fd.columns:
        st.markdown("### 💿 Albums")
        albums_summary = summarize(df_fd, "album").head(top_n)
        display_aggrid(albums_summary)



# =========================
# TAB 3
# =========================

with tab3:
    start_tp = pd.to_datetime(st.date_input("Start Date", datetime(2025,1,1), key="tp_start")).tz_localize(LOCAL_TZ)
    end_tp   = pd.to_datetime(st.date_input("End Date", datetime.now(), key="tp_end")).tz_localize(LOCAL_TZ)

    period_filter_tp = st.selectbox("Filter by time of day", ["All","Morning","Afternoon","Night"], key="tp_time")

    time_of_hour(df, start_tp, end_tp, period_filter_tp)
    time_of_weekday(df, start_tp, end_tp, period_filter_tp)
