"""
Testes para o módulo de validação de qualidade de dados.
"""

from __future__ import annotations

import pandas as pd
import pytest

from src.quality.validators import (
    ValidationReport,
    validate_bronze,
    validate_gold,
    validate_silver,
)


# ---------------------------------------------------------------------------
# ValidationReport
# ---------------------------------------------------------------------------

class TestValidationReport:
    def test_passed_sem_erros(self):
        report = ValidationReport(dataset_name="teste", total_rows=100)
        assert report.passed is True

    def test_falha_com_erro(self):
        report = ValidationReport(dataset_name="teste", total_rows=100)
        report.add_error("Coluna obrigatória ausente")
        assert report.passed is False

    def test_warning_nao_falha(self):
        report = ValidationReport(dataset_name="teste", total_rows=100)
        report.add_warning("Muitos nulos na coluna X")
        assert report.passed is True

    def test_print_summary_sem_crash(self, capsys):
        report = ValidationReport(dataset_name="gold", total_rows=500)
        report.add_warning("Aviso de teste")
        report.print_summary()
        captured = capsys.readouterr()
        assert "gold" in captured.out


# ---------------------------------------------------------------------------
# validate_bronze
# ---------------------------------------------------------------------------

class TestValidateBronze:
    def _bronze_df(self) -> pd.DataFrame:
        return pd.DataFrame({
            "cod_ibge": ["1234567", "7654321"],
            "municipio": ["São Paulo", "Campinas"],
            "iag0001": ["95,5", "88,2"],
            "fonte": ["SINISA - SNIS", "SINISA - SNIS"],
            "dt_ingestao": pd.to_datetime(["2024-01-01", "2024-01-01"]),
        })

    def test_dataframe_valido_passa(self):
        report = validate_bronze(self._bronze_df())
        assert report.passed

    def test_dataframe_vazio_falha(self):
        report = validate_bronze(pd.DataFrame())
        assert not report.passed
        assert any("vazio" in e.lower() for e in report.errors)


# ---------------------------------------------------------------------------
# validate_silver
# ---------------------------------------------------------------------------

class TestValidateSilver:
    def _silver_df(self) -> pd.DataFrame:
        return pd.DataFrame({
            "codigo_ibge": ["1234567", "7654321"],
            "municipio": ["São Paulo", "Campinas"],
            "uf": ["SP", "SP"],
            "iag0001": [95.5, 88.2],
            "fonte": ["SINISA - SNIS", "SINISA - SNIS"],
            "dt_ingestao": pd.to_datetime(["2024-01-01", "2024-01-01"]),
            "dt_transformacao": pd.to_datetime(["2024-01-01", "2024-01-01"]),
        })

    def test_dataframe_valido_passa(self):
        report = validate_silver(self._silver_df())
        assert report.passed

    def test_uf_invalida_gera_aviso(self):
        df = self._silver_df()
        df["uf"] = ["ZZ", "XX"]  # UFs inválidas
        report = validate_silver(df)
        assert any("uf" in w.lower() for w in report.warnings)

    def test_codigo_ibge_invalido_gera_aviso(self):
        df = self._silver_df()
        df["codigo_ibge"] = ["123", "456"]  # Menos de 7 dígitos
        report = validate_silver(df)
        assert any("ibge" in w.lower() for w in report.warnings)


# ---------------------------------------------------------------------------
# validate_gold
# ---------------------------------------------------------------------------

class TestValidateGold:
    def _gold_df(self) -> pd.DataFrame:
        return pd.DataFrame({
            "codigo_ibge": ["3550308", "3509502"],
            "municipio": ["São Paulo", "Campinas"],
            "uf": ["SP", "SP"],
            "nome_municipio": ["São Paulo", "Campinas"],
            "iag0001": [95.5, 88.2],
            "iag0002": [98.1, 92.0],
            "iag0003": [45.0, 60.0],
        })

    def test_dataframe_valido_passa(self):
        report = validate_gold(self._gold_df())
        assert report.passed

    def test_dataframe_vazio_falha(self):
        report = validate_gold(pd.DataFrame())
        assert not report.passed

    def test_indicador_acima_100_gera_aviso(self):
        df = self._gold_df()
        df["iag0001"] = [105.0, 110.0]  # Acima de 100%
        report = validate_gold(df)
        assert any("iag0001" in w for w in report.warnings)

    def test_indicador_negativo_gera_aviso(self):
        df = self._gold_df()
        df["iag0001"] = [-5.0, 88.0]
        report = validate_gold(df)
        assert any("iag0001" in w for w in report.warnings)

    def test_sem_correspondencia_ibge_gera_aviso(self):
        df = self._gold_df()
        df["nome_municipio"] = [None, None]
        report = validate_gold(df)
        assert any("ibge" in w.lower() for w in report.warnings)

    def test_duplicatas_geram_aviso(self):
        df = self._gold_df()
        df_dup = pd.concat([df, df], ignore_index=True)
        report = validate_gold(df_dup)
        assert any("duplicad" in w.lower() for w in report.warnings)
