"""
Testes para os módulos de transformação (limpeza, padronização geográfica).
"""

from __future__ import annotations

import pandas as pd
import pytest

from src.transformations.build_gold import to_numeric_br
from src.utils.cleaning import (
    normalize_nulls,
    standardize_codigo_ibge,
    standardize_uf,
)


# ---------------------------------------------------------------------------
# to_numeric_br (conversão formato brasileiro)
# ---------------------------------------------------------------------------

class TestToNumericBr:
    def test_virgula_decimal(self):
        assert to_numeric_br("60,35") == pytest.approx(60.35)

    def test_ponto_decimal(self):
        assert to_numeric_br("60.35") == pytest.approx(60.35)

    def test_milhar_com_virgula_decimal(self):
        assert to_numeric_br("1.234,56") == pytest.approx(1234.56)

    def test_inteiro_como_float(self):
        assert to_numeric_br(95) == pytest.approx(95.0)

    def test_float_direto(self):
        assert to_numeric_br(88.5) == pytest.approx(88.5)

    def test_nao_calculado_retorna_na(self):
        assert pd.isna(to_numeric_br("Não calculado"))

    def test_nao_calculado_sem_acento_retorna_na(self):
        assert pd.isna(to_numeric_br("Nao calculado"))

    def test_nulo_retorna_na(self):
        assert pd.isna(to_numeric_br(None))

    def test_string_vazia_retorna_na(self):
        assert pd.isna(to_numeric_br(""))

    def test_traco_retorna_na(self):
        assert pd.isna(to_numeric_br("-"))

    def test_nan_float_retorna_na(self):
        assert pd.isna(to_numeric_br(float("nan")))


# ---------------------------------------------------------------------------
# normalize_nulls
# ---------------------------------------------------------------------------

class TestNormalizeNulls:
    def test_substitui_traco_por_na(self):
        df = pd.DataFrame({"col": ["-", "valor"]})
        result = normalize_nulls(df)
        assert pd.isna(result["col"].iloc[0])

    def test_substitui_na_string(self):
        df = pd.DataFrame({"col": ["NA", "valor"]})
        result = normalize_nulls(df)
        assert pd.isna(result["col"].iloc[0])

    def test_preserva_valores_validos(self):
        df = pd.DataFrame({"col": ["São Paulo", "Campinas"]})
        result = normalize_nulls(df)
        assert result["col"].iloc[0] == "São Paulo"

    def test_nao_afeta_colunas_numericas(self):
        df = pd.DataFrame({"num": [1, 2, 3]})
        result = normalize_nulls(df)
        assert list(result["num"]) == [1, 2, 3]


# ---------------------------------------------------------------------------
# standardize_codigo_ibge
# ---------------------------------------------------------------------------

class TestStandardizeCodigoIbge:
    def test_codigo_correto(self):
        series = pd.Series(["3550308"])
        result = standardize_codigo_ibge(series)
        assert result.iloc[0] == 3550308

    def test_codigo_com_ponto_zero(self):
        series = pd.Series(["3550308.0"])
        result = standardize_codigo_ibge(series)
        assert result.iloc[0] == 3550308

    def test_codigo_curto_preenche_zero(self):
        series = pd.Series(["550308"])  # 6 dígitos → preenche para 7
        result = standardize_codigo_ibge(series)
        assert result.iloc[0] == 550308  # 0550308 como int

    def test_codigo_invalido_retorna_na(self):
        series = pd.Series(["999"])  # Muito curto
        result = standardize_codigo_ibge(series)
        assert pd.isna(result.iloc[0])


# ---------------------------------------------------------------------------
# standardize_uf
# ---------------------------------------------------------------------------

class TestStandardizeUf:
    def test_uf_valida_minuscula(self):
        series = pd.Series(["sp"])
        result = standardize_uf(series)
        assert result.iloc[0] == "SP"

    def test_uf_invalida_retorna_na(self):
        series = pd.Series(["ZZ"])
        result = standardize_uf(series)
        assert pd.isna(result.iloc[0])

    def test_todas_ufs_validas(self):
        ufs = ["AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA",
               "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN",
               "RS", "RO", "RR", "SC", "SP", "SE", "TO"]
        series = pd.Series(ufs)
        result = standardize_uf(series)
        assert result.notna().all()
