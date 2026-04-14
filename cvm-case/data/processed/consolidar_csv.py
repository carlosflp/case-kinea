import json
import os

import pandas as pd


BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
RAW_PATH = os.path.join(BASE_DIR, "data", "raw_csv")
PROCESSED_PATH = os.path.join(BASE_DIR, "data", "processed")

OUTPUT_PATH = os.path.join(PROCESSED_PATH, "funds_raw.parquet")
QUALITY_PATH = os.path.join(PROCESSED_PATH, "funds_raw_quality.json")

DAILY_PREFIX = "inf_diario_fi_"
DAILY_REQUIRED_COLUMNS = [
    "TP_FUNDO_CLASSE",
    "CNPJ_FUNDO_CLASSE",
    "ID_SUBCLASSE",
    "DT_COMPTC",
    "VL_TOTAL",
    "VL_QUOTA",
    "VL_PATRIM_LIQ",
    "CAPTC_DIA",
    "RESG_DIA",
    "NR_COTST",
]
REGISTRY_DATE_COLUMNS = [
    "Data_Registro",
    "Data_Constituicao",
    "Data_Inicio",
    "Data_Inicio_Situacao",
    "Data_Patrimonio_Liquido",
]


def normalize_cnpj(series):
    return series.astype("string").str.replace(r"\D", "", regex=True).str.strip()


def list_daily_files():
    files = []
    for name in sorted(os.listdir(RAW_PATH)):
        if name.startswith(DAILY_PREFIX) and name.endswith(".csv"):
            files.append(os.path.join(RAW_PATH, name))
    return files


def load_daily_data(files):
    frames = []

    for file_path in files:
        print(f"Lendo: {os.path.basename(file_path)}")
        frame = pd.read_csv(
            file_path,
            sep=";",
            encoding="latin-1",
            low_memory=False,
            usecols=DAILY_REQUIRED_COLUMNS,
        )
        frame["source_file"] = os.path.basename(file_path)
        frame["DT_COMPTC"] = pd.to_datetime(frame["DT_COMPTC"], errors="coerce")
        frame["CNPJ_FUNDO"] = normalize_cnpj(frame["CNPJ_FUNDO_CLASSE"])
        frame["ID_SUBCLASSE"] = frame["ID_SUBCLASSE"].astype("string")
        frame["ENTITY_KEY"] = (
            frame["CNPJ_FUNDO"]
            + "::"
            + frame["ID_SUBCLASSE"].fillna("SEM_SUBCLASSE")
        )
        frames.append(frame)

    daily = pd.concat(frames, ignore_index=True)
    print(f"Shape bruto consolidado: {daily.shape}")
    return daily


def resolve_daily_duplicates(daily):
    duplicate_mask = daily.duplicated(["ENTITY_KEY", "DT_COMPTC"], keep=False)
    duplicate_rows = daily.loc[duplicate_mask].copy()

    metric_columns = [
        "VL_TOTAL",
        "VL_QUOTA",
        "VL_PATRIM_LIQ",
        "CAPTC_DIA",
        "RESG_DIA",
        "NR_COTST",
    ]

    conflicts = (
        duplicate_rows.groupby(["ENTITY_KEY", "DT_COMPTC"])[metric_columns]
        .nunique(dropna=False)
        .max(axis=1)
    )
    conflicting_groups = int((conflicts > 1).sum())

    daily["tp_preference"] = daily["TP_FUNDO_CLASSE"].eq("CLASSES - FIF").astype(int)
    daily = daily.sort_values(
        ["ENTITY_KEY", "DT_COMPTC", "tp_preference", "TP_FUNDO_CLASSE", "source_file"],
        ascending=[True, True, False, True, True],
        na_position="last",
    )
    daily = daily.drop_duplicates(["ENTITY_KEY", "DT_COMPTC"], keep="first")
    daily = daily.drop(columns=["tp_preference"])
    print(f"Shape após deduplicação diária: {daily.shape}")

    return daily, {
        "duplicate_rows_before_cleaning": int(duplicate_mask.sum()),
        "duplicate_keys_before_cleaning": int(conflicts.shape[0]),
        "conflicting_duplicate_keys": conflicting_groups,
    }


