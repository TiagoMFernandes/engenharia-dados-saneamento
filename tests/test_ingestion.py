"""
Testes para os módulos de ingestão (IBGE e SINISA).
"""

from __future__ import annotations

from pathlib import Path
import re

import pandas as pd
import pytest

from src.ingestion.sinisa import (
    _normalize_text,
    list_input_files,
    normalize_dataframe,
)
from src.utils.columns import standardize_column_name, standardize_column_names


# ---------------------------------------------------------------------------
# Utilitários de colunas
# ---------------------------------------------------------------------------

class TestStandardizeColumnName:
    def test_remove_acentos(self):
        assert standardize_column_name("Município") == "municipio"

    def test_converte_espacos_para_underscore(self):
        assert standardize_column_name("nome do municipio") == "nome_do_municipio"

    def test_remove_caracteres_especiais(self):
        assert standardize_column_name("Código IBGE (%)") == "codigo_ibge"

    def test_coluna_sem_nome(self):
        assert standardize_column_name(None) == "coluna_sem_nome"

    def test_coluna_nan_float(self):
        assert standardize_column_name(float("nan")) == "coluna_sem_nome"

    def test_tudo_maiusculo(self):
        assert standardize_column_name("IAG0001") == "iag0001"


class TestStandardizeColumnNames:
    def test_desduplicacao(self):
        names = ["coluna", "coluna", "coluna"]
        result = standardize_column_names(names)
        assert result == ["coluna", "coluna_2", "coluna_3"]

    def test_lista_vazia(self):
        assert standardize_column_names([]) == []


# ---------------------------------------------------------------------------
# Utilitário de normalização de texto (header detection)
# ---------------------------------------------------------------------------

class TestNormalizeText:
    def test_remove_acentos(self):
        assert _normalize_text("Município") == "municipio"

    def test_espacos_viram_underscore(self):
        assert _normalize_text("cod IBGE") == "cod_ibge"

    def test_valor_nulo(self):
        assert _normalize_text(None) == ""

    def test_valor_nan(self):
        assert _normalize_text(float("nan")) == ""

    def test_codigo_indicador(self):
        result = _normalize_text("IAG0001")
        assert re.fullmatch(r"[a-z]{3}\d{4}", result)


# ---------------------------------------------------------------------------
# Listagem de arquivos
# ---------------------------------------------------------------------------

class TestListInputFiles:
    def test_pasta_inexistente_retorna_lista_vazia(self, tmp_path):
        result = list_input_files(tmp_path / "nao_existe")
        assert result == []

    def test_retorna_apenas_extensoes_suportadas(self, tmp_path):
        (tmp_path / "dados.xlsx").write_text("")
        (tmp_path / "dados.csv").write_text("")
        (tmp_path / "readme.txt").write_text("")
        (tmp_path / "imagem.png").write_bytes(b"")

        files = list_input_files(tmp_path)
        names = [f.name for f in files]

        assert "dados.xlsx" in names
        assert "dados.csv" in names
        assert "readme.txt" not in names
        assert "imagem.png" not in names

    def test_retorna_lista_vazia_se_pasta_vazia(self, tmp_path):
        assert list_input_files(tmp_path) == []


# ---------------------------------------------------------------------------
# Normalização de DataFrame
# ---------------------------------------------------------------------------

class TestNormalizeDataframe:
    def _sample_df(self) -> pd.DataFrame:
        return pd.DataFrame({
            "cod_IBGE": ["1234567", "7654321"],
            "Município": ["São Paulo", "Rio de Janeiro"],
            "IAG0001": ["95,5", "88,2"],
        })

    def test_adiciona_metadados(self):
        df = self._sample_df()
        result = normalize_dataframe(df, Path("arquivo_teste.xlsx"))

        assert "fonte" in result.columns
        assert "arquivo_origem" in result.columns
        assert "dt_ingestao" in result.columns

    def test_nome_arquivo_origem_correto(self):
        df = self._sample_df()
        result = normalize_dataframe(df, Path("arquivo_teste.xlsx"))
        assert result["arquivo_origem"].iloc[0] == "arquivo_teste.xlsx"

    def test_colunas_padronizadas(self):
        df = self._sample_df()
        result = normalize_dataframe(df, Path("teste.xlsx"))
        assert "cod_ibge" in result.columns
        assert "municipio" in result.columns
        assert "iag0001" in result.columns
