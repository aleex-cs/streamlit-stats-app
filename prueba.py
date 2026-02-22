import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import os
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode
import csv


# =========================
# CONFIG
# =========================

LOCAL_TZ = "Europe/Madrid"

DATA_PATH = "data/aleex_cs.csv"
DURATIONS_PATH = "data/musica.csv"

# --- Cargar scrobbles ---
scrobbles = pd.read_csv(DATA_PATH)

# convertir timestamp a datetime local
scrobbles["datetime"] = (
    pd.to_datetime(scrobbles["uts"], unit="s", utc=True)
    .dt.tz_convert(LOCAL_TZ)
)

# limpiar artistas: eliminar sufijos tipo " - ..."
scrobbles["artist"] = scrobbles["artist"].str.replace(r" - .*", "", regex=True)

# equivalencias de artistas
equivalencias = pd.DataFrame({
    "original": [
        "Smash (ESP)", "Smash", "Jim Morrison", "Robe.",
        "I Nomadi", "Godspeed You Black Emperor!", "Fito Y Fitipaldis"
    ],
    "canonico": [
        "Smash", "Smash", "The Doors", "Robe",
        "Nomadi", "Godspeed You! Black Emperor", "Fito & Fitipaldis"
    ]
})

scrobbles = scrobbles.merge(
    equivalencias,
    left_on="artist",
    right_on="original",
    how="left"
)

scrobbles["artist"] = scrobbles["canonico"].fillna(scrobbles["artist"])
scrobbles = scrobbles.drop(columns=["original", "canonico"])

# --- Cargar duraciones ---
if os.path.exists(DURATIONS_PATH):
    durations = pd.read_csv(
        DURATIONS_PATH,
        sep=";",
        engine="python",
        quoting=csv.QUOTE_NONE
    )
    durations = durations.rename(columns={
        "Artista": "artist",
        "Título": "track",
        "Duración(s)": "duration"
    })
    durations["duration"] = pd.to_numeric(
        durations.get("duration", pd.Series(dtype=float)),
        errors="coerce"
    ) / 100  # ajustar si la duración viene en centésimas de segundo
else:
    durations = pd.DataFrame(columns=["artist", "track", "duration"])

# --- Normalización de cadenas para merge ---
def normalize_str(s):
    if pd.isna(s):
        return ""
    return s.strip().lower().replace("’", "'")

scrobbles["artist_norm"] = scrobbles["artist"].apply(normalize_str)
scrobbles["track_norm"] = scrobbles["track"].apply(normalize_str)
durations["artist_norm"] = durations["artist"].apply(normalize_str)
durations["track_norm"] = durations["track"].apply(normalize_str)

durations = durations.drop_duplicates(subset=["artist_norm","track_norm"])

# --- Merge de duraciones ---
df = scrobbles.merge(
    durations[["artist_norm", "track_norm", "duration"]],
    on=["artist_norm", "track_norm"],
    how="left"
)

# eliminar columnas auxiliares de normalización
df = df.drop(columns=["artist_norm", "track_norm"])


df["datetime"] = pd.to_datetime(df["datetime"])

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
        df["Period"] = df["datetime"].dt.to_period("W").apply(lambda r: r.start_time.tz_convert(LOCAL_TZ).date())
    elif period == "day":
        df["Period"] = df["datetime"].dt.tz_convert(LOCAL_TZ).dt.date
    elif period == "month":
        df["Period"] = df["datetime"].dt.tz_convert(LOCAL_TZ).dt.to_period("M").apply(lambda r: r.start_time.date())
    elif period == "year":
        df["Period"] = df["datetime"].dt.tz_convert(LOCAL_TZ).dt.to_period("Y").apply(lambda r: r.start_time.date())

    rows = []
    for period_val, group in df.groupby("Period"):
        rows.append({
            "Period": str(period_val),
            "Minutes": round(group["duration"].sum() / 60, 2),
            "Top Artist": safe_top_by_minutes(group, "artist"),
            "Top Track": safe_top_by_minutes(group, "track"),
            "Top Album": safe_top_by_minutes(group, "album") if "album" in group.columns else None,
            "Plays": len(group)
        })

    return pd.DataFrame(rows).sort_values("Period")

print(get_listening_summary(df,period="day"))