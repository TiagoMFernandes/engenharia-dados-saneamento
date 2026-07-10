import re
import unicodedata


def standardize_column_name(name: str) -> str:
    if name is None or (isinstance(name, float) and str(name) == "nan"):
        name = "coluna_sem_nome"

    text = str(name).strip()
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")

    return text or "coluna_sem_nome"


def standardize_column_names(columns: list) -> list[str]:
    standardized: list[str] = []
    seen: dict[str, int] = {}

    for column in columns:
        base_name = standardize_column_name(column)
        count = seen.get(base_name, 0)
        if count:
            final_name = f"{base_name}_{count + 1}"
        else:
            final_name = base_name
        seen[base_name] = count + 1
        standardized.append(final_name)

    return standardized
