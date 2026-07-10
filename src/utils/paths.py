from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
BRONZE_DIR = DATA_DIR / "bronze"
SILVER_DIR = DATA_DIR / "silver"
GOLD_DIR = DATA_DIR / "gold"
RAW_DIR = DATA_DIR / "raw"
SINISA_RAW_DIR = RAW_DIR / "sinisa"
SINISA_BRONZE_DIR = BRONZE_DIR / "sinisa"
SINISA_SILVER_DIR = SILVER_DIR / "sinisa"
GOLD_AGUA_PATH = GOLD_DIR / "infra_municipios_agua.parquet"
