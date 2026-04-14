import json
import os

import numpy as np
import pandas as pd


BASE_DIR = os.path.dirname(os.path.dirname(__file__))
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")

INPUT_PATH = os.path.join(PROCESSED_DIR, "funds_scope.parquet")
OUTPUT_PATH = os.path.join(PROCESSED_DIR, "funds_features.parquet")
SUMMARY_PATH = os.path.join(PROCESSED_DIR, "funds_features_summary.json")

MIN_PL_LAG1 = 1_000_000
MIN_VALID_DAY_RATIO = 0.80
TARGET_CLIP_LOWER = -1.0
TARGET_CLIP_UPPER = 1.0
TOP_ANBIMA_BUCKETS = 8


def rolling_drawdown(series, window):
    rolling_peak = series.rolling(window=window, min_periods=window).max()
    return series / rolling_peak - 1


def build_fund_start_date(df):
    candidate_columns = ["Data_Constituicao", "Data_Inicio", "Data_Registro"]
    first_seen = df.groupby("ENTITY_KEY")["DT_COMPTC"].transform("min")

    candidates = [first_seen]
    for column in candidate_columns:
        valid = df[column].where(df[column].notna() & df[column].le(df["DT_COMPTC"]))
        candidates.append(valid)

    start_df = pd.concat(candidates, axis=1)
    return start_df.min(axis=1)


def add_category_buckets(df):
    anbima = df["Classificacao_Anbima"].fillna("Sem Classificacao").astype("string")
    top_buckets = anbima.value_counts().head(TOP_ANBIMA_BUCKETS).index
    df["anbima_bucket"] = np.where(
        anbima.isin(top_buckets),
        anbima,
        "Outras",
    )
    df["publico_alvo_bucket"] = (
        df["Publico_Alvo"].fillna("Nao Informado").astype("string")
    )
    df["exclusivo_flag"] = (
        df["Exclusivo"].fillna("Nao Informado").astype("string")
    )
    return df


