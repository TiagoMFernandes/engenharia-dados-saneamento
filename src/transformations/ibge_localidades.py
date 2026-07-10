"""
Transformação dos dados IBGE da camada Bronze para Silver.

Aplica limpeza, padronização de tipos e enriquecimento geográfico.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from src.utils.cleaning import (
    cast_integer_columns,
    clean_text,
    normalize_nulls,
    standardize_codigo_ibge,
    standardize_sigla,
    standardize_uf,
    transformation_timestamp,
)
from src.utils.io import save_parquet
from src.utils.paths import BRONZE_DIR, SILVER_DIR

logger = logging.getLogger(__name__)

INTEGER_COLUMNS = {
    "regioes": ["id_regiao"],
    "estados": ["id_estado", "id_regiao"],
    "municipios": [
        "id_municipio",
        "id_microrregiao",
        "id_mesorregiao",
        "id_estado",
        "id_regiao",
        "id_regiao_imediata",
        "id_regiao_intermediaria",
    ],
}

TEXT_COLUMNS = {
    "regioes": ["sigla_regiao", "nome_regiao"],
    "estados": ["sigla_estado", "nome_estado", "sigla_regiao", "nome_regiao"],
    "municipios": [
        "nome_municipio",
        "nome_microrregiao",
        "nome_mesorregiao",
        "sigla_estado",
        "nome_estado",
        "sigla_regiao",
        "nome_regiao",
        "nome_regiao_imediata",
        "nome_regiao_intermediaria",
    ],
}


def _clean_text_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    cleaned = df.copy()
    for column in columns:
        if column in cleaned.columns:
            cleaned[column] = clean_text(cleaned[column])
    return cleaned


def transform_regioes(df: pd.DataFrame) -> pd.DataFrame:
    cleaned = normalize_nulls(df)
    cleaned = cast_integer_columns(cleaned, INTEGER_COLUMNS["regioes"])
    cleaned = _clean_text_columns(cleaned, TEXT_COLUMNS["regioes"])
    cleaned["sigla_regiao"] = standardize_sigla(cleaned["sigla_regiao"])
    cleaned["dt_transformacao"] = transformation_timestamp()
    return cleaned


def transform_estados(df: pd.DataFrame) -> pd.DataFrame:
    cleaned = normalize_nulls(df)
    cleaned = cast_integer_columns(cleaned, INTEGER_COLUMNS["estados"])
    cleaned = _clean_text_columns(cleaned, TEXT_COLUMNS["estados"])
    cleaned["sigla_estado"] = standardize_uf(cleaned["sigla_estado"])
    cleaned["sigla_regiao"] = standardize_sigla(cleaned["sigla_regiao"])
    cleaned["dt_transformacao"] = transformation_timestamp()
    return cleaned


def transform_municipios(df: pd.DataFrame) -> pd.DataFrame:
    cleaned = normalize_nulls(df)
    cleaned = cast_integer_columns(cleaned, INTEGER_COLUMNS["municipios"])
    cleaned = _clean_text_columns(cleaned, TEXT_COLUMNS["municipios"])
    cleaned["sigla_estado"] = standardize_uf(cleaned["sigla_estado"])
    cleaned["sigla_regiao"] = standardize_sigla(cleaned["sigla_regiao"])
    cleaned["codigo_ibge"] = standardize_codigo_ibge(cleaned["id_municipio"])
    cleaned["sigla_uf"] = cleaned["sigla_estado"]
    cleaned["dt_transformacao"] = transformation_timestamp()
    return cleaned


def transform_ibge_localidades(
    input_dir: Path | None = None,
    output_dir: Path | None = None,
) -> dict[str, Path]:
    """
    Transforma os arquivos Bronze do IBGE para a camada Silver.

    Returns:
        Dicionário {nome_dataset: caminho_parquet_silver}
    """
    source_dir = input_dir or BRONZE_DIR
    target_dir = output_dir or SILVER_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    datasets = {
        "regioes": ("ibge_regioes.parquet", transform_regioes),
        "estados": ("ibge_estados.parquet", transform_estados),
        "municipios": ("ibge_municipios.parquet", transform_municipios),
    }

    saved_paths: dict[str, Path] = {}
    for name, (filename, transformer) in datasets.items():
        source_path = source_dir / filename
        if not source_path.exists():
            logger.warning("Arquivo bronze não encontrado: %s", source_path)
            continue

        logger.info("Transformando %s...", filename)
        bronze_df = pd.read_parquet(source_path)
        silver_df = transformer(bronze_df)
        output_path = save_parquet(silver_df, target_dir / filename)
        saved_paths[name] = output_path
        logger.info(
            "Silver salvo: %s (%s registros, %s colunas)",
            output_path, len(silver_df), len(silver_df.columns),
        )

    return saved_paths
