import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import os
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode
import csv
import plotly.graph_objects as go


# =========================
# CONFIG
# =========================

LOCAL_TZ = "Europe/Madrid"

st.set_page_config(page_title="Music Stats", layout="wide")

DATA_PATH = "data/aleex_cs.csv"
DURATIONS_PATH = "data/musica.csv"

# =========================
# THEME / STYLE (ALPINE-DARK REAL + REFUERZO)
# =========================

def inject_real_alpine_dark():
    """
    Inyecta variables del 'alpine-dark' oficial y fuerza los colores
    en cualquier clase de tema que use st-aggrid (streamlit/alpine).
    """
    st.markdown("""
        <style>
        /* Variables auténticas del tema azul oscuro (alpine-dark) */
        .ag-theme-alpine-dark,
        .ag-theme-alpine,
        .ag-theme-streamlit,
        .ag-theme-balham,
        .ag-theme-balham-dark,
        .ag-root-wrapper {
            --ag-foreground-color: #ffffff;
            --ag-background-color: #1b263b;             /* Azul oscuro base */
            --ag-header-background-color: #0d1b2a;      /* Azul más profundo para cabecera */
            --ag-header-foreground-color: #ffffff;

            --ag-odd-row-background-color: #1e2a3e;     /* Filas impares */
            --ag-row-hover-color: #24344d;              /* Hover fila */

            --ag-border-color: rgba(255,255,255,0.10);  /* Bordes sutiles */
            --ag-selected-row-background-color: #2b3d57;

            --ag-font-size: 14px !important;
            --ag-font-family: Inter, system-ui, -apple-system, Segoe UI, Roboto, sans-serif;

            /* Variables extra para header si están soportadas */
            --ag-header-cell-hover-background-color: #152238;
            --ag-header-row-background-color: #0d1b2a;
        }

        /* Bordes/sombra y densidad coherente */
        .ag-root-wrapper {
            border-radius: 10px !important;
            border: 1px solid rgba(255,255,255,0.12) !important;
            box-shadow: 0 1px 3px rgba(0,0,0,0.12);
        }
        .ag-header, .ag-header-row {
            height: 38px !important;
            min-height: 38px !important;
        }
        .ag-cell {
            padding: 6px 10px !important;
        }

        /* Inputs de filtro integrados */
        .ag-input-field-input, .ag-text-field-input {
            background-color: rgba(255,255,255,0.06) !important;
            color: #ffffff !important;
            border-radius: 6px !important;
            border: 1px solid rgba(255,255,255,0.12) !important;
        }

        /* Scrollbar discreto */
        .ag-body-horizontal-scroll, .ag-body-vertical-scroll {
            scrollbar-width: thin;
        }
        .ag-body-horizontal-scroll::-webkit-scrollbar,
        .ag-body-vertical-scroll::-webkit-scrollbar { height: 8px; width: 8px; }
        .ag-body-horizontal-scroll::-webkit-scrollbar-thumb,
        .ag-body-vertical-scroll::-webkit-scrollbar-thumb {
            background: rgba(128,128,128,0.35);
            border-radius: 6px;
        }
        </style>
    """, unsafe_allow_html=True)


def apply_plotly_theme():
    """Usa plotly_dark si Streamlit está en oscuro; si no, plotly_white."""
    base = (st.get_option("theme.base") or "light").lower()
    px.defaults.template = "plotly_dark" if base == "dark" else "plotly_white"
    px.defaults.color_discrete_sequence = ["#FF4B4B"]
    px.defaults.color_continuous_scale = ["#FF4B4B", "#7F2525"]
    
# Inyectar estilos y tema de gráficos al inicio
inject_real_alpine_dark()
st.markdown("""
<style>
.ag-theme-alpine-dark .ag-row,
.ag-row {
    background-color: #1b263b !important;   /* azul oscuro */
    color: white !important;
}

.ag-theme-alpine-dark .ag-row:hover,
.ag-row:hover {
    background-color: #24344d !important;    /* hover */
}

/* Para eliminar cualquier alternancia odd/even */
.ag-row-even, 
.ag-row-odd {
    background-color: #1b263b !important;
}

/* Refuerzo extra: header sin gradientes blanqueadores */
.ag-theme-alpine-dark .ag-header,
.ag-theme-alpine-dark .ag-header-viewport,
.ag-theme-alpine-dark .ag-header-row,
.ag-theme-alpine-dark .ag-header-cell,
.ag-theme-alpine-dark .ag-floating-filter {
    background-color: #0d1b2a !important;
    background-image: none !important;  /* <- clave */
    color: #ffffff !important;
}
</style>
""", unsafe_allow_html=True)
apply_plotly_theme()

# =========================
# LOAD DATA
# =========================

