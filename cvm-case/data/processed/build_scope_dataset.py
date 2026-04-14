import json
import os
import sys
import unicodedata

import pandas as pd


BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

PROCESSED_PATH = os.path.join(BASE_DIR, "data", "processed")
INPUT_PATH = os.path.join(PROCESSED_PATH, "funds_raw.parquet")
OUTPUT_PATH = os.path.join(PROCESSED_PATH, "funds_scope.parquet")
SUMMARY_PATH = os.path.join(PROCESSED_PATH, "funds_scope_summary.json")

from utils.br_calendar import business_days_between, is_business_day

MIN_OBSERVATIONS = 50
TARGET_WINDOW_DAYS = 21
MIN_VALID_DAY_RATIO = 0.80
MIN_VALID_BUSINESS_DAYS = 50


def normalize_text(value):
    if pd.isna(value):
        return None

    text = str(value).strip().lower()
    return "".join(
        char
        for char in unicodedata.normalize("NFKD", text)
        if not unicodedata.combining(char)
    )


def future_rolling_sum(series, window):
    shifted = series.shift(-1)
    return shifted.rolling(window=window, min_periods=window).sum().shift(-(window - 1))


def coverage_summary(group):
    expected_days = business_days_between(group["DT_COMPTC"].min(), group["DT_COMPTC"].max())
    expected_count = len(expected_days)
    observed_count = group["DT_COMPTC"].nunique()
    return pd.Series(
        {
            "observed_business_days": observed_count,
            "expected_business_days": expected_count,
            "valid_day_ratio": observed_count / expected_count if expected_count else None,
        }
    )


def build_scope_dataset():
    columns = [
        "CNPJ_FUNDO",
        "ENTITY_KEY",
        "ID_SUBCLASSE",
        "DT_COMPTC",
        "Denominacao_Social",
        "Situacao",
        "Classificacao",
        "VL_TOTAL",
        "VL_QUOTA",
        "VL_PATRIM_LIQ",
        "CAPTC_DIA",
        "RESG_DIA",
        "NR_COTST",
        "Data_Registro",
        "Data_Constituicao",
        "Data_Inicio",
        "Classe_Cotas",
        "Classificacao_Anbima",
        "Exclusivo",
        "Publico_Alvo",
    ]

    df = pd.read_parquet(INPUT_PATH, columns=columns)
    df["DT_COMPTC"] = pd.to_datetime(df["DT_COMPTC"])
    df = df.sort_values(["ENTITY_KEY", "DT_COMPTC"]).copy()
    df["is_business_day"] = is_business_day(df["DT_COMPTC"])

    df["classificacao_norm"] = df["Classificacao"].map(normalize_text)
    df["situacao_norm"] = df["Situacao"].map(normalize_text)

    scope_mask = (
        (df["classificacao_norm"] == "acoes")
        & (df["situacao_norm"] == "em funcionamento normal")
    )
    df = df.loc[scope_mask].copy()

    non_business_rows = int((~df["is_business_day"]).sum())
    if non_business_rows:
        df = df.loc[df["is_business_day"]].copy()

    entity_coverage = df.groupby("ENTITY_KEY").apply(coverage_summary).reset_index()
    eligible_entities = entity_coverage.loc[
        entity_coverage["observed_business_days"].ge(max(MIN_OBSERVATIONS, MIN_VALID_BUSINESS_DAYS))
        & entity_coverage["valid_day_ratio"].ge(MIN_VALID_DAY_RATIO),
        "ENTITY_KEY",
    ]
    df = df[df["ENTITY_KEY"].isin(eligible_entities)].copy()
    df = df.merge(entity_coverage, on="ENTITY_KEY", how="left")

    df["flow_dia"] = df["CAPTC_DIA"].fillna(0) - df["RESG_DIA"].fillna(0)
    df["pl_lag1"] = df.groupby("ENTITY_KEY")["VL_PATRIM_LIQ"].shift(1)
    df["ret_1d"] = df.groupby("ENTITY_KEY")["VL_QUOTA"].pct_change()

    df["target_flow_t1_t21"] = (
        df.groupby("ENTITY_KEY", group_keys=False)["flow_dia"]
        .apply(lambda series: future_rolling_sum(series, TARGET_WINDOW_DAYS))
    )

    positive_pl = df["pl_lag1"].where(df["pl_lag1"] > 0)
    df["target_flow_pct_t1_t21"] = df["target_flow_t1_t21"] / positive_pl

    df["is_model_ready"] = (
        df["pl_lag1"].gt(0)
        & df["target_flow_t1_t21"].notna()
        & df["VL_QUOTA"].gt(0)
        & df["VL_PATRIM_LIQ"].gt(0)
    )

    model_base = df.loc[df["is_model_ready"]].copy()
    clipped_target = model_base["target_flow_pct_t1_t21"].clip(lower=-1, upper=1)

    summary = {
        "scope_definition": {
            "classificacao": "Ações",
            "situacao": "Em Funcionamento Normal",
            "min_observations_per_fund": MIN_OBSERVATIONS,
            "min_valid_business_days": MIN_VALID_BUSINESS_DAYS,
            "min_valid_day_ratio": MIN_VALID_DAY_RATIO,
            "target": "Fluxo futuro acumulado de T+1 a T+21 dias úteis, normalizado pelo PL defasado em 1 dia",
        },
        "sample": {
            "rows_after_scope_filter": int(len(df)),
            "rows_model_ready": int(len(model_base)),
            "eligible_entities": int(df["ENTITY_KEY"].nunique()),
            "eligible_class_cnpjs": int(df["CNPJ_FUNDO"].nunique()),
            "period_start": str(df["DT_COMPTC"].min().date()),
            "period_end": str(df["DT_COMPTC"].max().date()),
        },
        "calendar_quality": {
            "non_business_rows_removed": non_business_rows,
            "median_valid_day_ratio": float(entity_coverage["valid_day_ratio"].median()),
            "p05_valid_day_ratio": float(entity_coverage["valid_day_ratio"].quantile(0.05)),
            "eligible_entities_after_calendar_filter": int(df["ENTITY_KEY"].nunique()),
        },
        "target_distribution": {
            "median": float(model_base["target_flow_pct_t1_t21"].median()),
            "mean_clipped_1": float(clipped_target.mean()),
            "p01": float(model_base["target_flow_pct_t1_t21"].quantile(0.01)),
            "p05": float(model_base["target_flow_pct_t1_t21"].quantile(0.05)),
            "p95": float(model_base["target_flow_pct_t1_t21"].quantile(0.95)),
            "p99": float(model_base["target_flow_pct_t1_t21"].quantile(0.99)),
            "share_abs_target_gt_1": float(
                model_base["target_flow_pct_t1_t21"].abs().gt(1).mean()
            ),
        },
    }

    df.to_parquet(OUTPUT_PATH, index=False)
    with open(SUMMARY_PATH, "w", encoding="utf-8") as file:
        json.dump(summary, file, ensure_ascii=False, indent=2)

    print(f"Dataset salvo em: {OUTPUT_PATH}")
    print(f"Resumo salvo em: {SUMMARY_PATH}")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    build_scope_dataset()
