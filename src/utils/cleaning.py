from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Iterable

import pandas as pd

VALID_UF = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA",
    "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN",
    "RS", "RO", "RR", "SC", "SP", "SE", "TO",
}

NULL_TOKENS = {
    "",
    " ",
    "-",
    "--",
    "---",
    "NA",
    "N/A",
    "N/A.",
    "n/a",
    "null",
    "NULL",
    "nan",
    "NaN",
    "None",
    "NONE",
    "?",
    ".",
}

IBGE_COLUMN_ALIASES = (
    "codigo_ibge",
    "cod_ibge",
    "ibge",
    "cod_municipio",
    "codigo_municipio",
    "id_municipio",
    "cd_ibge",
)

UF_COLUMN_ALIASES = (
    "sigla_uf",
    "uf",
    "sigla_estado",
    "sg_uf",
    "estado_uf",
)

MUNICIPIO_COLUMN_ALIASES = (
    "nome_municipio",
    "municipio",
    "nm_municipio",
    "nome_do_municipio",
    "descricao_municipio",
)

METADATA_COLUMNS = {"fonte", "arquivo_origem", "dt_ingestao", "dt_transformacao"}


def transformation_timestamp() -> pd.Timestamp:
    return pd.Timestamp(datetime.now(timezone.utc))


def normalize_nulls(df: pd.DataFrame) -> pd.DataFrame:
    cleaned = df.copy()
    object_columns = cleaned.select_dtypes(include=["object", "string"]).columns

    for column in object_columns:
        series = cleaned[column].astype("string")
        stripped = series.str.strip()
        cleaned[column] = stripped.where(~stripped.isin(NULL_TOKENS), pd.NA)

    return cleaned


def clean_text(series: pd.Series) -> pd.Series:
    as_string = series.astype("string")
    cleaned = as_string.str.strip()
    cleaned = cleaned.str.replace(r"\s+", " ", regex=True)
    cleaned = cleaned.where(~cleaned.isin(NULL_TOKENS), pd.NA)
    return cleaned


def standardize_codigo_ibge(series: pd.Series, digits: int = 7) -> pd.Series:
    normalized = series.astype("string").str.strip()
    normalized = normalized.str.replace(r"\.0$", "", regex=True)
    normalized = normalized.str.replace(r"\D", "", regex=True)
    normalized = normalized.where(normalized.notna() & (normalized != ""), pd.NA)

    length = normalized.str.len()
    normalized = normalized.where(length <= digits, pd.NA)
    normalized = normalized.where(length >= digits - 1, pd.NA)
    normalized = normalized.str.zfill(digits)
    return normalized.astype("Int64")


def standardize_sigla(series: pd.Series) -> pd.Series:
    normalized = series.astype("string").str.strip().str.upper()
    normalized = normalized.where(~normalized.isin(NULL_TOKENS), pd.NA)
    return normalized


def standardize_uf(series: pd.Series) -> pd.Series:
    normalized = series.astype("string").str.strip().str.upper()
    normalized = normalized.where(normalized.isin(VALID_UF), pd.NA)
    return normalized


def find_column(columns: Iterable[str], aliases: tuple[str, ...]) -> str | None:
    column_set = set(columns)
    for alias in aliases:
        if alias in column_set:
            return alias
    return None


def cast_integer_columns(df: pd.DataFrame, columns: Iterable[str]) -> pd.DataFrame:
    casted = df.copy()
    for column in columns:
        if column not in casted.columns:
            continue
        casted[column] = pd.to_numeric(casted[column], errors="coerce").astype("Int64")
    return casted


def infer_numeric_columns(df: pd.DataFrame) -> pd.DataFrame:
    converted = df.copy()

    for column in converted.columns:
        if column in METADATA_COLUMNS:
            continue
        if pd.api.types.is_numeric_dtype(converted[column]):
            if str(converted[column].dtype) == "float64":
                converted[column] = converted[column].astype("Float64")
            continue

        if not (
            pd.api.types.is_object_dtype(converted[column])
            or pd.api.types.is_string_dtype(converted[column])
        ):
            continue

        numeric = pd.to_numeric(converted[column], errors="coerce")
        non_null = converted[column].notna().sum()
        if non_null == 0:
            continue

        parsed_ratio = numeric.notna().sum() / non_null
        if parsed_ratio >= 0.9:
            if (numeric.dropna() % 1 == 0).all():
                converted[column] = numeric.astype("Int64")
            else:
                converted[column] = numeric.astype("Float64")

    return converted


def apply_geography_standardization(df: pd.DataFrame) -> pd.DataFrame:
    standardized = df.copy()

    ibge_column = find_column(standardized.columns, IBGE_COLUMN_ALIASES)
    if ibge_column:
        standardized[ibge_column] = standardize_codigo_ibge(standardized[ibge_column])

    uf_column = find_column(standardized.columns, UF_COLUMN_ALIASES)
    if uf_column:
        standardized[uf_column] = standardize_uf(standardized[uf_column])

    municipio_column = find_column(standardized.columns, MUNICIPIO_COLUMN_ALIASES)
    if municipio_column:
        standardized[municipio_column] = clean_text(standardized[municipio_column])

    return standardized
