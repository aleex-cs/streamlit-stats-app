import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import os
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode


# =========================
# CONFIG
# =========================

LOCAL_TZ = "Europe/Madrid"

st.set_page_config(page_title="Music Stats", layout="wide")
st.markdown("""
<style>
/* Fondo general azul oscuro en todos los wrappers/contendedores */
.ag-theme-alpine-dark .ag-root-wrapper,
.ag-theme-alpine-dark .ag-root,
.ag-theme-alpine-dark .ag-center-cols-viewport,
.ag-theme-alpine-dark .ag-center-cols-container,
.ag-theme-alpine-dark .ag-body-viewport,
.ag-theme-alpine-dark .ag-body-horizontal-scroll-viewport,
.ag-theme-alpine-dark .ag-body-vertical-scroll-viewport {
    background-color: #1b263b !important; /* azul oscuro */
}

/* Forzar fondo en filas y en CADA celda (clave para evitar "zebra" blanca) */
.ag-theme-alpine-dark .ag-row,
.ag-theme-alpine-dark .ag-row .ag-cell,
.ag-theme-alpine-dark .ag-row-even .ag-cell,
.ag-theme-alpine-dark .ag-row-odd .ag-cell {
    background-color: #1b263b !important; /* mismo azul en todas */
    color: #ffffff !important;
}

/* Hover consistente */
.ag-theme-alpine-dark .ag-row:hover .ag-cell,
.ag-theme-alpine-dark .ag-row-hover .ag-cell {
    background-color: #24344d !important;
}

/* Header en azul más profundo */
.ag-theme-alpine-dark .ag-header,
.ag-theme-alpine-dark .ag-header-viewport,
.ag-theme-alpine-dark .ag-header-row,
.ag-theme-alpine-dark .ag-header-cell,
.ag-theme-alpine-dark .ag-floating-filter {
    background-color: #0d1b2a !important;
    background-image: none !important; /* <- evita blanqueo por gradiente */
    color: #ffffff !important;
}

/* Bordes sutiles */
.ag-theme-alpine-dark .ag-root-wrapper,
.ag-theme-alpine-dark .ag-root {
    border-radius: 10px !important;
    border: 1px solid rgba(255,255,255,0.12) !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.12);
}

/* Inputs de filtro */
.ag-theme-alpine-dark .ag-input-field-input,
.ag-theme-alpine-dark .ag-text-field-input {
    background-color: rgba(255,255,255,0.06) !important;
    color: #ffffff !important;
    border: 1px solid rgba(255,255,255,0.12) !important;
    border-radius: 6px !important;
}
</style>
""", unsafe_allow_html=True)


DATA_PATH = "data/scrobbles.csv"
DURATIONS_PATH = "data/durations.csv"

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
            durations.get("duration", pd.Series(dtype=float)),
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
        df["Period"] = df["datetime"].dt.to_period("W").apply(lambda r: r.start_time.date())
    elif period == "day":
        df["Period"] = df["datetime"].dt.floor("D").dt.date
    elif period == "month":
        df["Period"] = df["datetime"].dt.to_period("M").apply(lambda r: r.start_time.date())
    elif period == "year":
        df["Period"] = df["datetime"].dt.to_period("Y").apply(lambda r: r.start_time.date())

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
tab1, tab2, tab3 = st.tabs([
    "Summary",
    "Tracks / Artists / Albums",
    "Time Patterns"
])

# =========================
# TAB 1 - Listening Summary
# =========================

with tab1:
    df_filtered = df[(df["datetime"] >= global_start) & (df["datetime"] <= global_end)]
    df_filtered = apply_time_filter(df_filtered, global_time_filter)

    # Generamos TODO el resumen
    summary_full = get_listening_summary(df_filtered, global_period)

    # Indicador total
    st.caption(f"Total rows in summary: {len(summary_full):,}")

    # Tabla en orden descendente + número global de filas
    summary_table = summary_full.sort_values("Period", ascending=False).head(global_rows_to_show)
    display_aggrid(summary_table, container_id="grid_summary_tab1")

    # Gráfica con todos los datos
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

    artists_summary = summarize(df_fd, "artist")
    artists_summary.rename(columns={"artist": "Artist"}, inplace=True)
    artists_summary = add_share_columns(artists_summary)
    artists_summary = artists_summary[["Artist", "Minutes", "Minutes%", "Plays", "Plays%"]]
    artists_summary = artists_summary.head(global_rows_to_show)
    display_aggrid(artists_summary, container_id="grid_artists")

    # ======================================================================
    # ALBUMS
    # ======================================================================
    if "album" in df_fd.columns:
        st.markdown("### Albums")

        n_unique_albums = df_fd["album"].nunique()
        avg_minutes_per_album = round(total_minutes_fd / n_unique_albums, 2) if n_unique_albums > 0 else 0.0

        c1, c2, c4, c3 = st.columns(4)
        c1.metric("Unique albums", n_unique_albums)
        c2.metric("Minutes per album", f"{avg_minutes_per_album:.2f} min")
        c3.metric("Plays per day", plays_per_day)
        c4.metric("Minutes per day", f"{minutes_per_day:.2f} min")

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
    time_of_hour(df, global_start, global_end, global_time_filter)
    time_of_weekday(df, global_start, global_end, global_time_filter)