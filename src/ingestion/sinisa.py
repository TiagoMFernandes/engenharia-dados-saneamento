"""
Ingestão de dados do SINISA (Sistema Nacional de Informações sobre Saneamento).

Os arquivos CSV ou Excel devem ser baixados manualmente e colocados em data/raw/sinisa/.
Para tentar o download automático, use: python -m src.ingestion.sinisa_download

Documentação oficial: https://www.gov.br/mdr/pt-br/assuntos/saneamento/sinisa
"""

from __future__ import annotations

import logging
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from src.utils.columns import standardize_column_names
from src.utils.io import save_parquet
from src.utils.paths import SINISA_BRONZE_DIR, SINISA_RAW_DIR

logger = logging.getLogger(__name__)

FONTE = "SINISA - SNIS"
SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".xls"}
CSV_ENCODINGS = ("utf-8", "utf-8-sig", "latin-1", "cp1252")


def list_input_files(input_dir: Path) -> list[Path]:
    """Lista todos os arquivos suportados na pasta de entrada."""
    if not input_dir.exists():
        logger.warning("Pasta de entrada não encontrada: %s", input_dir)
        return []

    files = sorted(
        path
        for path in input_dir.iterdir()
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
    )
    return files


def _read_csv(path: Path) -> pd.DataFrame:
    """Tenta ler CSV com múltiplos encodings comuns em dados brasileiros."""
    last_error: Exception | None = None
    for encoding in CSV_ENCODINGS:
        try:
            return pd.read_csv(path, encoding=encoding, sep=None, engine="python")
        except UnicodeDecodeError as exc:
            last_error = exc
    raise ValueError(f"Não foi possível ler o CSV {path.name}") from last_error


def _normalize_text(value: object) -> str:
    """Normaliza texto para facilitar identificação de cabeçalhos."""
    if pd.isna(value):
        return ""

    text = str(value).strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = re.sub(r"\s+", "_", text)
    return text


def _find_sinisa_header_row(path: Path, engine: str | None) -> int:
    """
    Procura a linha real de cabeçalho da planilha SINISA.

    As planilhas do SINISA possuem linhas institucionais (títulos, logos)
    antes da tabela de dados real. Este método escaneia as primeiras 40 linhas
    buscando a linha que contém simultaneamente:
    - 'cod_ibge' (código do município)
    - 'municipio' (nome do município)
    - pelo menos um código de indicador no padrão AAA9999 (ex: IAG0001)
    """
    preview = pd.read_excel(
        path,
        engine=engine,
        sheet_name=0,
        header=None,
        dtype=str,
        nrows=40,
    )

    for idx, row in preview.iterrows():
        values = [_normalize_text(value) for value in row.tolist()]

        has_cod_ibge = "cod_ibge" in values
        has_municipio = "municipio" in values
        has_indicator_code = any(
            re.fullmatch(r"[a-z]{3}\d{4}", value or "")
            for value in values
        )

        if has_cod_ibge and has_municipio and has_indicator_code:
            logger.info("Cabeçalho real identificado na linha %s do Excel", idx + 1)
            return idx

    raise ValueError(
        f"Não foi possível identificar a linha real de cabeçalho no arquivo {path.name}. "
        "Verifique se o arquivo é uma planilha válida do SINISA."
    )


def _read_excel(path: Path) -> pd.DataFrame:
    """Lê arquivo Excel do SINISA detectando automaticamente o cabeçalho real."""
    suffix = path.suffix.lower()
    engine = "openpyxl" if suffix == ".xlsx" else None

    header_row = _find_sinisa_header_row(path, engine)

    df = pd.read_excel(
        path,
        engine=engine,
        sheet_name=0,
        header=header_row,
        dtype=str,
    )

    df = df.dropna(axis=1, how="all")
    df = df.dropna(axis=0, how="all")

    # Remove linhas duplicadas de cabeçalho que aparecem no meio da tabela
    if "cod_IBGE" in df.columns:
        df = df[df["cod_IBGE"].astype(str).str.lower().str.strip() != "cod_ibge"]

    return df


