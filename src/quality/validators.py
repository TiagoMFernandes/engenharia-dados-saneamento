"""
Módulo de validação de qualidade de dados.

Implementa verificações que garantem a integridade dos dados em cada camada
do pipeline (Bronze, Silver, Gold). Retorna um relatório estruturado com
alertas e erros encontrados.

Uso:
    from src.quality.validators import validate_gold
    report = validate_gold(df)
    report.print_summary()
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import pandas as pd

logger = logging.getLogger(__name__)

VALID_UF = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA",
    "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN",
    "RS", "RO", "RR", "SC", "SP", "SE", "TO",
}

# Indicadores de atendimento: esperados entre 0 e 100 (percentual)
PERCENT_INDICATORS = {"iag0001", "iag0002", "iag0003", "iag0004", "iag0005", "iag0006"}


@dataclass
class ValidationReport:
    """Relatório de qualidade gerado após validação de um DataFrame."""

    dataset_name: str
    total_rows: int
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """Retorna True se não houver erros (avisos são permitidos)."""
        return len(self.errors) == 0

    def add_error(self, message: str) -> None:
        self.errors.append(message)
        logger.error("[QUALIDADE] %s: %s", self.dataset_name, message)

    def add_warning(self, message: str) -> None:
        self.warnings.append(message)
        logger.warning("[QUALIDADE] %s: %s", self.dataset_name, message)

    def print_summary(self) -> None:
        status = "PASSOU" if self.passed else "FALHOU"
        print(f"\n{'='*60}")
        print(f"Relatório de Qualidade: {self.dataset_name}")
        print(f"Status: {status} | Total de registros: {self.total_rows:,}")
        if self.errors:
            print(f"\n{len(self.errors)} ERRO(S):")
            for e in self.errors:
                print(f"  ✗ {e}")
        if self.warnings:
            print(f"\n{len(self.warnings)} AVISO(S):")
            for w in self.warnings:
                print(f"  ⚠ {w}")
        if not self.errors and not self.warnings:
            print("  ✓ Nenhum problema encontrado.")
        print("=" * 60)


def _check_nulls(
    df: pd.DataFrame,
    required_columns: list[str],
    report: ValidationReport,
    threshold: float = 0.5,
) -> None:
    """
    Verifica nulos em colunas obrigatórias.
    Gera erro se > threshold (50%) dos valores são nulos.
    """
    for col in required_columns:
        if col not in df.columns:
            report.add_error(f"Coluna obrigatória ausente: '{col}'")
            continue

        null_ratio = df[col].isna().mean()
        if null_ratio > threshold:
            report.add_error(
                f"Coluna '{col}' tem {null_ratio:.1%} de valores nulos "
                f"(limite: {threshold:.0%})"
            )
        elif null_ratio > 0.1:
            report.add_warning(
                f"Coluna '{col}' tem {null_ratio:.1%} de valores nulos"
            )


def _check_duplicates(
    df: pd.DataFrame,
    key_columns: list[str],
    report: ValidationReport,
) -> None:
    """Verifica registros duplicados com base em colunas-chave."""
    existing_keys = [c for c in key_columns if c in df.columns]
    if not existing_keys:
        return

    duplicates = df.duplicated(subset=existing_keys).sum()
    if duplicates > 0:
        report.add_warning(
            f"{duplicates} registros duplicados encontrados "
            f"(chave: {', '.join(existing_keys)})"
        )


def _check_percent_range(
    df: pd.DataFrame,
    columns: set[str],
    report: ValidationReport,
) -> None:
    """
    Verifica se indicadores percentuais estão no intervalo esperado [0, 100].
    Valores fora desse intervalo indicam problema na fonte ou na transformação.
    """
    for col in columns:
        if col not in df.columns:
            continue

        numeric = pd.to_numeric(df[col], errors="coerce")
        out_of_range = numeric[(numeric < 0) | (numeric > 100)].count()

        if out_of_range > 0:
            report.add_warning(
                f"Indicador '{col}' tem {out_of_range} valor(es) fora do intervalo [0, 100]"
            )


def _check_ibge_codes(df: pd.DataFrame, report: ValidationReport) -> None:
    """Verifica se os códigos IBGE têm 7 dígitos (padrão nacional)."""
    col = next(
        (c for c in ["codigo_ibge", "cod_ibge"] if c in df.columns),
        None,
    )
    if col is None:
        return

    codes = df[col].dropna().astype(str)
    invalid = codes[~codes.str.match(r"^\d{7}$")].count()

    if invalid > 0:
        report.add_warning(
            f"{invalid} código(s) IBGE inválidos em '{col}' (esperado: 7 dígitos)"
        )


def _check_uf_values(df: pd.DataFrame, report: ValidationReport) -> None:
    """Verifica se as siglas de UF são válidas."""
    col = next(
        (c for c in ["uf", "sigla_uf", "sigla_estado"] if c in df.columns),
        None,
    )
    if col is None:
        return

    ufs = df[col].dropna().str.upper().unique()
    invalid_ufs = [uf for uf in ufs if uf not in VALID_UF]

    if invalid_ufs:
        report.add_warning(
            f"Siglas de UF inválidas encontradas em '{col}': {invalid_ufs}"
        )


def validate_bronze(df: pd.DataFrame, dataset_name: str = "bronze") -> ValidationReport:
    """Validações básicas para a camada Bronze."""
    report = ValidationReport(dataset_name=dataset_name, total_rows=len(df))

    if len(df) == 0:
        report.add_error("DataFrame vazio — nenhum dado foi ingerido")
        return report

    _check_nulls(df, required_columns=["fonte", "dt_ingestao"], report=report)
    _check_duplicates(df, key_columns=["cod_ibge", "municipio"], report=report)

    return report


def validate_silver(df: pd.DataFrame, dataset_name: str = "silver") -> ValidationReport:
    """Validações intermediárias para a camada Silver."""
    report = ValidationReport(dataset_name=dataset_name, total_rows=len(df))

    if len(df) == 0:
        report.add_error("DataFrame vazio — nenhum dado foi transformado")
        return report

    _check_nulls(
        df,
        required_columns=["fonte", "dt_ingestao", "dt_transformacao"],
        report=report,
    )
    _check_duplicates(df, key_columns=["codigo_ibge", "municipio"], report=report)
    _check_ibge_codes(df, report)
    _check_uf_values(df, report)

    return report


def validate_gold(df: pd.DataFrame, dataset_name: str = "gold") -> ValidationReport:
    """
    Validações completas para a camada Gold.

    Verifica colunas obrigatórias, duplicatas, códigos IBGE,
    UFs válidas e intervalos dos indicadores percentuais.
    """
    report = ValidationReport(dataset_name=dataset_name, total_rows=len(df))

    if len(df) == 0:
        report.add_error("DataFrame vazio — camada Gold não foi gerada")
        return report

    _check_nulls(
        df,
        required_columns=["codigo_ibge", "municipio", "uf"],
        report=report,
    )
    _check_duplicates(df, key_columns=["codigo_ibge"], report=report)
    _check_ibge_codes(df, report)
    _check_uf_values(df, report)
    _check_percent_range(df, PERCENT_INDICATORS, report)

    # Valida integração: municípios sem dados geográficos do IBGE
    if "nome_municipio" in df.columns:
        sem_ibge = df["nome_municipio"].isna().sum()
        if sem_ibge > 0:
            report.add_warning(
                f"{sem_ibge} município(s) sem correspondência na base do IBGE"
            )

    return report
