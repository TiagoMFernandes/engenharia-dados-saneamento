"""
Interface de consulta SQL sobre os dados via DuckDB.

DuckDB permite executar SQL diretamente em arquivos Parquet, sem necessidade
de carregar tudo na memória. É ideal para análises exploratórias na camada Gold.

Pré-requisito: pip install duckdb

Exemplos de uso:
    from src.query.duck import query_gold, top_municipios_agua

    # Consulta livre
    df = query_gold("SELECT uf, AVG(iag0001) as media FROM gold GROUP BY uf")

    # Consulta pronta
    df = top_municipios_agua(uf="SP", limit=10)
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from src.utils.paths import GOLD_AGUA_PATH

logger = logging.getLogger(__name__)


def _get_duckdb():
    """Importa DuckDB com mensagem amigável se não estiver instalado."""
    try:
        import duckdb
        return duckdb
    except ImportError:
        raise ImportError(
            "DuckDB não está instalado. Execute: pip install duckdb\n"
            "Ou instale todas as dependências: pip install -r requirements.txt"
        )


def query_gold(sql: str, gold_path: Path | None = None) -> pd.DataFrame:
    """
    Executa uma consulta SQL sobre a camada Gold.

    A tabela está disponível como 'gold' na query.

    Args:
        sql: Query SQL. Use 'gold' como nome da tabela.
             Ex: "SELECT uf, COUNT(*) as total FROM gold GROUP BY uf"
        gold_path: Caminho alternativo para o arquivo Parquet Gold.

    Returns:
        DataFrame com o resultado da consulta.

    Example:
        df = query_gold("SELECT * FROM gold WHERE uf = 'SP' LIMIT 10")
    """
    duckdb = _get_duckdb()
    path = gold_path or GOLD_AGUA_PATH

    if not path.exists():
        raise FileNotFoundError(
            f"Arquivo Gold não encontrado: {path}\n"
            "Execute o pipeline completo antes de fazer consultas."
        )

    # DuckDB lê o Parquet diretamente — sem carregar tudo na memória
    conn = duckdb.connect()
    conn.execute(f"CREATE VIEW gold AS SELECT * FROM read_parquet('{path}')")

    logger.info("Executando query: %s", sql[:100])
    result = conn.execute(sql).df()
    conn.close()

    return result


def top_municipios_agua(
    indicador: str = "iag0001",
    uf: str | None = None,
    ascending: bool = False,
    limit: int = 20,
) -> pd.DataFrame:
    """
    Retorna ranking de municípios por indicador de abastecimento de água.

    Args:
        indicador: Código do indicador SINISA (padrão: iag0001 = atendimento total).
        uf: Filtrar por UF (ex: 'SP', 'MG'). None retorna todos os estados.
        ascending: True para menor valor primeiro, False para maior.
        limit: Número máximo de registros retornados.

    Returns:
        DataFrame com colunas: municipio, uf, nome_prestador, indicador.
    """
    order = "ASC" if ascending else "DESC"
    uf_filter = f"AND uf = '{uf.upper()}'" if uf else ""

    sql = f"""
        SELECT
            codigo_ibge,
            municipio,
            uf,
            nome_do_prestador,
            {indicador}
        FROM gold
        WHERE {indicador} IS NOT NULL
          {uf_filter}
        ORDER BY {indicador} {order}
        LIMIT {limit}
    """
    return query_gold(sql)


def resumo_por_uf(indicador: str = "iag0001") -> pd.DataFrame:
    """
    Retorna média, mínimo, máximo e total de municípios por UF.

    Args:
        indicador: Código do indicador SINISA.

    Returns:
        DataFrame agregado por UF.
    """
    sql = f"""
        SELECT
            uf,
            COUNT(DISTINCT codigo_ibge)        AS municipios,
            ROUND(AVG({indicador}), 2)         AS media,
            ROUND(MIN({indicador}), 2)         AS minimo,
            ROUND(MAX({indicador}), 2)         AS maximo
        FROM gold
        WHERE {indicador} IS NOT NULL
        GROUP BY uf
        ORDER BY media DESC
    """
    return query_gold(sql)


def municipios_sem_atendimento(threshold: float = 50.0) -> pd.DataFrame:
    """
    Retorna municípios com atendimento total de água abaixo do limite.

    Args:
        threshold: Percentual mínimo (padrão: 50%). Municípios abaixo disso são retornados.

    Returns:
        DataFrame com municípios em situação crítica.
    """
    sql = f"""
        SELECT
            codigo_ibge,
            municipio,
            uf,
            nome_do_prestador,
            iag0001  AS atendimento_total_pct
        FROM gold
        WHERE iag0001 IS NOT NULL
          AND iag0001 < {threshold}
        ORDER BY iag0001 ASC
    """
    return query_gold(sql)


def main() -> None:
    """Demonstração das consultas disponíveis."""
    import sys

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    print("\n--- Top 10 municípios com MAIOR atendimento de água ---")
    try:
        df = top_municipios_agua(limit=10)
        print(df.to_string(index=False))
    except FileNotFoundError as e:
        print(f"Erro: {e}")
        sys.exit(1)

    print("\n--- Resumo por UF (média de atendimento total) ---")
    df_uf = resumo_por_uf()
    print(df_uf.to_string(index=False))

    print("\n--- Municípios com menos de 50% de atendimento ---")
    df_criticos = municipios_sem_atendimento(threshold=50.0)
    print(f"Total: {len(df_criticos)} municípios")
    print(df_criticos.head(10).to_string(index=False))


if __name__ == "__main__":
    main()