def read_file(path: Path) -> pd.DataFrame:
    """Lê um arquivo SINISA (CSV ou Excel) e retorna um DataFrame bruto."""
    suffix = path.suffix.lower()
    logger.info("Lendo arquivo: %s", path.name)

    if suffix == ".csv":
        df = _read_csv(path)
    elif suffix in {".xlsx", ".xls"}:
        df = _read_excel(path)
    else:
        raise ValueError(f"Formato não suportado: {path.suffix}")

    logger.info(
        "Arquivo %s carregado com %s linhas e %s colunas",
        path.name, len(df), len(df.columns),
    )
    return df


def normalize_dataframe(df: pd.DataFrame, source_file: Path) -> pd.DataFrame:
    """
    Padroniza nomes de colunas e adiciona metadados de ingestão.

    Metadados adicionados:
    - fonte: origem dos dados
    - arquivo_origem: nome do arquivo fonte
    - dt_ingestao: timestamp UTC da ingestão
    """
    normalized = df.copy()
    original_columns = list(normalized.columns)
    normalized.columns = standardize_column_names(original_columns)

    renamed = {
        original: new
        for original, new in zip(original_columns, normalized.columns)
        if str(original) != new
    }
    if renamed:
        logger.info(
            "Colunas padronizadas em %s: %s",
            source_file.name,
            ", ".join(f"{old} -> {new}" for old, new in renamed.items()),
        )

    normalized["fonte"] = FONTE
    normalized["arquivo_origem"] = source_file.name
    normalized["dt_ingestao"] = pd.Timestamp(datetime.now(timezone.utc))
    return normalized


def _output_path(source_file: Path, output_dir: Path) -> Path:
    stem = source_file.stem.lower().replace(" ", "_")
    return output_dir / f"sinisa_{stem}.parquet"


def ingest_sinisa(
    input_dir: Path | None = None,
    output_dir: Path | None = None,
) -> dict[str, Path]:
    """
    Ingere todos os arquivos SINISA da pasta raw e salva na camada Bronze.

    MELHORIA: erros em arquivos individuais são registrados em log e o
    processamento continua para os demais arquivos, ao invés de abortar tudo.

    Returns:
        Dicionário {nome_arquivo: caminho_parquet_bronze}
    """
    source_dir = input_dir or SINISA_RAW_DIR
    target_dir = output_dir or SINISA_BRONZE_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    files = list_input_files(source_dir)
    if not files:
        logger.warning(
            "Nenhum arquivo CSV ou Excel encontrado em %s. "
            "Execute 'python -m src.ingestion.sinisa_download' para tentar o download automático "
            "ou baixe manualmente em: https://www.gov.br/mdr/pt-br/assuntos/saneamento/sinisa",
            source_dir,
        )
        return {}

    saved_paths: dict[str, Path] = {}
    errors: list[str] = []

    for file_path in files:
        try:
            df = read_file(file_path)
            normalized = normalize_dataframe(df, file_path)
            output_path = _output_path(file_path, target_dir)
            save_parquet(normalized, output_path)
            saved_paths[file_path.stem] = output_path
            logger.info(
                "Arquivo bronze salvo: %s (%s registros, %s colunas)",
                output_path,
                len(normalized),
                len(normalized.columns),
            )
        except Exception as exc:
            # MELHORIA: captura o erro, registra e continua para o próximo arquivo
            logger.error("Falha ao processar %s: %s", file_path.name, exc)
            errors.append(file_path.name)

    if errors:
        logger.warning(
            "Ingestão SINISA concluída com %s erro(s). Arquivos com falha: %s",
            len(errors),
            ", ".join(errors),
        )
    else:
        logger.info(
            "Ingestão SINISA concluída com sucesso: %s arquivo(s) processado(s)",
            len(saved_paths),
        )

    return saved_paths


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    paths = ingest_sinisa()
    if not paths:
        print(f"Nenhum arquivo encontrado em {SINISA_RAW_DIR}")
        return

    for name, path in paths.items():
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()
