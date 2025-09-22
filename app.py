"""Streamlit app per generare dashboard di KPI partendo da file Excel."""
from __future__ import annotations

from io import BytesIO
from typing import Dict, List

import pandas as pd
import streamlit as st
import altair as alt


st.set_page_config(
    page_title="Dashboard KPI da Excel",
    page_icon="📊",
    layout="wide",
)


AGGREGATIONS = {
    "Somma": "sum",
    "Media": "mean",
    "Minimo": "min",
    "Massimo": "max",
}


def _auto_parse_dates(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Prova a convertire automaticamente le colonne testuali in date."""
    converted = dataframe.copy()

    for column in converted.columns:
        series = converted[column]
        if pd.api.types.is_object_dtype(series):
            parsed = pd.to_datetime(series, errors="coerce", dayfirst=True)
            if parsed.notna().mean() > 0.6:
                converted[column] = parsed

    return converted


def format_number(value: float) -> str:
    """Formatta i numeri usando la convenzione italiana (., per migliaia e , per decimali)."""
    if pd.isna(value):
        return "-"

    formatted = f"{value:,.2f}"
    formatted = formatted.replace(",", "¤").replace(".", ",").replace("¤", ".")
    return formatted


@st.cache_data(show_spinner=False)
def load_excel(file_bytes: bytes) -> Dict[str, pd.DataFrame]:
    """Legge tutte le pagine di un file Excel e restituisce un dizionario."""
    buffer = BytesIO(file_bytes)
    with pd.ExcelFile(buffer) as xls:
        sheets = {name: xls.parse(name) for name in xls.sheet_names}
    return sheets


def describe_numeric_columns(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Genera statistiche descrittive per le colonne numeriche."""
    numeric_df = dataframe.select_dtypes(include="number")
    if numeric_df.empty:
        return pd.DataFrame()

    summary = numeric_df.agg(["sum", "mean", "min", "max", "median", "count"]).transpose()
    summary = summary.rename(
        columns={
            "sum": "Somma",
            "mean": "Media",
            "min": "Minimo",
            "max": "Massimo",
            "median": "Mediana",
            "count": "Conteggio",
        }
    )
    summary.index.name = "Colonna"
    return summary.reset_index()


def prepare_categorical_columns(dataframe: pd.DataFrame) -> List[str]:
    """Restituisce le colonne che possono essere usate come dimensioni."""
    categorical_cols: List[str] = []
    for column in dataframe.columns:
        series = dataframe[column]
        if pd.api.types.is_categorical_dtype(series) or pd.api.types.is_bool_dtype(series):
            categorical_cols.append(column)
        elif pd.api.types.is_object_dtype(series):
            if series.nunique(dropna=True) <= max(50, len(series) // 5):
                categorical_cols.append(column)
        elif pd.api.types.is_datetime64_any_dtype(series):
            categorical_cols.append(column)
    return categorical_cols


st.title("📈 Dashboard automatica di KPI da Excel")
st.write(
    "Carica un file Excel per generare automaticamente dashboard interattive. "
    "L'app identifica le colonne numeriche e testuali per calcolare KPI, grafici e tendenze temporali."
)

uploaded_file = st.file_uploader("Carica un file Excel", type=["xls", "xlsx"])

if uploaded_file is None:
    st.info("⬆️ Carica un file per iniziare.")
    st.stop()

try:
    sheets_data = load_excel(uploaded_file.getvalue())
except ValueError as error:  # file non valido
    st.error(f"Impossibile leggere il file: {error}")
    st.stop()

if not sheets_data:
    st.warning("Il file non contiene fogli di lavoro.")
    st.stop()

selected_sheet = st.selectbox("Scegli il foglio da analizzare", list(sheets_data.keys()))
raw_df = sheets_data[selected_sheet]

if raw_df.empty:
    st.warning("Il foglio selezionato è vuoto.")
    st.stop()

df = _auto_parse_dates(raw_df).convert_dtypes()

st.subheader("Anteprima dei dati")
st.dataframe(df.head(100))
st.caption(f"Osservazioni totali: {len(df):,} · Colonne: {len(df.columns)}")

numeric_columns = df.select_dtypes(include="number").columns.tolist()

if numeric_columns:
    st.subheader("KPI principali")
    metric_cols = st.columns(min(3, len(numeric_columns)))
    for index, column in enumerate(numeric_columns[: len(metric_cols)]):
        column_sum = df[column].sum()
        column_mean = df[column].mean()
        metric_cols[index].metric(
            label=f"Somma {column}",
            value=format_number(column_sum),
            delta=f"Media {format_number(column_mean)}",
        )

    stats_df = describe_numeric_columns(df)
    if not stats_df.empty:
        formatted_columns = {
            column: format_number for column in stats_df.columns if column != "Colonna"
        }
        st.dataframe(stats_df.style.format(formatted_columns))
else:
    st.warning(
        "Non sono state trovate colonne numeriche nel foglio selezionato."
    )

categorical_columns = prepare_categorical_columns(df)

if numeric_columns and categorical_columns:
    st.subheader("Analisi per dimensione")

    dimension = st.selectbox("Dimensione", categorical_columns)
    metrics = st.multiselect(
        "Metriche da analizzare", numeric_columns, default=numeric_columns[:1]
    )
    aggregation_label = st.selectbox(
        "Tipo di aggregazione",
        options=list(AGGREGATIONS.keys()),
        index=0,
    )

    aggregation_function = AGGREGATIONS[aggregation_label]

    if metrics:
        grouped = df.groupby(dimension)[metrics].agg(aggregation_function).reset_index()
        melted = grouped.melt(id_vars=dimension, var_name="Metrica", value_name="Valore")

        if pd.api.types.is_datetime64_any_dtype(df[dimension]):
            x_axis = alt.X(f"{dimension}:T", title=dimension)
        else:
            x_axis = alt.X(f"{dimension}:N", sort="-y", title=dimension)

        chart = (
            alt.Chart(melted)
            .mark_bar()
            .encode(
                x=x_axis,
                y="Valore:Q",
                color="Metrica:N",
                tooltip=[dimension, "Metrica", alt.Tooltip("Valore:Q", format=",.2f")],
            )
            .properties(height=400)
        )
        st.altair_chart(chart, use_container_width=True)
        formatted_metrics = {
            column: format_number for column in grouped.columns if column != dimension
        }
        st.dataframe(grouped.style.format(formatted_metrics))
    else:
        st.info("Seleziona almeno una metrica numerica per generare il grafico.")

    st.caption(
        "Suggerimento: prova ad aggiungere filtri o modificare l'aggregazione per ottenere "
        "nuove prospettive sui tuoi KPI."
    )

    st.markdown("---")

if numeric_columns:
    date_columns = [
        column for column in df.columns if pd.api.types.is_datetime64_any_dtype(df[column])
    ]

    if date_columns:
        st.subheader("Trend temporali")
        date_column = st.selectbox("Colonna temporale", date_columns)
        timeseries_metric = st.selectbox("Metrica", numeric_columns)
        timeseries_aggregation_label = st.selectbox(
            "Aggregazione", options=list(AGGREGATIONS.keys()), index=0
        )
        resample_option = st.selectbox(
            "Frequenza",
            options=["Automatica", "Giornaliera", "Settimanale", "Mensile", "Trimestrale"],
            index=0,
        )

        resample_map = {
            "Automatica": None,
            "Giornaliera": "D",
            "Settimanale": "W",
            "Mensile": "M",
            "Trimestrale": "Q",
        }
        resample_rule = resample_map[resample_option]

        ts_df = df[[date_column, timeseries_metric]].dropna()
        if not ts_df.empty:
            ts_df = ts_df.sort_values(by=date_column)
            aggregation_function = AGGREGATIONS[timeseries_aggregation_label]
            if resample_rule:
                ts_df = (
                    ts_df.set_index(date_column)
                    .resample(resample_rule)
                    .agg({timeseries_metric: aggregation_function})
                    .reset_index()
                )
            else:
                ts_df = (
                    ts_df.groupby(date_column, as_index=False)[timeseries_metric]
                    .agg(aggregation_function)
                    .sort_values(by=date_column)
                )
            line_chart = (
                alt.Chart(ts_df)
                .mark_line(point=True)
                .encode(
                    x=alt.X(f"{date_column}:T", title="Data"),
                    y=alt.Y(f"{timeseries_metric}:Q", title=timeseries_metric),
                    tooltip=[
                        alt.Tooltip(f"{date_column}:T", title="Data"),
                        alt.Tooltip(f"{timeseries_metric}:Q", format=",.2f", title="Valore"),
                    ],
                )
                .properties(height=400)
            )
            st.altair_chart(line_chart, use_container_width=True)
            st.dataframe(
                ts_df.style.format({timeseries_metric: format_number})
            )
        else:
            st.info("Nessun dato disponibile dopo la pulizia delle date.")

st.success("Dashboard generata! Esplora i grafici e i KPI per ottenere insight immediati.")