def load_registry():
    registry_path = os.path.join(RAW_PATH, "registro_classe.csv")
    registry = pd.read_csv(
        registry_path,
        sep=";",
        encoding="latin-1",
        low_memory=False,
    )

    registry["CNPJ_FUNDO"] = normalize_cnpj(registry["CNPJ_Classe"])

    for column in REGISTRY_DATE_COLUMNS:
        if column in registry.columns:
            registry[column] = pd.to_datetime(registry[column], errors="coerce")

    registry["registry_non_null_score"] = registry.notna().sum(axis=1)
    registry = registry.sort_values(
        ["CNPJ_FUNDO", "registry_non_null_score", "Data_Registro"],
        ascending=[True, False, False],
        na_position="last",
    )

    duplicate_keys = int(registry.duplicated(["CNPJ_FUNDO"]).sum())
    registry = registry.drop_duplicates(["CNPJ_FUNDO"], keep="first")

    return registry, {
        "registry_rows_before_dedup": int(len(registry) + duplicate_keys),
        "registry_duplicate_keys_before_cleaning": duplicate_keys,
        "registry_rows_after_dedup": int(len(registry)),
    }


def build_quality_report(df, daily_quality, registry_quality):
    merge_hit_rate = float(df["ID_Registro_Classe"].notna().mean())

    quality = {
        "source_requirements": {
            "daily_informe_used": True,
            "registry_used": True,
        },
        "daily_data": daily_quality,
        "registry_data": registry_quality,
        "merge": {
            "rows_after_merge": int(len(df)),
            "funds_after_merge": int(df["CNPJ_FUNDO"].nunique()),
            "merge_hit_rate": merge_hit_rate,
            "rows_without_registry_match": int(df["ID_Registro_Classe"].isna().sum()),
        },
        "nulls_after_merge": {
            "VL_QUOTA": int(df["VL_QUOTA"].isna().sum()),
            "VL_PATRIM_LIQ": int(df["VL_PATRIM_LIQ"].isna().sum()),
            "CAPTC_DIA": int(df["CAPTC_DIA"].isna().sum()),
            "RESG_DIA": int(df["RESG_DIA"].isna().sum()),
            "Classificacao": int(df["Classificacao"].isna().sum()),
            "Situacao": int(df["Situacao"].isna().sum()),
        },
        "cleaning_rules": [
            "Padronização de chave CNPJ removendo pontuação.",
            "Conversão de datas com tratamento de erro para NaT.",
            "Criação de chave da entidade por classe/subclasse usando CNPJ_FUNDO e ID_SUBCLASSE.",
            "Deduplicação do informe diário mantendo uma linha por ENTITY_KEY e DT_COMPTC.",
            "Em duplicidades da mesma entidade, preferência para TP_FUNDO_CLASSE = CLASSES - FIF.",
            "Validação de conflitos em duplicidades usando colunas econômicas do informe diário.",
            "Deduplicação do cadastro por CNPJ escolhendo o registro com mais campos preenchidos e data de registro mais recente.",
        ],
    }
    return quality


def main():
    os.makedirs(PROCESSED_PATH, exist_ok=True)

    daily_files = list_daily_files()
    if not daily_files:
        raise FileNotFoundError("Nenhum CSV mensal do informe diário foi encontrado.")

    daily = load_daily_data(daily_files)
    daily, daily_quality = resolve_daily_duplicates(daily)

    registry, registry_quality = load_registry()

    df = daily.merge(registry, on="CNPJ_FUNDO", how="left")
    df = df.sort_values(["CNPJ_FUNDO", "DT_COMPTC"]).reset_index(drop=True)

    quality = build_quality_report(df, daily_quality, registry_quality)

    df.to_parquet(OUTPUT_PATH, index=False)
    with open(QUALITY_PATH, "w", encoding="utf-8") as file:
        json.dump(quality, file, ensure_ascii=False, indent=2, default=str)

    print(f"Arquivo salvo em: {OUTPUT_PATH}")
    print(f"Relatório de qualidade salvo em: {QUALITY_PATH}")
    print(json.dumps(quality, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
