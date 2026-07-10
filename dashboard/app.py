"""
Dashboard de Saneamento Básico — Engenharia de Dados Brasil

Consome a camada Gold do pipeline e exibe indicadores de abastecimento de água
por município, UF e prestador de serviço.

Para executar:
    streamlit run dashboard/app.py
"""

from pathlib import Path
import sys

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from src.utils.sinisa_labels import SINISA_AGUA_LABELS

GOLD_PATH = PROJECT_ROOT / "data" / "gold" / "infra_municipios_agua.parquet"

st.set_page_config(
    page_title="Saneamento Brasil",
    page_icon="💧",
    layout="wide",
)

COLUMN_LABELS = {
    "codigo_ibge": "Código IBGE",
    "municipio": "Município",
    "uf": "UF",
    "nome_do_prestador": "Prestador de serviço",
    "natureza_juridica": "Natureza jurídica",
    "abrangencia": "Abrangência",
    "capital": "Capital",
    "rm_ride": "RM/RIDE",
    "fonte": "Fonte",
    "arquivo_origem": "Arquivo de origem",
    "dt_ingestao": "Data de ingestão",
    "ano_referencia": "Ano de referência",
    **SINISA_AGUA_LABELS,
}


def get_label(coluna: str) -> str:
    return COLUMN_LABELS.get(coluna, coluna)


def rename_columns_for_display(df: pd.DataFrame) -> pd.DataFrame:
    return df.rename(columns=COLUMN_LABELS)


@st.cache_data
def load_data() -> pd.DataFrame:
    if not GOLD_PATH.exists():
        return pd.DataFrame()
    return pd.read_parquet(GOLD_PATH)


def format_percent(value) -> str:
    if pd.isna(value):
        return "-"
    return f"{value:.2f}%"


# -----------------------------------------------------------------------
# Carregamento dos dados
# -----------------------------------------------------------------------

df = load_data()

st.title("💧 Saneamento Básico Brasil")
st.markdown(
    "Pipeline de engenharia de dados para análise de indicadores públicos "
    "de abastecimento de água nos municípios brasileiros. "
    "Fonte: **SINISA / SNIS** + **IBGE**."
)

if df.empty:
    st.error(
        "⚠️ Dados não encontrados. Execute o pipeline completo antes de abrir o dashboard:\n\n"
        "```\n"
        "python -m src.ingestion.ibge_localidades\n"
        "python -m src.ingestion.sinisa\n"
        "python -m src.transformations.bronze_to_silver\n"
        "python -m src.transformations.build_gold\n"
        "```"
    )
    st.stop()

# -----------------------------------------------------------------------
# Filtros na barra lateral
# -----------------------------------------------------------------------

st.sidebar.header("🔍 Filtros")

ufs = sorted(df["uf"].dropna().unique()) if "uf" in df.columns else []
uf_selected = st.sidebar.multiselect("UF", ufs, default=ufs)

filtered = df.copy()
if uf_selected and "uf" in filtered.columns:
    filtered = filtered[filtered["uf"].isin(uf_selected)]

indicadores_disponiveis = [
    col for col in SINISA_AGUA_LABELS.keys() if col in filtered.columns
]

if indicadores_disponiveis:
    indicador_selecionado = st.sidebar.selectbox(
        "Indicador de análise",
        indicadores_disponiveis,
        index=0,
        format_func=get_label,
    )
else:
    indicador_selecionado = None

# -----------------------------------------------------------------------
# Métricas gerais
# -----------------------------------------------------------------------

st.subheader("📊 Visão Geral")

col1, col2, col3, col4 = st.columns(4)

total_municipios = (
    filtered["codigo_ibge"].nunique() if "codigo_ibge" in filtered.columns else len(filtered)
)
total_ufs = filtered["uf"].nunique() if "uf" in filtered.columns else 0
media_agua_total = (
    pd.to_numeric(filtered["iag0001"], errors="coerce").mean()
    if "iag0001" in filtered.columns else None
)
media_indicador = (
    pd.to_numeric(filtered[indicador_selecionado], errors="coerce").mean()
    if indicador_selecionado else None
)

