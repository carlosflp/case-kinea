# case-kinea

Pipeline reprodutível para o case com dados públicos da CVM, cobrindo:
- download dos informes diários e do cadastro de classes
- consolidação e limpeza
- definição do escopo da classe `Ações`
- validação manual de amostras
- construção de features sem vazamento
- baseline com split temporal

## Estrutura

- `case.md`: briefing do desafio.
- `cvm-case/data/raw_csv/download_csv.py`: download dos informes mensais da CVM e do `registro_classe.csv`.
- `cvm-case/data/processed/consolidar_csv.py`: consolida o informe diário com o cadastro.
- `cvm-case/data/processed/build_scope_dataset.py`: aplica o recorte do case, trata calendário B3 e cria o target.
- `cvm-case/data/processed/validate_manual_samples.py`: confere 2 fundos x 3 datas no bruto.
- `cvm-case/modeling/build_features_dataset.py`: gera a base de features históricas sem vazamento.
- `cvm-case/modeling/train_flow_baseline.py`: treina e avalia o baseline temporal.
- `cvm-case/notebooks/eda.ipynb`: exploração inicial da base e sanity checks.

## Ambiente

Use uma virtualenv com Python 3.14 e instale:

```bash
python -m pip install -r requirements.txt
```

## Execução fim a fim

Na raiz do projeto:

```bash
python run_pipeline.py
```

Se quiser pular o download e usar os arquivos já existentes:

```bash
python run_pipeline.py --skip-download
```

Execução manual por etapas:

```bash
python cvm-case/data/raw_csv/download_csv.py
python cvm-case/data/processed/consolidar_csv.py
python cvm-case/data/processed/build_scope_dataset.py
python cvm-case/data/processed/validate_manual_samples.py
python cvm-case/modeling/build_features_dataset.py
python cvm-case/modeling/train_flow_baseline.py
```

## Regras principais do pipeline

- Fonte: apenas dados públicos da CVM.
- Unidade de análise: `ENTITY_KEY = CNPJ_FUNDO + ID_SUBCLASSE`.
- Escopo: classe `Ações`, situação `Em Funcionamento Normal`, mínimo de 50 observações.
- Calendário: uso explícito do calendário de negociação da `B3` para tratar feriados e datas sem pregão.
- Qualidade temporal mínima por entidade:
  - `min_valid_business_days = 50`
  - `valid_day_ratio >= 0.80`
- Target: fluxo futuro acumulado de `T+1` a `T+21` dias úteis, normalizado por `PL` defasado em 1 dia.
- Anti-vazamento: features históricas usam defasagem mínima de 1 dia útil.
- Filtro adicional para modelagem: `pl_lag1 >= 1.000.000`.
- Target de regressão clipado em `[-1, 1]` para reduzir o efeito de caudas extremas.

## Artefatos gerados

Em `cvm-case/data/processed/`:
- `funds_raw.parquet`
- `funds_raw_quality.json`
- `funds_scope.parquet`
- `funds_scope_summary.json`
- `manual_validation_samples.json`
- `funds_features.parquet`
- `funds_features_summary.json`

Em `cvm-case/artifacts/`:
- `flow_baseline_results.json`
- `flow_baseline_feature_importance.csv`
- `flow_baseline_holdout_predictions.parquet`

## Resultado atual do baseline

Problema escolhido: regressão.

Amostra final de features:
- 1.185.572 linhas
- 3.725 entidades
- período de `2024-10-29` a `2026-03-11`

Qualidade de calendário no escopo:
- `non_business_rows_removed = 14.689`
- `median_valid_day_ratio = 1.0`
- `p05_valid_day_ratio = 0.9979`

Split temporal:
- treino: `2024-10-29` a `2025-10-08`
- validação: `2025-10-09` a `2025-12-08`
- teste: `2025-12-09` a `2026-03-11`

Métricas:
- validação baseline: `MAE 0.03574`, `RMSE 0.10258`
- validação modelo: `MAE 0.03783`, `RMSE 0.09779`
- teste baseline: `MAE 0.03459`, `RMSE 0.10152`
- teste modelo: `MAE 0.03752`, `RMSE 0.09859`

Leitura rápida:
- o baseline mediano segue forte em `MAE`, o que é esperado com target muito concentrado em zero
- o modelo melhora `RMSE`, sugerindo captura melhor das caudas e dos casos com fluxo mais intenso

Principais drivers no holdout:
- `flow_pct_63d_sum`
- `ex_flow_return_5d_mean`
- `ret_5d`
- `vol_63d`
- `flow_pct_5d_sum`
- `log_nr_cotst_lag1`
- `log_pl_lag1`
- `ex_flow_return_21d_mean`
- `anbima_bucket`
- `flow_pct_21d_sum`
- `publico_alvo_bucket`
- `nr_cotst_change_21d`
- `valid_day_ratio`

## Próximos passos

Como evolução natural do baseline atual, um caminho promissor seria testar uma modelagem em dois estágios para lidar melhor com a natureza do target, que é fortemente concentrado em zero e apresenta caudas relevantes. Nesse desenho, o primeiro estágio estimaria a probabilidade de ocorrência de um evento relevante de fluxo, enquanto o segundo estágio modelaria a magnitude condicional desse fluxo. Essa abordagem pode ser mais aderente ao problema do que uma regressão única, especialmente para capturar melhor os casos de captação ou resgate mais intensos, mantendo uma avaliação temporal consistente em comparação com o baseline atual.

