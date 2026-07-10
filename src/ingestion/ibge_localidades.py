"""
Ingestão de localidades (regiões, estados e municípios) via API pública do IBGE.

A API do IBGE é gratuita e não requer autenticação.
Documentação oficial: https://servicodados.ibge.gov.br/docs/localidades
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import requests

from src.utils.io import save_parquet
from src.utils.paths import BRONZE_DIR

logger = logging.getLogger(__name__)

BASE_URL = "https://servicodados.ibge.gov.br/api/v1/localidades"
FONTE = "IBGE - API Localidades"
TIMEOUT_SECONDS = 60


def _fetch(endpoint: str) -> list[dict[str, Any]]:
    """Faz requisição GET à API do IBGE e retorna a lista de registros."""
    url = f"{BASE_URL}/{endpoint}"
    logger.info("Requisitando: %s", url)
    response = requests.get(url, timeout=TIMEOUT_SECONDS)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, list):
        raise ValueError(f"Resposta inesperada da API IBGE em {url}")
    return payload


def _ingestion_timestamp() -> pd.Timestamp:
    return pd.Timestamp(datetime.now(timezone.utc))


def normalize_regioes(records: list[dict[str, Any]]) -> pd.DataFrame:
    rows = [
        {
            "id_regiao": record["id"],
            "sigla_regiao": record["sigla"],
            "nome_regiao": record["nome"],
        }
        for record in records
    ]
    df = pd.DataFrame(rows)
    df["fonte"] = FONTE
    df["dt_ingestao"] = _ingestion_timestamp()
    return df


def normalize_estados(records: list[dict[str, Any]]) -> pd.DataFrame:
    rows = [
        {
            "id_estado": record["id"],
            "sigla_estado": record["sigla"],
            "nome_estado": record["nome"],
            "id_regiao": record["regiao"]["id"],
            "sigla_regiao": record["regiao"]["sigla"],
            "nome_regiao": record["regiao"]["nome"],
        }
        for record in records
    ]
    df = pd.DataFrame(rows)
    df["fonte"] = FONTE
    df["dt_ingestao"] = _ingestion_timestamp()
    return df


def normalize_municipios(records: list[dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for record in records:
        regiao_imediata = record["regiao-imediata"]
        regiao_intermediaria = regiao_imediata["regiao-intermediaria"]
        uf = regiao_intermediaria["UF"]
        regiao = uf["regiao"]

        microrregiao = record.get("microrregiao")
        if microrregiao:
            mesorregiao = microrregiao["mesorregiao"]
            id_microrregiao = microrregiao["id"]
            nome_microrregiao = microrregiao["nome"]
            id_mesorregiao = mesorregiao["id"]
            nome_mesorregiao = mesorregiao["nome"]
        else:
            id_microrregiao = None
            nome_microrregiao = None
            id_mesorregiao = None
            nome_mesorregiao = None

        rows.append(
            {
                "id_municipio": record["id"],
                "nome_municipio": record["nome"],
                "id_microrregiao": id_microrregiao,
                "nome_microrregiao": nome_microrregiao,
                "id_mesorregiao": id_mesorregiao,
                "nome_mesorregiao": nome_mesorregiao,
                "id_estado": uf["id"],
                "sigla_estado": uf["sigla"],
                "nome_estado": uf["nome"],
                "id_regiao": regiao["id"],
                "sigla_regiao": regiao["sigla"],
                "nome_regiao": regiao["nome"],
                "id_regiao_imediata": regiao_imediata["id"],
                "nome_regiao_imediata": regiao_imediata["nome"],
                "id_regiao_intermediaria": regiao_intermediaria["id"],
                "nome_regiao_intermediaria": regiao_intermediaria["nome"],
            }
        )

    df = pd.DataFrame(rows)
    df["fonte"] = FONTE
    df["dt_ingestao"] = _ingestion_timestamp()
    return df


def ingest_localidades(output_dir: Path | None = None) -> dict[str, Path]:
    """
    Ingere regiões, estados e municípios do IBGE e salva na camada Bronze.

    Returns:
        Dicionário {nome_dataset: caminho_parquet}
    """
    target_dir = output_dir or BRONZE_DIR

    logger.info("Baixando regiões do IBGE...")
    regioes = normalize_regioes(_fetch("regioes"))
    path_regioes = save_parquet(regioes, target_dir / "ibge_regioes.parquet")
    logger.info("Regiões salvas: %s (%s registros)", path_regioes, len(regioes))

    logger.info("Baixando estados do IBGE...")
    estados = normalize_estados(_fetch("estados"))
    path_estados = save_parquet(estados, target_dir / "ibge_estados.parquet")
    logger.info("Estados salvos: %s (%s registros)", path_estados, len(estados))

    logger.info("Baixando municípios do IBGE (pode demorar alguns segundos)...")
    municipios = normalize_municipios(_fetch("municipios"))
    path_municipios = save_parquet(municipios, target_dir / "ibge_municipios.parquet")
    logger.info("Municípios salvos: %s (%s registros)", path_municipios, len(municipios))

    return {
        "regioes": path_regioes,
        "estados": path_estados,
        "municipios": path_municipios,
    }


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    paths = ingest_localidades()
    for dataset, path in paths.items():
        print(f"{dataset}: {path}")


if __name__ == "__main__":
    main()