col1.metric("Municípios", f"{total_municipios:,}".replace(",", "."))
col2.metric("UFs", total_ufs)
col3.metric("Atendimento médio de água", format_percent(media_agua_total))
col4.metric("Média do indicador selecionado", format_percent(media_indicador))

st.divider()

# -----------------------------------------------------------------------
# Ranking por indicador
# -----------------------------------------------------------------------

if indicador_selecionado:
    st.subheader(f"🏆 Ranking: {get_label(indicador_selecionado)}")

    ranking_cols = [
        c for c in ["codigo_ibge", "municipio", "uf", "nome_do_prestador",
                    "natureza_juridica", indicador_selecionado]
        if c in filtered.columns
    ]

    ranking = filtered[ranking_cols].copy()
    ranking[indicador_selecionado] = pd.to_numeric(ranking[indicador_selecionado], errors="coerce")

    col_r1, col_r2 = st.columns(2)

    with col_r1:
        st.markdown("##### 🔴 Menor atendimento (municípios prioritários)")
        ranking_menor = ranking.sort_values(indicador_selecionado, ascending=True, na_position="last")
        st.dataframe(rename_columns_for_display(ranking_menor.head(20)), use_container_width=True)

    with col_r2:
        st.markdown("##### 🟢 Maior atendimento")
        ranking_maior = ranking.sort_values(indicador_selecionado, ascending=False, na_position="last")
        st.dataframe(rename_columns_for_display(ranking_maior.head(20)), use_container_width=True)

else:
    st.warning("Nenhum indicador SINISA encontrado na tabela Gold.")

st.divider()

# -----------------------------------------------------------------------
# Média por UF
# -----------------------------------------------------------------------

st.subheader("🗺️ Média do indicador por UF")

if indicador_selecionado and "uf" in filtered.columns:
    temp = filtered.copy()
    temp[indicador_selecionado] = pd.to_numeric(temp[indicador_selecionado], errors="coerce")

    uf_summary = (
        temp.groupby("uf", as_index=False)
        .agg(
            media_indicador=(indicador_selecionado, "mean"),
            municipios=("codigo_ibge", "nunique"),
        )
        .sort_values("media_indicador", ascending=False)
    )

    st.bar_chart(uf_summary.set_index("uf")["media_indicador"])

    st.dataframe(
        uf_summary.rename(columns={
            "uf": "UF",
            "media_indicador": get_label(indicador_selecionado),
            "municipios": "Municípios",
        }),
        use_container_width=True,
    )

st.divider()

# -----------------------------------------------------------------------
# Distribuição por natureza jurídica
# -----------------------------------------------------------------------

st.subheader("🏢 Distribuição por natureza jurídica do prestador")

if "natureza_juridica" in filtered.columns:
    natureza = (
        filtered["natureza_juridica"]
        .fillna("Não informado")
        .value_counts()
        .reset_index()
    )
    natureza.columns = ["natureza_juridica", "quantidade"]

    st.bar_chart(natureza.set_index("natureza_juridica")["quantidade"])
    st.dataframe(
        natureza.rename(columns={
            "natureza_juridica": "Natureza jurídica",
            "quantidade": "Quantidade",
        }),
        use_container_width=True,
    )

st.divider()

# -----------------------------------------------------------------------
# Tabela completa com download
# -----------------------------------------------------------------------

st.subheader("📋 Base analítica Gold completa")

display_df = rename_columns_for_display(filtered.copy())
st.dataframe(display_df, use_container_width=True)

st.download_button(
    label="⬇️ Baixar dados filtrados em CSV",
    data=display_df.to_csv(index=False, sep=";").encode("utf-8-sig"),
    file_name="saneamento_brasil_gold.csv",
    mime="text/csv",
)