@st.cache_data
@st.cache_data
def load_data():
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
            "I Nomadi", "Godspeed You Black Emperor!", "Fito Y Fitipaldis",
            "Fabrizio de Andre'","Fabrizio De Andre","Fabrizio De AndrÃ©",
            "Fabrizio De André"
        ],
        "canonico": [
            "Smash", "Smash", "The Doors", "Robe",
            "Nomadi", "Godspeed You! Black Emperor", "Fito & Fitipaldis",
            "Fabrizio De Andre'", "Fabrizio De Andre'", "Fabrizio De Andre'",
            "Fabrizio De Andre'"
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

    # --- Merge de duraciones ---
    df = scrobbles.merge(
        durations[["artist_norm", "track_norm", "duration"]],
        on=["artist_norm", "track_norm"],
        how="left"
    )

    # eliminar columnas auxiliares de normalización
    df = df.drop(columns=["artist_norm", "track_norm"])

    return df
 
df = load_data()

df_full = df.copy()  # o aplicar filtros si quieres
df_full.to_csv("full_dataframe_export.csv", index=False, encoding="utf-8")

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
        df["Period"] = df["datetime"].dt.to_period("W").apply(
            lambda r: r.start_time.tz_localize(LOCAL_TZ).date()
        )
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

def summarize(df, col):
    return (
        df.groupby(col)
        .agg(
            Minutes=("duration", lambda x: round(x.sum() / 60, 2)),
            Plays=(col, "count")
        )
        .sort_values("Minutes", ascending=False)
        .reset_index()
    )

def add_share_columns(df_summary):
    """Añade Minutes% y Plays% como porcentaje (numérico, no string)."""
    df_summary = df_summary.copy()
    minutes_total = df_summary["Minutes"].sum()
    plays_total = df_summary["Plays"].sum()

    df_summary["Minutes%"] = (df_summary["Minutes"] / minutes_total * 100) if minutes_total > 0 else 0.0
    df_summary["Plays%"] = (df_summary["Plays"] / plays_total * 100) if plays_total > 0 else 0.0
    return df_summary

def longest_streak(series):
    """
    Devuelve (valor, longitud_racha) para la racha consecutiva más larga
    en una serie.
    """
    if series.empty:
        return None, 0

    best_value = None
    best_len = 0

    current_value = None
    current_len = 0

    for v in series:
        if v == current_value:
            current_len += 1
        else:
            current_value = v
            current_len = 1

        if current_len > best_len:
            best_len = current_len
            best_value = current_value

    return best_value, best_len

# =========================
# AGGRID DISPLAY
# =========================

# CSS directo de st-aggrid para forzar colores clave en el árbol interno
AGGRID_CUSTOM_CSS = {
    # Contenedor principal (fondo azul oscuro)
    ".ag-root-wrapper": {
        "background-color": "#1b263b !important",
    },
    # Header con azul más profundo (y sin gradiente)
    ".ag-header": {
        "background-color": "#0d1b2a !important",
        "background-image": "none !important",
        "color": "#ffffff !important",
        "border-bottom": "1px solid rgba(255,255,255,0.12) !important",
    },
    ".ag-header-viewport": {
        "background-color": "#0d1b2a !important",
        "background-image": "none !important",
    },
    ".ag-header-row": {
        "background-color": "#0d1b2a !important",
    },
    ".ag-header-cell": {
        "background-color": "#0d1b2a !important",
        "color": "#ffffff !important",
    },
    ".ag-floating-filter": {
        "background-color": "#0d1b2a !important",
        "color": "#ffffff !important",
    },
    # Celdas
    ".ag-center-cols-container": {
        "background-color": "#1b263b !important",
        "color": "#ffffff !important",
    },
    # Filas impares
    ".ag-row-odd": {
        "background-color": "#1e2a3e !important",
    },
    # Hover
    ".ag-row-hover": {
        "background-color": "#24344d !important",
    },
    # Bordes
    ".ag-root": {
        "border-color": "rgba(255,255,255,0.10) !important",
    },
    # Inputs de filtros
    ".ag-input-field-input": {
        "background-color": "rgba(255,255,255,0.06) !important",
        "color": "#ffffff !important",
        "border": "1px solid rgba(255,255,255,0.12) !important",
        "border-radius": "6px !important",
    },
}

def display_aggrid(df_summary, container_id: str):
    if df_summary.empty:
        st.write("No data")
        return

    df_summary = df_summary.copy()

    # Formateo de tipos
    for c in df_summary.select_dtypes(include=["datetime"]).columns:
        df_summary.loc[:, c] = df_summary[c].dt.strftime("%Y-%m-%d")

    for c in df_summary.select_dtypes(include=["float", "int"]).columns:
        df_summary.loc[:, c] = df_summary[c].round(2)

    gb = GridOptionsBuilder.from_dataframe(df_summary)
    gb.configure_default_column(filter=True, sortable=True, resizable=True)

    # Filtros por tipo y alineación
    for c in df_summary.select_dtypes(include=["number"]).columns:
        gb.configure_column(
            c,
            filter="agNumberColumnFilter",
            type=["numericColumn"],
            cellStyle={"textAlign": "right"},
        )
    for c in df_summary.select_dtypes(include=["object"]).columns:
        gb.configure_column(c, filter="agTextColumnFilter")

    # ---- Formateo de porcentajes si existen ----
    if "Minutes%" in df_summary.columns:
        gb.configure_column(
            "Minutes%",
            filter="agNumberColumnFilter",
            type=["numericColumn"],
            cellStyle={"textAlign": "right"},
            valueFormatter=JsCode("function(params){ return (params.value==null)?'':(Number(params.value).toFixed(2)+'%'); }"),
        )
    if "Plays%" in df_summary.columns:
        gb.configure_column(
            "Plays%",
            filter="agNumberColumnFilter",
            type=["numericColumn"],
            cellStyle={"textAlign": "right"},
            valueFormatter=JsCode("function(params){ return (params.value==null)?'':(Number(params.value).toFixed(2)+'%'); }"),
        )

    # ---- JS callbacks para ajuste real de columnas ----
    on_first_data_rendered = JsCode("""
    function(params) {
        params.api.sizeColumnsToFit();
        setTimeout(function() { params.api.sizeColumnsToFit(); }, 0);
    }
    """)

    on_grid_size_changed = JsCode("""
    function(params) {
        params.api.sizeColumnsToFit();
        setTimeout(function() { params.api.sizeColumnsToFit(); }, 50);
    }
    """)

    # Estilo de filas
    row_style = JsCode("""
    function(params) {
      return { backgroundColor: '#1b263b', color: '#ffffff' };
    }
    """)

    gb.configure_grid_options(
        rowHeight=32,
        headerHeight=38,
        suppressCellFocus=True,
        rowSelection="single",
        enableBrowserTooltips=True,
        animateRows=True,
        domLayout="autoHeight",
        getRowStyle=row_style,
        onFirstDataRendered=on_first_data_rendered,
        onGridSizeChanged=on_grid_size_changed,
        suppressColumnVirtualisation=True,
    )

    grid_options = gb.build()

    # ---- Scoping por id para máxima especificidad del header ----
    st.markdown(f"""
    <style>
    #{container_id} .ag-header,
    #{container_id} .ag-header-viewport,
    #{container_id} .ag-header-row,
    #{container_id} .ag-header-cell,
    #{container_id} .ag-floating-filter {{
        background-color: #0d1b2a !important;
        background-image: none !important;
        color: #ffffff !important;
    }}
    </style>
    """, unsafe_allow_html=True)

    # Render dentro de un contenedor con id
    st.markdown(f'<div id="{container_id}">', unsafe_allow_html=True)

    AgGrid(
        df_summary,
        gridOptions=grid_options,
        fit_columns_on_grid_load=False,
        theme="alpine-dark",
        allow_unsafe_jscode=True,
        custom_css=AGGRID_CUSTOM_CSS,
    )
    st.markdown('</div>', unsafe_allow_html=True)

# =========================
# TIME PATTERNS
# =========================

def time_of_hour(df, start_date, end_date, period_filter):
    df_filtered = df[(df["datetime"] >= start_date) & (df["datetime"] <= end_date)]
    df_filtered = apply_time_filter(df_filtered, period_filter)

    df_filtered = df_filtered.copy()
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
    
    fig.update_traces(marker_line_width=0)

    st.plotly_chart(fig, use_container_width=True)

def time_of_weekday(df, start_date, end_date, period_filter):
    df_filtered = df[(df["datetime"] >= start_date) & (df["datetime"] <= end_date)]
    df_filtered = apply_time_filter(df_filtered, period_filter)

    df_filtered = df_filtered.copy()
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
    fig.update_traces(marker_line_width=0)
    st.plotly_chart(fig, use_container_width=True)

# =========================
# UI - SIDEBAR GLOBAL + TABS
# =========================

st.sidebar.title("Filtros Globales")

# Filtros globales
global_start = pd.to_datetime(st.sidebar.date_input("Start Date", datetime(2025,1,1))).tz_localize(LOCAL_TZ)
global_end   = pd.to_datetime(st.sidebar.date_input("End Date", datetime.now())).tz_localize(LOCAL_TZ)
global_period = st.sidebar.selectbox("Time period", ["day", "week", "month", "year"], index=2)
global_time_filter = st.sidebar.selectbox("Time of day", ["All","Morning","Afternoon","Night"], index=0)
global_rows_to_show = st.sidebar.selectbox(
    "Number of rows",
    [10, 25, 50, 100, 200, 500],
    index=0
)

# =========================
# TABS
# =========================

st.title("Music Stats")
tab1, tab2, tab3, tab4 = st.tabs([
    "Summary",
    "Tracks / Artists / Albums",
    "Time Patterns",
    "Listening Behavior"
])


# =========================
# TAB 1 - Listening Summary
# =========================
with tab1:
    # Filtrado por fecha y hora
    df_filtered = df[(df["datetime"] >= global_start) & (df["datetime"] <= global_end)]
    df_filtered = apply_time_filter(df_filtered, global_time_filter)

    # Generamos el resumen completo por periodo
    summary_full = get_listening_summary(df_filtered, global_period)

    if not summary_full.empty:

        # --------------------------
        # Period max/min minutos
        # --------------------------
        idx_max_minutes = summary_full["Minutes"].idxmax()
        idx_min_minutes = summary_full["Minutes"].idxmin()

        period_max_minutes_period = summary_full.loc[idx_max_minutes, "Period"]
        period_max_minutes_val = summary_full.loc[idx_max_minutes, "Minutes"]

        period_min_minutes_period = summary_full.loc[idx_min_minutes, "Period"]
        period_min_minutes_val = summary_full.loc[idx_min_minutes, "Minutes"]

        avg_minutes = round(summary_full["Minutes"].mean(), 2)

        # --------------------------
        # Period max/min plays
        # --------------------------
        idx_max_plays = summary_full["Plays"].idxmax()
        idx_min_plays = summary_full["Plays"].idxmin()

        period_max_plays_period = summary_full.loc[idx_max_plays, "Period"]
        period_max_plays_val = summary_full.loc[idx_max_plays, "Plays"]

        period_min_plays_period = summary_full.loc[idx_min_plays, "Period"]
        period_min_plays_val = summary_full.loc[idx_min_plays, "Plays"]

        avg_plays = round(summary_full["Plays"].mean(), 2)

        # --------------------------
        # Top Artist / Track / Album usando summary_full
        # --------------------------
        # Agrupamos por Artist / Track / Album sobre df_filtered ya resumido por periodo
        top_artist_series = summary_full.groupby("Top Artist").size()
        top_artist = top_artist_series.idxmax()
        top_artist_count = top_artist_series.max()

        top_track_series = summary_full.groupby("Top Track").size()
        top_track = top_track_series.idxmax()
        top_track_count = top_track_series.max()

        top_album_series = summary_full.groupby("Top Album").size()
        top_album = top_album_series.idxmax()
        top_album_count = top_album_series.max()

        # --------------------------
        # Rachas consecutivas
        # --------------------------
        summary_sorted = summary_full.sort_values("Period")

        track_streak_val, track_streak_len = longest_streak(summary_sorted["Top Track"])
        artist_streak_val, artist_streak_len = longest_streak(summary_sorted["Top Artist"])
        album_streak_val, album_streak_len = longest_streak(summary_sorted["Top Album"])

        first_track_listen = df.groupby("track")["datetime"].min().reset_index()
        new_tracks = first_track_listen[
            (first_track_listen["datetime"] >= global_start) &
            (first_track_listen["datetime"] <= global_end)
        ]

        first_artist_listen = df.groupby("artist")["datetime"].min().reset_index()
        new_artists = first_artist_listen[
            (first_artist_listen["datetime"] >= global_start) &
            (first_artist_listen["datetime"] <= global_end)
        ]

        first_album_listen = df.groupby("album")["datetime"].min().reset_index()
        new_albums = first_album_listen[
            (first_album_listen["datetime"] >= global_start) &
            (first_album_listen["datetime"] <= global_end)
        ]


        artist_counts = df_filtered["artist"].value_counts(normalize=True)
        diversity = 1 - (artist_counts**2).sum()

        # --------------------------
        # Mostrar métricas
        # --------------------------
        r1, r2, r3 = st.columns(3)
        r1.metric("Period max minutes", f"{period_max_minutes_period} ({period_max_minutes_val} min)")
        r2.metric(f"Average minutes per {global_period}", f"{avg_minutes} min")
        r3.metric("Period min minutes", f"{period_min_minutes_period} ({period_min_minutes_val} min)")

        r1, r2, r3 = st.columns(3)
        r1.metric("Top Artist most repeated", 
                  f"{top_artist} ({top_artist_count})",
                  help=f"{top_artist} ({top_artist_count})"
                  )
        r2.metric(
            "Top Track most repeated",
            f"{top_track} ({top_track_count})",
            help=f"{top_track} ({top_track_count})"
            )
        r3.metric("Top Album most repeated",
                   f"{top_album} ({top_album_count})",
                   help= f"{top_album} ({top_album_count})"
                   )

        r1, r2, r3 = st.columns(3)
        r1.metric("Period max plays", f"{period_max_plays_period} ({period_max_plays_val} plays)")
        r2.metric(f"Average plays per {global_period}", f"{avg_plays}")
        r3.metric("Period min plays", f"{period_min_plays_period} ({period_min_plays_val} plays)")

        r2, r1, r3 = st.columns(3)

        r2.metric(
            "Longest Top Artist streak",
            f"{artist_streak_val} ({artist_streak_len})",
            help=f"{artist_streak_val} ({artist_streak_len})")
        r1.metric(
            "Longest Top Track streak",
            f"{track_streak_val} ({track_streak_len})",
            help=f"{track_streak_val} ({track_streak_len})")
        r3.metric(
            "Longest Top Album streak",
            f"{album_streak_val} ({album_streak_len})",
            help=f"{album_streak_val} ({album_streak_len})")

        r1, r2, r3 = st.columns(3)

        r1.metric("New artists discovered", len(new_artists))
        r2.metric("New tracks discovered", len(new_tracks))
        r3.metric("New albums discovered", len(new_albums))

        st.metric("Artist diversity index", round(diversity,3))
        

    # --------------------------
    # Tabla en orden descendente
    # --------------------------
    summary_table = summary_full.sort_values("Period", ascending=False).head(global_rows_to_show)
    display_aggrid(summary_table, container_id="grid_summary_tab1")

    # --------------------------
    # Gráficas de minutos y plays
    # --------------------------
    fig = px.bar(
        summary_full,
        x="Period",
        y="Minutes",
        labels={"Minutes": "Minutes", "Period": "Date"},
        title="Minutes Listened Over Time"
    )
    fig.update_traces(marker_line_width=0)
    st.plotly_chart(fig, use_container_width=True)

    fig2 = px.bar(
        summary_full,
        x="Period",
        y="Plays",
        labels={"Plays": "Plays", "Period": "Date"},
        title="Plays Over Time"
    )
    fig2.update_traces(marker_line_width=0)
    st.plotly_chart(fig2, use_container_width=True)

# =========================
# TAB 2 - Full Data Viewer
# =========================

with tab2:

    df_fd = df[(df["datetime"] >= global_start) & (df["datetime"] <= global_end)]
    df_fd = apply_time_filter(df_fd, global_time_filter)
    df_fd = df_fd.copy()

    df_fd["track"] = df_fd["track"].str.title()
    df_fd["artist"] = df_fd["artist"].str.title()
    if "album" in df_fd.columns:
        df_fd["album"] = df_fd["album"].str.title()

    # ======================================================================
    # Cálculo correcto de días efectivos según los datos disponibles
    # ======================================================================
    if not df_fd.empty:
        data_start = df_fd["datetime"].min()
        data_end = df_fd["datetime"].max()

        effective_start = max(global_start, data_start)
        effective_end = min(global_end, data_end)

        effective_days = (effective_end - effective_start).days + 1
        if effective_days < 1:
            effective_days = 1
    else:
        effective_days = 1  # evitar divisiones por 0

    total_minutes_fd = df_fd["duration"].sum() / 60 if not df_fd.empty else 0.0

    # ======================================================================
    # TRACKS
    # ======================================================================
    st.markdown("### Tracks")

    n_unique_tracks = df_fd["track"].nunique()
    avg_minutes_per_track = round(total_minutes_fd / n_unique_tracks, 2) if n_unique_tracks > 0 else 0.0
    plays_per_day = round(len(df_fd) / effective_days, 2)
    minutes_per_day = round(total_minutes_fd / effective_days, 2)

    c1, c2, c4, c3 = st.columns(4)
    c1.metric("Unique tracks", n_unique_tracks)
    c2.metric("Minutes per track", f"{avg_minutes_per_track:.2f} min")
    c3.metric("Plays per day", plays_per_day)
    c4.metric("Minutes per day", f"{minutes_per_day:.2f} min")

    tracks_summary = summarize(df_fd, "track")
    tracks_summary.rename(columns={"track": "Track"}, inplace=True)
    tracks_summary = add_share_columns(tracks_summary)

    df_sorted = df_filtered.sort_values("datetime")
    df_sorted["prev_track"] = df_sorted["track"].shift()
    df_sorted["new_block"] = df_sorted["track"] != df_sorted["prev_track"]
    df_sorted["block"] = df_sorted["new_block"].cumsum()

    repeats = df_sorted.groupby(["track","block"]).size()
    top_repeats = repeats.groupby("track").max().sort_values(ascending=False)

    c1, c2, c3= st.columns(3)

    # Track con más repeticiones consecutivas
    top_track = top_repeats.index[0]

    # Filtramos las reproducciones de ese track
    track_plays = df_sorted[df_sorted['track'] == top_track].sort_values("datetime")

    # Creamos un identificador de racha
    track_plays['diff'] = track_plays['datetime'].diff().dt.total_seconds().fillna(0)
    # Consideramos que si la diferencia > 1 día, es otra racha (ajusta según tu criterio)
    track_plays['streak_id'] = (track_plays['diff'] > 3600).cumsum()  

    # Contamos la racha más larga
    streak_lengths = track_plays.groupby('streak_id').size()
    longest_streak_id = streak_lengths.idxmax()
    longest_streak = track_plays[track_plays['streak_id'] == longest_streak_id]

    # Primera y última reproducción de la racha
    first_play = longest_streak['datetime'].min()
    last_play = longest_streak['datetime'].max()
    num_plays = len(longest_streak)

    # Mostramos métricas
    c1.metric("Longest track repeat streak", f"{top_repeats.iloc[0]} plays of {top_repeats.index[0]}", help=f"{top_repeats.iloc[0]} plays of {top_repeats.index[0]}")
    c2.metric("First play of the streak", first_play.strftime('%Y-%m-%d %H:%M:%S'))
    c3.metric("Last play of the streak", last_play.strftime('%Y-%m-%d %H:%M:%S'))

    # Reordenar columnas: Track | Minutes | Minutes% | Plays | Plays%
    tracks_summary = tracks_summary[["Track", "Minutes", "Minutes%", "Plays", "Plays%"]]
    tracks_summary = tracks_summary.head(global_rows_to_show)
    display_aggrid(tracks_summary, container_id="grid_tracks")

    

    # ======================================================================
    # ARTISTS
    # ======================================================================
    st.markdown("### Artists")

    n_unique_artists = df_fd["artist"].nunique()
    avg_minutes_per_artist = round(total_minutes_fd / n_unique_artists, 2) if n_unique_artists > 0 else 0.0

    c1, c2, c4, c3 = st.columns(4)
    c1.metric("Unique artists", n_unique_artists)
    c2.metric("Minutes per artist", f"{avg_minutes_per_artist:.2f} min")
    c3.metric("Plays per day", plays_per_day)
    c4.metric("Minutes per day", f"{minutes_per_day:.2f} min")

    df_sorted = df_filtered.sort_values("datetime")
    df_sorted["prev_artist"] = df_sorted["artist"].shift()
    df_sorted["new_block"] = df_sorted["artist"] != df_sorted["prev_artist"]
    df_sorted["block"] = df_sorted["new_block"].cumsum()
    
    repeats = df_sorted.groupby(["artist","block"]).size()
    top_repeats = repeats.groupby("artist").max().sort_values(ascending=False)

    c1, c2, c3= st.columns(3)

    # Track con más repeticiones consecutivas
    top_track = top_repeats.index[0]

    # Filtramos las reproducciones de ese track
    track_plays = df_sorted[df_sorted['artist'] == top_track].sort_values("datetime")

    # Creamos un identificador de racha
    track_plays['diff'] = track_plays['datetime'].diff().dt.total_seconds().fillna(0)
    # Consideramos que si la diferencia > 1 día, es otra racha (ajusta según tu criterio)
    track_plays['streak_id'] = (track_plays['diff'] > 3600).cumsum()  

    # Contamos la racha más larga
    streak_lengths = track_plays.groupby('streak_id').size()
    longest_streak_id = streak_lengths.idxmax()
    longest_streak = track_plays[track_plays['streak_id'] == longest_streak_id]

    # Primera y última reproducción de la racha
    first_play = longest_streak['datetime'].min()
    last_play = longest_streak['datetime'].max()
    num_plays = len(longest_streak)

    # Mostramos métricas
    c1.metric("Longest track repeat streak", f"{top_repeats.iloc[0]} plays of {top_repeats.index[0]}", help=f"{top_repeats.iloc[0]} plays of {top_repeats.index[0]}")
    c2.metric("First play of the streak", first_play.strftime('%Y-%m-%d %H:%M:%S'))
    c3.metric("Last play of the streak", last_play.strftime('%Y-%m-%d %H:%M:%S'))

    artists_summary = summarize(df_fd, "artist")
    artists_summary.rename(columns={"artist": "Artist"}, inplace=True)
    artists_summary = add_share_columns(artists_summary)
    artists_summary = artists_summary[["Artist", "Minutes", "Minutes%", "Plays", "Plays%"]]
    artists_summary = artists_summary.head(global_rows_to_show)
    display_aggrid(artists_summary, container_id="grid_artists")



    # ======================================================================
    # ALBUMS
    # ======================================================================
    st.markdown("### Albums")

    n_unique_albums = df_fd["album"].nunique()
    avg_minutes_per_album = round(total_minutes_fd / n_unique_albums, 2) if n_unique_albums > 0 else 0.0

    c1, c2, c4, c3 = st.columns(4)
    c1.metric("Unique albums", n_unique_albums)
    c2.metric("Minutes per album", f"{avg_minutes_per_album:.2f} min")
    c3.metric("Plays per day", plays_per_day)
    c4.metric("Minutes per day", f"{minutes_per_day:.2f} min")

    df_sorted = df_filtered.sort_values("datetime")
    df_sorted["prev_album"] = df_sorted["album"].shift()
    df_sorted["new_block"] = df_sorted["album"] != df_sorted["prev_album"]
    df_sorted["block"] = df_sorted["new_block"].cumsum()

    repeats = df_sorted.groupby(["album","block"]).size()
    top_repeats = repeats.groupby("album").max().sort_values(ascending=False)

    c1, c2, c3= st.columns(3)

    # Track con más repeticiones consecutivas
    top_track = top_repeats.index[0]

    # Filtramos las reproducciones de ese track
    track_plays = df_sorted[df_sorted['album'] == top_track].sort_values("datetime")

    # Creamos un identificador de racha
    track_plays['diff'] = track_plays['datetime'].diff().dt.total_seconds().fillna(0)
    # Consideramos que si la diferencia > 1 día, es otra racha (ajusta según tu criterio)
    track_plays['streak_id'] = (track_plays['diff'] > 3600).cumsum()  

    # Contamos la racha más larga
    streak_lengths = track_plays.groupby('streak_id').size()
    longest_streak_id = streak_lengths.idxmax()
    longest_streak = track_plays[track_plays['streak_id'] == longest_streak_id]

    # Primera y última reproducción de la racha
    first_play = longest_streak['datetime'].min()
    last_play = longest_streak['datetime'].max()
    num_plays = len(longest_streak)

    # Mostramos métricas
    c1.metric("Longest track repeat streak", f"{top_repeats.iloc[0]} plays of {top_repeats.index[0]}", help=f"{top_repeats.iloc[0]} plays of {top_repeats.index[0]}")
    c2.metric("First play of the streak", first_play.strftime('%Y-%m-%d %H:%M:%S'))
    c3.metric("Last play of the streak", last_play.strftime('%Y-%m-%d %H:%M:%S'))

    albums_summary = summarize(df_fd, "album")
    albums_summary.rename(columns={"album": "Album"}, inplace=True)
    albums_summary = add_share_columns(albums_summary)
    albums_summary = albums_summary[["Album", "Minutes", "Minutes%", "Plays", "Plays%"]]
    albums_summary = albums_summary.head(global_rows_to_show)
    display_aggrid(albums_summary, container_id="grid_albums")

        
# =========================
# TAB 3 - Time Patterns
# =========================

with tab3:

    # =========================
    # CLOCK CHART — Listening Time by Hour (Radial)
    # =========================
    df_clock = df[(df["datetime"] >= global_start) & (df["datetime"] <= global_end)]
    df_clock = apply_time_filter(df_clock, global_time_filter).copy()

    if not df_clock.empty:
        df_clock["hour"] = df_clock["datetime"].dt.hour

        summary_clock = (
            df_clock.groupby("hour")["duration"].sum().reset_index()
        )
        summary_clock["minutes"] = summary_clock["duration"] / 60

        # Convertimos horas a strings para poder ordenarlas correctamente en polar
        summary_clock["hour_str"] = summary_clock["hour"].astype(str)

        # Orden de horas circular 0–23
        hour_order = [str(h) for h in range(24)]

        fig_clock = px.line_polar(
            summary_clock,
            r="minutes",
            theta="hour_str",
            category_orders={"hour_str": hour_order},
            line_close=True,
            markers=True,
            title="Clock Chart — Minutes Listened by Hour",
        )

        # Estética coherente con la app
        fig_clock.update_traces(
            line=dict(color="#FF4B4B", width=3),
            marker=dict(size=6, color="#FF4B4B")
        )

        # Ajustes de eje polar estilo reloj
        fig_clock.update_layout(
            polar=dict(
                bgcolor="#111825",   
                radialaxis=dict(
                            showticklabels=False,   # Oculta los números
                            ticks='',               # Quita marcas
                            showgrid=True,          # Mantiene la rejilla (opcional)
                            gridcolor="#3a4750",
                            showline=False,          # Sin línea radial central
                        ),
                angularaxis=dict(
                    direction="clockwise",
                    rotation=90,        # 0h hacia arriba
                    color="white",
                    gridcolor="#3a4750",
                ),
            ),
            font=dict(color="white")
        )


        st.plotly_chart(fig_clock, use_container_width=True)

    else:
        st.info("No hay datos para el rango seleccionado.")


    time_of_hour(df, global_start, global_end, global_time_filter)
    time_of_weekday(df, global_start, global_end, global_time_filter)

    # =========================
    # HEATMAP 1 — Hora (filas) × Día de la semana (columnas)
    # =========================
    df_hm = df[(df["datetime"] >= global_start) & (df["datetime"] <= global_end)]
    df_hm = apply_time_filter(df_hm, global_time_filter).copy()

    df_hm["hour"] = df_hm["datetime"].dt.hour
    df_hm["weekday"] = df_hm["datetime"].dt.day_name()

    weekday_order = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]

    heatmap1 = (
        df_hm.groupby(["hour", "weekday"])["duration"].sum()
        .reset_index()
        .pivot(index="hour", columns="weekday", values="duration")
        .reindex(columns=weekday_order, fill_value=0)
    ) / 60
    heatmap1 = heatmap1.round(2)

    fig_hm1 = px.imshow(
        heatmap1.values,                    # pasar solo los valores
        x=heatmap1.columns,                 # columnas = weekdays
        y=heatmap1.index,                   # filas = hours
        labels=dict(x="Weekday", y="Hour", color="Minutes"),
        title="Heatmap — Minutes by Hour × Weekday",
        color_continuous_scale=[
            "#0d1b2a", "#3b1c5a", "#b52a3a", "#ff6e48", "#ffe04b"
        ],
        zmin=0,                             # asegura que el mínimo sea 0
        zmax=heatmap1.values.max(),         # máximo de la matriz
        aspect="auto"
    )
    fig_hm1.update_xaxes(side="top")
    st.plotly_chart(fig_hm1, use_container_width=True)


    # =========================
    # HEATMAP 2 — Día (filas) × Mes (columnas)
    # =========================
    df_hm2 = df[(df["datetime"] >= global_start) & (df["datetime"] <= global_end)]
    df_hm2 = apply_time_filter(df_hm2, global_time_filter).copy()

    df_hm2["weekday"] = df_hm2["datetime"].dt.day_name()
    df_hm2["month"] = df_hm2["datetime"].dt.strftime("%Y-%m")

    heatmap2 = (
        df_hm2.groupby(["weekday", "month"])["duration"].sum()
        .reset_index()
        .pivot(index="weekday", columns="month", values="duration")
        .reindex(index=weekday_order, fill_value=0)
    ) / 60
    heatmap2 = heatmap2.round(2)

    fig_hm2 = px.imshow(
        heatmap2.values,
        x=heatmap2.columns,
        y=heatmap2.index,
        labels=dict(x="Month", y="Weekday", color="Minutes"),
        title="Heatmap — Minutes by Weekday × Month",
        color_continuous_scale=[
            "#0d1b2a", "#3b1c5a", "#b52a3a", "#ff6e48", "#ffe04b"
        ],
        zmin=0,
        zmax=heatmap2.values.max(),
        aspect="auto"
    )
    fig_hm2.update_xaxes(side="top")
    st.plotly_chart(fig_hm2, use_container_width=True)