def build_features():
    columns = [
        "ENTITY_KEY",
        "CNPJ_FUNDO",
        "DT_COMPTC",
        "Denominacao_Social",
        "VL_TOTAL",
        "VL_QUOTA",
        "VL_PATRIM_LIQ",
        "CAPTC_DIA",
        "RESG_DIA",
        "NR_COTST",
        "Data_Registro",
        "Data_Constituicao",
        "Data_Inicio",
        "Classificacao_Anbima",
        "Exclusivo",
        "Publico_Alvo",
        "flow_dia",
        "pl_lag1",
        "ret_1d",
        "valid_day_ratio",
        "observed_business_days",
        "expected_business_days",
        "target_flow_t1_t21",
        "target_flow_pct_t1_t21",
        "is_model_ready",
    ]

    df = pd.read_parquet(INPUT_PATH, columns=columns)
    df["DT_COMPTC"] = pd.to_datetime(df["DT_COMPTC"])
    for column in ["Data_Registro", "Data_Constituicao", "Data_Inicio"]:
        df[column] = pd.to_datetime(df[column], errors="coerce")

    df = df.sort_values(["ENTITY_KEY", "DT_COMPTC"]).copy()
    entity_group = df.groupby("ENTITY_KEY", group_keys=False)

    df["fund_start_date"] = build_fund_start_date(df)
    df["fund_age_days"] = (df["DT_COMPTC"] - df["fund_start_date"]).dt.days.clip(lower=0)
    df["fund_age_years"] = df["fund_age_days"] / 365.25

    df["quota_lag1"] = entity_group["VL_QUOTA"].shift(1)
    df["vl_total_lag1"] = entity_group["VL_TOTAL"].shift(1)
    df["nr_cotst_lag1"] = entity_group["NR_COTST"].shift(1)
    df["flow_pct_1d"] = df["flow_dia"] / df["pl_lag1"].where(df["pl_lag1"] > 0)
    df["ex_flow_return_1d"] = (
        (df["VL_PATRIM_LIQ"] - df["pl_lag1"] - df["flow_dia"])
        / df["pl_lag1"].where(df["pl_lag1"] > 0)
    )

    for window in [5, 21, 63, 126]:
        df[f"ret_{window}d"] = entity_group["VL_QUOTA"].pct_change(window).shift(1)

    for window in [21, 63]:
        df[f"vol_{window}d"] = (
            entity_group["ret_1d"]
            .rolling(window=window, min_periods=window)
            .std()
            .shift(1)
            .reset_index(level=0, drop=True)
        )

    for window in [63, 126]:
        drawdown = entity_group["quota_lag1"].apply(
            lambda series, drawdown_window=window: rolling_drawdown(series, drawdown_window)
        )
        df[f"drawdown_{window}d"] = drawdown.reset_index(level=0, drop=True)

    rolling_mean_21 = (
        entity_group["ret_1d"]
        .rolling(window=21, min_periods=21)
        .mean()
        .shift(1)
        .reset_index(level=0, drop=True)
    )
    rolling_std_21 = (
        entity_group["ret_1d"]
        .rolling(window=21, min_periods=21)
        .std()
        .shift(1)
        .reset_index(level=0, drop=True)
    )
    df["ret_zscore_21d"] = (entity_group["ret_1d"].shift(1) - rolling_mean_21) / rolling_std_21

    for window in [5, 21, 63]:
        df[f"flow_pct_{window}d_sum"] = (
            entity_group["flow_pct_1d"]
            .rolling(window=window, min_periods=window)
            .sum()
            .shift(1)
            .reset_index(level=0, drop=True)
        )
        df[f"ex_flow_return_{window}d_mean"] = (
            entity_group["ex_flow_return_1d"]
            .rolling(window=window, min_periods=window)
            .mean()
            .shift(1)
            .reset_index(level=0, drop=True)
        )

    df["nr_cotst_change_21d"] = entity_group["NR_COTST"].pct_change(21).shift(1)
    df["log_pl_lag1"] = np.log1p(df["pl_lag1"].clip(lower=0))
    df["log_vl_total_lag1"] = np.log1p(df["vl_total_lag1"].clip(lower=0))
    df["log_nr_cotst_lag1"] = np.log1p(df["nr_cotst_lag1"].clip(lower=0))

    class_medians = (
        df.groupby("DT_COMPTC")[["ret_21d", "ret_63d", "vol_21d", "flow_pct_21d_sum"]]
        .median()
        .rename(
            columns={
                "ret_21d": "class_median_ret_21d",
                "ret_63d": "class_median_ret_63d",
                "vol_21d": "class_median_vol_21d",
                "flow_pct_21d_sum": "class_median_flow_pct_21d_sum",
            }
        )
        .reset_index()
    )
    df = df.merge(class_medians, on="DT_COMPTC", how="left")
    df["ret_21d_rel_class"] = df["ret_21d"] - df["class_median_ret_21d"]
    df["ret_63d_rel_class"] = df["ret_63d"] - df["class_median_ret_63d"]
    df["vol_21d_rel_class"] = df["vol_21d"] - df["class_median_vol_21d"]
    df["flow_pct_21d_rel_class"] = (
        df["flow_pct_21d_sum"] - df["class_median_flow_pct_21d_sum"]
    )

    df["weekday"] = df["DT_COMPTC"].dt.weekday
    df["month"] = df["DT_COMPTC"].dt.month
    df["is_month_end"] = df["DT_COMPTC"].dt.is_month_end.astype(int)
    df["is_quarter_end"] = df["DT_COMPTC"].dt.is_quarter_end.astype(int)
    df["is_january"] = (df["month"] == 1).astype(int)

    df = add_category_buckets(df)

    df["target_flow_pct_t1_t21_clipped"] = df["target_flow_pct_t1_t21"].clip(
        lower=TARGET_CLIP_LOWER,
        upper=TARGET_CLIP_UPPER,
    )
    df["target_top_decile"] = (
        df.groupby("DT_COMPTC")["target_flow_pct_t1_t21_clipped"]
        .transform(lambda series: series >= series.quantile(0.9))
        .astype("Int64")
    )

    feature_columns = [
        "log_pl_lag1",
        "log_vl_total_lag1",
        "log_nr_cotst_lag1",
        "fund_age_years",
        "ret_5d",
        "ret_21d",
        "ret_63d",
        "ret_126d",
        "ret_21d_rel_class",
        "ret_63d_rel_class",
        "vol_21d",
        "vol_63d",
        "vol_21d_rel_class",
        "drawdown_63d",
        "drawdown_126d",
        "ret_zscore_21d",
        "flow_pct_5d_sum",
        "flow_pct_21d_sum",
        "flow_pct_63d_sum",
        "flow_pct_21d_rel_class",
        "ex_flow_return_5d_mean",
        "ex_flow_return_21d_mean",
        "ex_flow_return_63d_mean",
        "nr_cotst_change_21d",
        "weekday",
        "month",
        "is_month_end",
        "is_quarter_end",
        "is_january",
        "anbima_bucket",
        "publico_alvo_bucket",
        "exclusivo_flag",
    ]

    required_history = [
        "ret_21d",
        "ret_63d",
        "ret_126d",
        "vol_21d",
        "vol_63d",
        "drawdown_63d",
        "drawdown_126d",
        "flow_pct_21d_sum",
        "flow_pct_63d_sum",
        "ex_flow_return_21d_mean",
        "ex_flow_return_63d_mean",
    ]

    model_df = df.loc[df["is_model_ready"]].copy()
    model_df = model_df.loc[model_df["pl_lag1"] >= MIN_PL_LAG1].copy()
    model_df = model_df.loc[model_df["valid_day_ratio"] >= MIN_VALID_DAY_RATIO].copy()
    model_df["has_full_history"] = model_df[required_history].notna().all(axis=1)
    model_df = model_df.loc[model_df["has_full_history"]].copy()

    keep_columns = [
        "ENTITY_KEY",
        "CNPJ_FUNDO",
        "Denominacao_Social",
        "DT_COMPTC",
        "target_flow_t1_t21",
        "target_flow_pct_t1_t21",
        "target_flow_pct_t1_t21_clipped",
        "target_top_decile",
        "pl_lag1",
        "valid_day_ratio",
        "observed_business_days",
        "expected_business_days",
    ] + feature_columns
    model_df = model_df[keep_columns].copy()
    numeric_columns = model_df.select_dtypes(include=["number"]).columns
    model_df[numeric_columns] = model_df[numeric_columns].replace([np.inf, -np.inf], np.nan)

    summary = {
        "filters": {
            "is_model_ready_required": True,
            "min_pl_lag1": MIN_PL_LAG1,
            "min_valid_day_ratio": MIN_VALID_DAY_RATIO,
            "requires_full_history_windows": [21, 63, 126],
            "target_clip_bounds": [TARGET_CLIP_LOWER, TARGET_CLIP_UPPER],
        },
        "sample": {
            "rows": int(len(model_df)),
            "entities": int(model_df["ENTITY_KEY"].nunique()),
            "period_start": str(model_df["DT_COMPTC"].min().date()),
            "period_end": str(model_df["DT_COMPTC"].max().date()),
        },
        "target_distribution": {
            "mean_clipped": float(model_df["target_flow_pct_t1_t21_clipped"].mean()),
            "median_clipped": float(model_df["target_flow_pct_t1_t21_clipped"].median()),
            "p01_clipped": float(model_df["target_flow_pct_t1_t21_clipped"].quantile(0.01)),
            "p99_clipped": float(model_df["target_flow_pct_t1_t21_clipped"].quantile(0.99)),
            "top_decile_share": float(model_df["target_top_decile"].mean()),
        },
        "feature_columns": feature_columns,
    }

    model_df.to_parquet(OUTPUT_PATH, index=False)
    with open(SUMMARY_PATH, "w", encoding="utf-8") as file:
        json.dump(summary, file, ensure_ascii=False, indent=2)

    print(f"Features salvas em: {OUTPUT_PATH}")
    print(f"Resumo salvo em: {SUMMARY_PATH}")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    build_features()
