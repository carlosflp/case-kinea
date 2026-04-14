import json
import os

os.environ.setdefault("LOKY_MAX_CPU_COUNT", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.pipeline import Pipeline
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.preprocessing import OrdinalEncoder


BASE_DIR = os.path.dirname(os.path.dirname(__file__))
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")
ARTIFACTS_DIR = os.path.join(BASE_DIR, "artifacts")

INPUT_PATH = os.path.join(PROCESSED_DIR, "funds_features.parquet")
RESULTS_PATH = os.path.join(ARTIFACTS_DIR, "flow_baseline_results.json")
IMPORTANCE_PATH = os.path.join(ARTIFACTS_DIR, "flow_baseline_feature_importance.csv")
PREDICTIONS_PATH = os.path.join(ARTIFACTS_DIR, "flow_baseline_holdout_predictions.parquet")

TARGET_COLUMN = "target_flow_pct_t1_t21_clipped"
ID_COLUMNS = ["ENTITY_KEY", "CNPJ_FUNDO", "Denominacao_Social", "DT_COMPTC"]
TEST_DATES = 63
VALIDATION_DATES = 42
WALK_FORWARD_FOLDS = 3
WALK_FORWARD_TEST_DATES = 42
MIN_TRAIN_DATES = 168
PERMUTATION_SAMPLE_SIZE = 100_000
TRAIN_SAMPLE_SIZE = 400_000


def rmse(y_true, y_pred):
    return float(np.sqrt(mean_squared_error(y_true, y_pred)))


def build_pipeline(numeric_columns, categorical_columns):
    numeric_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
        ]
    )
    categorical_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            (
                "encoder",
                OrdinalEncoder(
                    handle_unknown="use_encoded_value",
                    unknown_value=-1,
                ),
            ),
        ]
    )

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", numeric_pipeline, numeric_columns),
            ("cat", categorical_pipeline, categorical_columns),
        ]
    )

    model = HistGradientBoostingRegressor(
        loss="squared_error",
        learning_rate=0.05,
        max_depth=6,
        max_iter=250,
        min_samples_leaf=200,
        l2_regularization=0.1,
        random_state=42,
    )

    return Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("model", model),
        ]
    )


def evaluate_predictions(y_true, y_pred):
    return {
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "rmse": rmse(y_true, y_pred),
    }


def make_date_splits(df):
    unique_dates = np.array(sorted(df["DT_COMPTC"].unique()))
    if len(unique_dates) <= TEST_DATES + VALIDATION_DATES + MIN_TRAIN_DATES:
        raise ValueError("A série temporal não possui datas suficientes para os splits definidos.")

    test_dates = set(unique_dates[-TEST_DATES:])
    validation_dates = set(unique_dates[-(TEST_DATES + VALIDATION_DATES):-TEST_DATES])
    train_dates = set(unique_dates[: -(TEST_DATES + VALIDATION_DATES)])

    train_mask = df["DT_COMPTC"].isin(train_dates)
    validation_mask = df["DT_COMPTC"].isin(validation_dates)
    test_mask = df["DT_COMPTC"].isin(test_dates)
    return train_mask, validation_mask, test_mask, unique_dates


def build_walk_forward_windows(unique_dates):
    windows = []
    cutoff = len(unique_dates) - TEST_DATES
    pre_holdout_dates = unique_dates[:cutoff]
    for fold_idx in range(WALK_FORWARD_FOLDS, 0, -1):
        test_end = len(pre_holdout_dates) - WALK_FORWARD_TEST_DATES * (fold_idx - 1)
        test_start = test_end - WALK_FORWARD_TEST_DATES
        if test_start < MIN_TRAIN_DATES:
            continue
        train_dates = set(pre_holdout_dates[:test_start])
        eval_dates = set(pre_holdout_dates[test_start:test_end])
        windows.append((train_dates, eval_dates))
    return windows