with tab4:
    df_sorted = df_filtered.sort_values("datetime")

    df_sorted["gap"] = df_sorted["datetime"].diff().dt.total_seconds() / 60

    df_sorted["session"] = (df_sorted["gap"] > 30).cumsum()

    sessions = df_sorted.groupby("session").agg(
        start=("datetime", "min"),
        end=("datetime", "max"),        # timestamp de inicio del último track
        last_duration=("duration", "last"),   # duración del último track
        plays=("track","count"),
        minutes_total=("duration", "sum")    # minutos totales de la sesión
    )

    sessions["minutes_total"] = sessions["minutes_total"] / 60
    # end real = timestamp inicio último track + duración del track
    sessions["end"] = sessions["end"] + pd.to_timedelta(sessions["last_duration"], unit='s')

    sessions["length"] = (sessions["end"] - sessions["start"]).dt.total_seconds() / 60
    sessions["%listening"] = (sessions["minutes_total"] / sessions["length"])*100

    longest_session = sessions.loc[sessions["length"].idxmax()]

    display_aggrid(sessions.reset_index(drop=True).sort_values("length", ascending=False).head(global_rows_to_show), container_id="grid_sessions")

    df_month = df_filtered.copy()
    df_month["month"] = df_month["datetime"].dt.to_period("M").dt.to_timestamp()

    # Top 5 artistas
    top_artists = df_filtered["artist"].value_counts().head(5).index
    df_month = df_month[df_month["artist"].isin(top_artists)]

    # Resumir minutos por artista y mes
    summary = df_month.groupby(["month","artist"])["duration"].sum().reset_index()
    summary["minutes"] = summary["duration"] / 60

    # Crear la figura
    fig_artists = go.Figure()

    colors = px.colors.qualitative.Safe  # paleta de colores consistente

    for i, artist in enumerate(top_artists):
        df_artist = summary[summary["artist"] == artist]
        fig_artists.add_trace(go.Scatter(
            x=df_artist["month"],
            y=df_artist["minutes"],
            mode="lines+markers",
            name=artist,
            marker=dict(size=8),
            line=dict(width=3, color=colors[i % len(colors)]),
            hovertemplate="%{y:.2f} min<extra>%{fullData.name}</extra>"
        ))

    # Layout
    fig_artists.update_layout(
        template="plotly_dark",
        title="Artist Listening Evolution",
        xaxis_title="Month",
        yaxis_title="Minutes",
        hovermode="x unified",
    )

    st.plotly_chart(fig_artists, use_container_width=True)

    df_month = df_filtered.copy()
    df_month["month"] = df_month["datetime"].dt.to_period("M")

    dominant = (
        df_month.groupby(["month","artist"])["duration"]
        .sum()
        .reset_index()
    )

    idx = dominant.groupby("month")["duration"].idxmax()

    dominant = dominant.loc[idx]
    dominant["minutes"] = dominant["duration"]/60