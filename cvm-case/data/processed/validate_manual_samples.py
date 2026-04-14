import json
import os
import pandas as pd


BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
RAW_PATH = os.path.join(BASE_DIR, "data", "raw_csv")
PROCESSED_PATH = os.path.join(BASE_DIR, "data", "processed")

FUNDS_SCOPE_PATH = os.path.join(PROCESSED_PATH, "funds_scope.parquet")
OUTPUT_PATH = os.path.join(PROCESSED_PATH, "manual_validation_samples.json")

FIELDS_TO_COMPARE = ["CAPTC_DIA", "RESG_DIA", "VL_PATRIM_LIQ", "VL_QUOTA"]


def normalize_cnpj(series):
    return series.astype("string").str.replace(r"\D", "", regex=True).str.strip()


def pick_validation_points(scope_df):
    candidates = (
        scope_df.loc[scope_df["is_model_ready"]]
        .sort_values(["ENTITY_KEY", "DT_COMPTC"])
        .groupby("ENTITY_KEY")
        .head(3)
    )

    selected_funds = candidates["ENTITY_KEY"].drop_duplicates().head(2).tolist()
    picked = []

    for entity_key in selected_funds:
        fund_rows = candidates[candidates["ENTITY_KEY"] == entity_key].head(3)
        picked.append(fund_rows)

    return pd.concat(picked, ignore_index=True)


def load_raw_month(month_code):
    file_path = os.path.join(RAW_PATH, f"inf_diario_fi_{month_code}.csv")
    raw_df = pd.read_csv(file_path, sep=";", encoding="latin-1", low_memory=False)
    raw_df["CNPJ_FUNDO"] = normalize_cnpj(raw_df["CNPJ_FUNDO_CLASSE"])
    raw_df["DT_COMPTC"] = pd.to_datetime(raw_df["DT_COMPTC"], errors="coerce")
    return raw_df


def compare_row(raw_row, processed_row):
    comparison = {}
    for field in FIELDS_TO_COMPARE:
        raw_value = raw_row[field]
        processed_value = processed_row[field]
        comparison[field] = {
            "raw": None if pd.isna(raw_value) else float(raw_value),
            "processed": None if pd.isna(processed_value) else float(processed_value),
            "match": bool(pd.isna(raw_value) and pd.isna(processed_value) or raw_value == processed_value),
        }
    return comparison


def main():
    scope_df = pd.read_parquet(
        FUNDS_SCOPE_PATH,
        columns=[
            "ENTITY_KEY",
            "CNPJ_FUNDO",
            "ID_SUBCLASSE",
            "DT_COMPTC",
            "Denominacao_Social",
            "CAPTC_DIA",
            "RESG_DIA",
            "VL_PATRIM_LIQ",
            "VL_QUOTA",
            "is_model_ready",
        ],
    )

    validation_points = pick_validation_points(scope_df)
    raw_cache = {}
    report = []

    for _, row in validation_points.iterrows():
        month_code = row["DT_COMPTC"].strftime("%Y%m")
        if month_code not in raw_cache:
            raw_cache[month_code] = load_raw_month(month_code)

        raw_df = raw_cache[month_code]
        raw_rows = raw_df[
            (raw_df["CNPJ_FUNDO"] == row["CNPJ_FUNDO"])
            & (raw_df["DT_COMPTC"] == row["DT_COMPTC"])
        ]
        if pd.notna(row["ID_SUBCLASSE"]):
            raw_rows = raw_rows[raw_rows["ID_SUBCLASSE"].astype("string") == str(row["ID_SUBCLASSE"])]

        raw_row = raw_rows.iloc[0]
        report.append(
            {
                "entity_key": row["ENTITY_KEY"],
                "cnpj_fundo": row["CNPJ_FUNDO"],
                "id_subclasse": None if pd.isna(row["ID_SUBCLASSE"]) else str(row["ID_SUBCLASSE"]),
                "denominacao_social": row["Denominacao_Social"],
                "dt_comptc": row["DT_COMPTC"].strftime("%Y-%m-%d"),
                "raw_file": f"inf_diario_fi_{month_code}.csv",
                "raw_match_count": int(len(raw_rows)),
                "comparison": compare_row(raw_row, row),
            }
        )

    with open(OUTPUT_PATH, "w", encoding="utf-8") as file:
        json.dump(report, file, ensure_ascii=False, indent=2)

    print(f"Validação manual salva em: {OUTPUT_PATH}")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
