"""
Constrói a camada Gold integrando dados do IBGE e SINISA.

A tabela Gold é o produto final do pipeline: dados territoriais do IBGE
cruzados com indicadores de abastecimento de água do SINISA, prontos para
consumo em dashboards e análises.

Arquivo gerado: data/gold/infra_municipios_agua.parquet
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from src.quality.validators import validate_gold
from src.utils.paths import GOLD_AGUA_PATH, SILVER_DIR, SINISA_SILVER_DIR

logger = logging.getLogger(__name__)

IBGE_MUNICIPIOS_PATH = SILVER_DIR / "ibge_municipios.parquet"
SINISA_AGUA_GLOB = "sinisa_*.parquet"


def find_column(df: pd.DataFrame, candidates: list[str]) -> str:
    """Encontra a primeira coluna disponível dentre as candidatas."""
    for col in candidates:
        if col in df.columns:
            return col
    raise ValueError(
        f"Nenhuma coluna encontrada entre as opções: {candidates}. "
        f"Colunas disponíveis: {df.columns.tolist()}"
    )


def to_numeric_br(value: object) -> float | None:
    """
    Converte valores numéricos no formato brasileiro para float.

    Trata casos como:
    - '60,35'     → 60.35
    - '60.35'     → 60.35
    - '1.234,56'  → 1234.56
    - 'Não calculado' → None
    """
    if pd.isna(value):
        return pd.NA

    if isinstance(value, (int, float)):
        return float(value)

    value = str(value).strip()
    if not value:
        return pd.NA

    value_lower = value.lower()
    invalid_tokens = {"nao calculado", "não calculado", "nan", "none", "-"}
    if value_lower in invalid_tokens or "não calculado" in value_lower:
        return pd.NA

    # Formato BR: 1.234,56 → remove ponto de milhar, troca vírgula por ponto
    if "," in value:
        value = value.replace(".", "").replace(",", ".")

    try:
        return float(value)
    except ValueError:
        return pd.NA


def _load_sinisa_silver() -> pd.DataFrame:
    """Carrega e concatena todos os arquivos Silver do SINISA."""
    files = sorted(SINISA_SILVER_DIR.glob(SINISA_AGUA_GLOB))
    if not files:
        raise FileNotFoundError(
            f"Nenhum arquivo Silver SINISA encontrado em {SINISA_SILVER_DIR}. "
            "Execute o pipeline Bronze→Silver antes de gerar a camada Gold."
        )

    frames = [pd.read_parquet(f) for f in files]
    df = pd.concat(frames, ignore_index=True)
    logger.info("SINISA Silver carregado: %s registros de %s arquivo(s)", len(df), len(files))
    return df


def build_gold_infra_municipios_agua(output_path: Path | None = None) -> Path:
    """
    Integra IBGE + SINISA e salva a tabela Gold de municípios × água.

    Inclui validação de qualidade dos dados ao final.

    Returns:
        Caminho do arquivo Parquet Gold gerado.
    """
    target_path = output_path or GOLD_AGUA_PATH

    # --- Carrega Silver do IBGE ---
    logger.info("Lendo Silver do IBGE: %s", IBGE_MUNICIPIOS_PATH)
    if not IBGE_MUNICIPIOS_PATH.exists():
        raise FileNotFoundError(
            f"Silver IBGE não encontrado: {IBGE_MUNICIPIOS_PATH}. "
            "Execute 'python -m src.transformations.bronze_to_silver' primeiro."
        )
    ibge = pd.read_parquet(IBGE_MUNICIPIOS_PATH)

    # --- Carrega Silver do SINISA ---
    sinisa = _load_sinisa_silver()

    # --- Identifica colunas de junção ---
    ibge_key = find_column(ibge, ["id_municipio", "codigo_ibge", "cod_ibge"])
    sinisa_key = find_column(sinisa, ["cod_ibge", "codigo_ibge", "codigo_do_ibge"])

    logger.info("Chave IBGE: '%s' | Chave SINISA: '%s'", ibge_key, sinisa_key)

    ibge = ibge.copy()
    sinisa = sinisa.copy()
    ibge["codigo_ibge"] = ibge[ibge_key].astype(str).str.strip()
    sinisa["codigo_ibge"] = sinisa[sinisa_key].astype(str).str.strip()

    # --- Seleciona colunas SINISA para o Gold ---
    sinisa_cols_priority = [
        "codigo_ibge", "macrorregiao", "municipio", "uf", "capital", "rm_ride",
        "natureza_juridica", "abrangencia", "nome_do_prestador", "sigla",
        "iag0001", "iag0002", "iag0003", "iag0004", "iag0005", "iag0006",
        "fonte", "arquivo_origem", "dt_ingestao",
    ]
    sinisa_cols = [c for c in sinisa_cols_priority if c in sinisa.columns]
    sinisa_gold = sinisa[sinisa_cols].copy()

    # Converte indicadores percentuais para float
    for col in ["iag0001", "iag0002", "iag0003", "iag0004", "iag0005", "iag0006"]:
        if col in sinisa_gold.columns:
            sinisa_gold[col] = sinisa_gold[col].apply(to_numeric_br)

    # --- Seleciona colunas IBGE para o Gold ---
    ibge_cols_priority = [
        "codigo_ibge", "nome_municipio",
        "id_microrregiao", "nome_microrregiao",
        "id_mesorregiao", "nome_mesorregiao",
        "id_estado", "sigla_estado", "nome_estado",
        "id_regiao", "sigla_regiao", "nome_regiao",
    ]
    ibge_cols = [c for c in ibge_cols_priority if c in ibge.columns]
    ibge_gold = ibge[ibge_cols].drop_duplicates(subset=["codigo_ibge"])

    # --- Integração SINISA × IBGE ---
    gold = sinisa_gold.merge(ibge_gold, on="codigo_ibge", how="left", suffixes=("_sinisa", "_ibge"))
    gold["ano_referencia"] = 2024

    # --- Validação de qualidade ---
    report = validate_gold(gold, dataset_name="gold_infra_municipios_agua")
    report.print_summary()

    if not report.passed:
        logger.error("Camada Gold gerada com erros de qualidade. Verifique o relatório acima.")

    # --- Salva Gold ---
    target_path.parent.mkdir(parents=True, exist_ok=True)
    gold.to_parquet(target_path, index=False)

    logger.info(
        "Gold salvo em %s (%s registros, %s colunas)",
        target_path, len(gold), len(gold.columns),
    )
    return target_path


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    path = build_gold_infra_municipios_agua()
    print(f"\nTabela Gold criada: {path}")


if __name__ == "__main__":
    main()
