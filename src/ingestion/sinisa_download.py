"""
Tentativa de download automático dos dados do SINISA.

O SINISA não disponibiliza uma API pública com download direto.
Este script tenta localizar e baixar a planilha mais recente disponível
no portal do governo. Caso falhe, exibe instruções claras para o download manual.

Download manual: https://www.gov.br/mdr/pt-br/assuntos/saneamento/sinisa
"""

from __future__ import annotations

import logging
from pathlib import Path

import requests

from src.utils.paths import SINISA_RAW_DIR

logger = logging.getLogger(__name__)

# URLs candidatas para download direto (podem mudar com atualizações do portal)
SINISA_DOWNLOAD_CANDIDATES = [
    "https://www.gov.br/mdr/pt-br/assuntos/saneamento/sinisa/planilhas-de-indicadores-de-abastecimento-de-agua",
]

MANUAL_DOWNLOAD_INSTRUCTIONS = """
========================================================
  DOWNLOAD MANUAL DO SINISA NECESSÁRIO
========================================================

O download automático não foi possível pois o portal do
governo requer navegação manual para obter o arquivo.

Siga os passos abaixo:

  1. Acesse: https://www.gov.br/mdr/pt-br/assuntos/saneamento/sinisa
  2. Navegue até "Planilhas de Indicadores"
  3. Baixe a planilha de "Abastecimento de Água" (arquivo .xlsx)
  4. Salve o arquivo na pasta:
        data/raw/sinisa/

  5. Execute novamente:
        python -m src.ingestion.sinisa

========================================================
"""


def try_download(output_dir: Path | None = None) -> bool:
    """
    Tenta baixar o arquivo SINISA automaticamente.

    Returns:
        True se o download foi bem-sucedido, False caso contrário.
    """
    target_dir = output_dir or SINISA_RAW_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    for url in SINISA_DOWNLOAD_CANDIDATES:
        try:
            logger.info("Tentando download de: %s", url)
            response = requests.get(url, timeout=30, allow_redirects=True)
            content_type = response.headers.get("content-type", "")

            # Verifica se é um arquivo Excel ou CSV (não HTML)
            is_excel = "spreadsheet" in content_type or "excel" in content_type
            is_csv = "text/csv" in content_type
            is_octet = "octet-stream" in content_type

            if response.status_code == 200 and (is_excel or is_csv or is_octet):
                # Determina extensão pelo content-type
                if "spreadsheetml" in content_type:
                    ext = ".xlsx"
                elif is_csv:
                    ext = ".csv"
                else:
                    ext = ".xlsx"

                output_path = target_dir / f"sinisa_indicadores_agua{ext}"
                output_path.write_bytes(response.content)
                logger.info("Download concluído: %s", output_path)
                return True

        except requests.RequestException as exc:
            logger.debug("Falha no download de %s: %s", url, exc)

    return False


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    print("Tentando download automático dos dados do SINISA...")

    success = try_download()

    if success:
        print(f"\nArquivo salvo em: {SINISA_RAW_DIR}")
        print("Agora execute: python -m src.ingestion.sinisa")
    else:
        print(MANUAL_DOWNLOAD_INSTRUCTIONS)


if __name__ == "__main__":
    main()
