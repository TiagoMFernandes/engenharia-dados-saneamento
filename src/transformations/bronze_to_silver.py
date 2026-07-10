"""
Orquestra as transformações Bronze → Silver para todas as fontes do pipeline.

Executa em sequência: IBGE localidades → SINISA indicadores.
"""

from __future__ import annotations

import logging
from pathlib import Path

from src.transformations.ibge_localidades import transform_ibge_localidades
from src.transformations.sinisa import transform_sinisa

logger = logging.getLogger(__name__)


def run_all_transformations() -> dict[str, dict[str, Path]]:
    """
    Executa todas as transformações Bronze → Silver disponíveis.

    Returns:
        Dicionário {fonte: {dataset: caminho_parquet}}
    """
    logger.info("Iniciando transformações bronze -> silver")

    results = {
        "ibge": transform_ibge_localidades(),
        "sinisa": transform_sinisa(),
    }

    total = sum(len(paths) for paths in results.values())
    logger.info("Transformações concluídas: %s dataset(s) gerado(s)", total)
    return results


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    results = run_all_transformations()

    for source, paths in results.items():
        if not paths:
            print(f"{source}: nenhum dataset transformado")
            continue
        for name, path in paths.items():
            print(f"{source}/{name}: {path}")


if __name__ == "__main__":
    main()