def main():
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)

    df = pd.read_parquet(INPUT_PATH)
    df["DT_COMPTC"] = pd.to_datetime(df["DT_COMPTC"])
    df = df.sort_values(["DT_COMPTC", "ENTITY_KEY"]).reset_index(drop=True)

    feature_columns = [column for column in df.columns if column not in ID_COLUMNS + [TARGET_COLUMN, "target_flow_t1_t21", "target_flow_pct_t1_t21", "target_top_decile", "pl_lag1"]]
    categorical_columns = [
        "anbima_bucket",
        "publico_alvo_bucket",
        "exclusivo_flag",
    ]
    numeric_columns = [column for column in feature_columns if column not in categorical_columns]
    df[numeric_columns] = df[numeric_columns].replace([np.inf, -np.inf], np.nan)

    train_mask, validation_mask, test_mask, unique_dates = make_date_splits(df)
    walk_forward_windows = build_walk_forward_windows(unique_dates)

    train_df = df.loc[train_mask].copy()
    validation_df = df.loc[validation_mask].copy()
    test_df = df.loc[test_mask].copy()
    fit_train_df = train_df.sample(
        n=min(len(train_df), TRAIN_SAMPLE_SIZE),
        random_state=42,
    )

    X_train = fit_train_df[feature_columns]
    y_train = fit_train_df[TARGET_COLUMN]
    X_validation = validation_df[feature_columns]
    y_validation = validation_df[TARGET_COLUMN]
    X_test = test_df[feature_columns]
    y_test = test_df[TARGET_COLUMN]

    baseline_validation_pred = np.repeat(y_train.median(), len(y_validation))
    baseline_test_pred = np.repeat(y_train.median(), len(y_test))

    pipeline = build_pipeline(numeric_columns=numeric_columns, categorical_columns=categorical_columns)
    pipeline.fit(X_train, y_train)

    validation_pred = pipeline.predict(X_validation)
    test_pred = pipeline.predict(X_test)

    walk_forward_results = []
    for fold_idx, (fold_train_dates, fold_eval_dates) in enumerate(walk_forward_windows, start=1):
        fold_train = df[df["DT_COMPTC"].isin(fold_train_dates)]
        fold_eval = df[df["DT_COMPTC"].isin(fold_eval_dates)]
        fold_fit_train = fold_train.sample(
            n=min(len(fold_train), TRAIN_SAMPLE_SIZE),
            random_state=42,
        )

        fold_pipeline = build_pipeline(
            numeric_columns=numeric_columns,
            categorical_columns=categorical_columns,
        )
        fold_pipeline.fit(
            fold_fit_train[feature_columns],
            fold_fit_train[TARGET_COLUMN],
        )
        fold_pred = fold_pipeline.predict(fold_eval[feature_columns])

        walk_forward_results.append(
            {
                "fold": fold_idx,
                "train_start": str(fold_train["DT_COMPTC"].min().date()),
                "train_end": str(fold_train["DT_COMPTC"].max().date()),
                "eval_start": str(fold_eval["DT_COMPTC"].min().date()),
                "eval_end": str(fold_eval["DT_COMPTC"].max().date()),
                "rows_train": int(len(fold_train)),
                "rows_train_fit": int(len(fold_fit_train)),
                "rows_eval": int(len(fold_eval)),
                "metrics": evaluate_predictions(fold_eval[TARGET_COLUMN], fold_pred),
            }
        )

    importance_sample = validation_df.sample(
        n=min(len(validation_df), PERMUTATION_SAMPLE_SIZE),
        random_state=42,
    )
    importance = permutation_importance(
        pipeline,
        importance_sample[feature_columns],
        importance_sample[TARGET_COLUMN],
        scoring="neg_mean_absolute_error",
        n_repeats=5,
        random_state=42,
    )
    importance_df = pd.DataFrame(
        {
            "feature": feature_columns,
            "importance_mean": importance.importances_mean,
            "importance_std": importance.importances_std,
        }
    ).sort_values("importance_mean", ascending=False)

    holdout_predictions = test_df[ID_COLUMNS + [TARGET_COLUMN]].copy()
    holdout_predictions["prediction"] = test_pred
    holdout_predictions["baseline_median_prediction"] = y_train.median()

    results = {
        "problem_type": "regression",
        "target_column": TARGET_COLUMN,
        "target_original_column": "target_flow_pct_t1_t21",
        "split_strategy": {
            "train_dates": int(train_df["DT_COMPTC"].nunique()),
            "validation_dates": int(validation_df["DT_COMPTC"].nunique()),
            "test_dates": int(test_df["DT_COMPTC"].nunique()),
            "train_period": [
                str(train_df["DT_COMPTC"].min().date()),
                str(train_df["DT_COMPTC"].max().date()),
            ],
            "validation_period": [
                str(validation_df["DT_COMPTC"].min().date()),
                str(validation_df["DT_COMPTC"].max().date()),
            ],
            "test_period": [
                str(test_df["DT_COMPTC"].min().date()),
                str(test_df["DT_COMPTC"].max().date()),
            ],
        },
        "sample": {
            "rows_total": int(len(df)),
            "rows_train": int(len(train_df)),
            "rows_train_fit": int(len(fit_train_df)),
            "rows_validation": int(len(validation_df)),
            "rows_test": int(len(test_df)),
            "entities_total": int(df["ENTITY_KEY"].nunique()),
        },
        "metrics": {
            "validation_baseline": evaluate_predictions(y_validation, baseline_validation_pred),
            "validation_model": evaluate_predictions(y_validation, validation_pred),
            "test_baseline": evaluate_predictions(y_test, baseline_test_pred),
            "test_model": evaluate_predictions(y_test, test_pred),
        },
        "walk_forward": walk_forward_results,
        "top_features": importance_df.head(15).to_dict(orient="records"),
    }

    with open(RESULTS_PATH, "w", encoding="utf-8") as file:
        json.dump(results, file, ensure_ascii=False, indent=2)
    importance_df.to_csv(IMPORTANCE_PATH, index=False)
    holdout_predictions.to_parquet(PREDICTIONS_PATH, index=False)

    print(f"Resultados salvos em: {RESULTS_PATH}")
    print(f"Importâncias salvas em: {IMPORTANCE_PATH}")
    print(f"Predições holdout salvas em: {PREDICTIONS_PATH}")
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
