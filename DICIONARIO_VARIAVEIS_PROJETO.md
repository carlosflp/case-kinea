# Dicionário de Variáveis do Projeto

## Como ler este documento

Este dicionário está organizado por etapa da pipeline, porque as variáveis mudam de função ao longo do projeto.

Blocos:

- base bruta consolidada: `funds_raw.parquet`
- base de escopo do case: `funds_scope.parquet`
- base final de modelagem: `funds_features.parquet`
- artefatos de resultado do modelo
- resumos em JSON

Quando a variável já aparece em uma etapa anterior, mas continua existindo depois, a explicação principal fica na primeira vez em que ela surge.

---

## 1. Variáveis da base bruta consolidada

Arquivo:

- `cvm-case/data/processed/funds_raw.parquet`

Essas variáveis vêm da junção entre o informe diário da CVM e o cadastro de classes.

### 1.1. Identificação e origem

- `TP_FUNDO_CLASSE`
  - tipo do registro no informe diário.
  - foi usado também como critério de preferência na deduplicação, priorizando `CLASSES - FIF`.

- `CNPJ_FUNDO_CLASSE`
  - CNPJ da classe no arquivo bruto, com pontuação.

- `ID_SUBCLASSE`
  - identificador da subclasse.
  - quando ausente, a pipeline trata como `SEM_SUBCLASSE` ao montar a chave da entidade.

- `DT_COMPTC`
  - data de competência do registro.
  - representa o dia a que os valores econômicos se referem.

- `source_file`
  - nome do CSV mensal de origem.
  - útil para rastrear de qual arquivo bruto a linha foi lida.

- `CNPJ_FUNDO`
  - CNPJ da classe já normalizado, sem pontuação.
  - é a chave usada para merge com o cadastro.

- `ENTITY_KEY`
  - identificador analítico da entidade.
  - formado por `CNPJ_FUNDO + "::" + ID_SUBCLASSE`.
  - é a unidade principal de série temporal do projeto.

### 1.2. Variáveis econômicas do informe diário

- `VL_TOTAL`
  - valor total da carteira.
  - representa o valor total dos ativos da classe.

- `VL_QUOTA`
  - valor unitário da cota.
  - informa quanto vale uma cota do fundo naquela data.

- `VL_PATRIM_LIQ`
  - patrimônio líquido.
  - é a principal medida de tamanho econômico do fundo no dia.

- `CAPTC_DIA`
  - captação do dia.
  - volume de entradas de recursos no dia.

- `RESG_DIA`
  - resgate do dia.
  - volume de saídas de recursos no dia.

- `NR_COTST`
  - número de cotistas.
  - aproxima o tamanho da base de investidores.

### 1.3. Identificadores do cadastro

- `ID_Registro_Fundo`
  - identificador cadastral do fundo no registro.

- `ID_Registro_Classe`
  - identificador cadastral da classe.
  - também é usado como proxy de match bem-sucedido entre informe e cadastro.

- `CNPJ_Classe`
  - CNPJ da classe no cadastro, normalmente com pontuação.

- `Codigo_CVM`
  - código de identificação na CVM.

### 1.4. Datas cadastrais

- `Data_Registro`
  - data de registro da classe.

- `Data_Constituicao`
  - data de constituição da classe.

- `Data_Inicio`
  - data de início de funcionamento ou início da série.

- `Data_Inicio_Situacao`
  - data a partir da qual a situação cadastral vigente passou a valer.

- `Data_Patrimonio_Liquido`
  - data de referência do patrimônio líquido informado no cadastro.

### 1.5. Classificação e enquadramento

- `Tipo_Classe`
  - tipo cadastral da classe.

- `Denominacao_Social`
  - nome do fundo ou da classe.

- `Situacao`
  - situação cadastral da classe.
  - no recorte do case, foi exigido `Em Funcionamento Normal`.

- `Classificacao`
  - classificação principal da classe.
  - no recorte do case, foi exigido `Ações`.

- `Indicador_Desempenho`
  - indicador ou referência de desempenho associada ao produto, quando disponível.

- `Classe_Cotas`
  - classificação relacionada à estrutura de cotas.

- `Classificacao_Anbima`
  - bucket de classificação ANBIMA do produto.

- `Tributacao_Longo_Prazo`
  - indicador relacionado ao regime tributário de longo prazo.

- `Entidade_Investimento`
  - informa enquadramento como entidade de investimento, quando aplicável.

- `Permitido_Aplicacao_CemPorCento_Exterior`
  - flag indicando se é permitido aplicar 100% no exterior.

- `Classe_ESG`
  - classificação ESG da classe, quando houver.

- `Forma_Condominio`
  - estrutura condominial do fundo ou classe.

- `Exclusivo`
  - indica se o fundo é exclusivo.

- `Publico_Alvo`
  - público-alvo do produto.

### 1.6. Prestadores e cadastro complementar

- `Patrimonio_Liquido`
  - patrimônio líquido vindo do cadastro.
  - diferente de `VL_PATRIM_LIQ`, que vem do informe diário.

- `CNPJ_Auditor`
  - CNPJ do auditor.

- `Auditor`
  - nome do auditor.

- `CNPJ_Custodiante`
  - CNPJ do custodiante.

- `Custodiante`
  - nome do custodiante.

- `CNPJ_Controlador`
  - CNPJ do controlador.

- `Controlador`
  - nome do controlador.

- `registry_non_null_score`
  - score criado pela pipeline para deduplicar o cadastro.
  - conta quantos campos não nulos a linha possui.
  - quanto maior, mais completa era a linha escolhida.

---

## 2. Variáveis da base de escopo do case

Arquivo:

- `cvm-case/data/processed/funds_scope.parquet`

Essa base já contém apenas o universo do case, com recorte temático e tratamento de calendário.

### 2.1. Variáveis herdadas da etapa anterior

As seguintes variáveis já foram explicadas acima e seguem com o mesmo significado:

- `CNPJ_FUNDO`
- `ENTITY_KEY`
- `ID_SUBCLASSE`
- `DT_COMPTC`
- `Denominacao_Social`
- `Situacao`
- `Classificacao`
- `VL_TOTAL`
- `VL_QUOTA`
- `VL_PATRIM_LIQ`
- `CAPTC_DIA`
- `RESG_DIA`
- `NR_COTST`
- `Data_Registro`
- `Data_Constituicao`
- `Data_Inicio`
- `Classe_Cotas`
- `Classificacao_Anbima`
- `Exclusivo`
- `Publico_Alvo`

### 2.2. Variáveis criadas na etapa de escopo

- `is_business_day`
  - flag que indica se `DT_COMPTC` é dia útil de mercado.
  - usada para remover observações em datas sem pregão.

- `classificacao_norm`
  - versão normalizada de `Classificacao`.
  - remove acentos, padroniza caixa e espaços para facilitar filtros.

- `situacao_norm`
  - versão normalizada de `Situacao`.
  - usada para aplicar o filtro de `Em Funcionamento Normal`.

- `observed_business_days`
  - número de dias úteis efetivamente observados para a entidade dentro do intervalo de datas da sua série.

- `expected_business_days`
  - número de dias úteis esperados entre a primeira e a última data da entidade.

- `valid_day_ratio`
  - cobertura temporal da série:
  - `observed_business_days / expected_business_days`

- `flow_dia`
  - fluxo líquido diário.
  - calculado como:
  - `CAPTC_DIA - RESG_DIA`

- `pl_lag1`
  - patrimônio líquido defasado em 1 dia útil.
  - usado para normalizar o target e algumas features.

- `ret_1d`
  - retorno diário da cota.
  - calculado como variação percentual de `VL_QUOTA`.

- `target_flow_t1_t21`
  - fluxo futuro acumulado de `T+1` a `T+21` dias úteis.
  - é a soma do `flow_dia` nas 21 observações futuras.

- `target_flow_pct_t1_t21`
  - versão percentual do target.
  - calculado como:
  - `target_flow_t1_t21 / pl_lag1`

- `is_model_ready`
  - flag que indica se a linha está apta para entrar na modelagem básica.
  - exige:
  - `pl_lag1 > 0`
  - `target_flow_t1_t21` não nulo
  - `VL_QUOTA > 0`
  - `VL_PATRIM_LIQ > 0`

---

## 3. Variáveis da base final de modelagem

Arquivo:

- `cvm-case/data/processed/funds_features.parquet`

Essa é a base usada para treinar o modelo.

### 3.1. Variáveis de identificação

- `ENTITY_KEY`
  - identificador da entidade analítica.

- `CNPJ_FUNDO`
  - CNPJ normalizado da classe.

- `Denominacao_Social`
  - nome do fundo.

- `DT_COMPTC`
  - data da observação.

### 3.2. Variáveis de target e elegibilidade

- `target_flow_t1_t21`
  - fluxo futuro acumulado entre `T+1` e `T+21` dias úteis, em valor absoluto.

- `target_flow_pct_t1_t21`
  - fluxo futuro acumulado relativo ao `pl_lag1`.

- `target_flow_pct_t1_t21_clipped`
  - target de regressão clipado no intervalo `[-1, 1]`.
  - usado no treinamento do modelo.

- `target_top_decile`
  - flag indicando se a observação está no decil superior do target clipado na data.
  - útil para análises alternativas e possíveis extensões de classificação.

- `pl_lag1`
  - patrimônio líquido defasado em 1 dia útil.
  - reaparece aqui como variável auxiliar importante.

- `valid_day_ratio`
  - razão de dias válidos da entidade.

- `observed_business_days`
  - dias úteis observados da entidade.

- `expected_business_days`
  - dias úteis esperados da entidade.

### 3.3. Variáveis de porte e idade do fundo

- `log_pl_lag1`
  - log do patrimônio líquido defasado.
  - aproxima o porte econômico do fundo em escala mais estável.

- `log_vl_total_lag1`
  - log do valor total da carteira defasado.

- `log_nr_cotst_lag1`
  - log do número de cotistas defasado.
  - aproxima o tamanho da base de investidores.

- `fund_age_years`
  - idade do fundo em anos.
  - construída a partir da melhor data inicial disponível.

### 3.4. Variáveis de retorno

- `ret_5d`
  - retorno acumulado da cota em 5 dias úteis, com defasagem mínima de 1 dia.

- `ret_21d`
  - retorno acumulado em 21 dias úteis.

- `ret_63d`
  - retorno acumulado em 63 dias úteis.

- `ret_126d`
  - retorno acumulado em 126 dias úteis.

- `ret_21d_rel_class`
  - retorno de 21 dias do fundo menos a mediana do retorno de 21 dias do conjunto na mesma data.

- `ret_63d_rel_class`
  - retorno de 63 dias do fundo menos a mediana do retorno de 63 dias do conjunto na mesma data.

- `ret_zscore_21d`
  - z-score do retorno recente frente à média e ao desvio padrão de 21 dias.
  - mede quão extremo está o retorno recente do fundo.

### 3.5. Variáveis de volatilidade e perda relativa

- `vol_21d`
  - desvio padrão dos retornos diários em 21 dias úteis.

- `vol_63d`
  - desvio padrão dos retornos diários em 63 dias úteis.

- `vol_21d_rel_class`
  - volatilidade de 21 dias do fundo menos a mediana da volatilidade do conjunto na data.

- `drawdown_63d`
  - drawdown em 63 dias.
  - mede a perda relativa em relação ao pico recente.

- `drawdown_126d`
  - drawdown em 126 dias.

### 3.6. Variáveis de fluxo histórico

- `flow_pct_5d_sum`
  - soma do fluxo percentual diário nos últimos 5 dias úteis.

- `flow_pct_21d_sum`
  - soma do fluxo percentual diário nos últimos 21 dias úteis.

- `flow_pct_63d_sum`
  - soma do fluxo percentual diário nos últimos 63 dias úteis.

- `flow_pct_21d_rel_class`
  - fluxo percentual de 21 dias do fundo menos a mediana do conjunto na data.

### 3.7. Variáveis de retorno ex-fluxo

- `ex_flow_return_5d_mean`
  - média do retorno ex-fluxo em 5 dias úteis.
  - tenta separar desempenho do fundo do efeito mecânico de captação e resgate.

- `ex_flow_return_21d_mean`
  - média do retorno ex-fluxo em 21 dias úteis.

- `ex_flow_return_63d_mean`
  - média do retorno ex-fluxo em 63 dias úteis.

### 3.8. Variáveis de base de cotistas

- `nr_cotst_change_21d`
  - variação percentual do número de cotistas em 21 dias úteis.

### 3.9. Variáveis temporais

- `weekday`
  - dia da semana numérico.

- `month`
  - mês numérico.

- `is_month_end`
  - flag de fim de mês.

- `is_quarter_end`
  - flag de fim de trimestre.

- `is_january`
  - flag indicando janeiro.

### 3.10. Variáveis categóricas de perfil

- `anbima_bucket`
  - agrupamento das principais categorias ANBIMA.
  - as categorias menos frequentes são agrupadas em `Outras`.

- `publico_alvo_bucket`
  - bucket do público-alvo.
  - quando ausente, recebe `Nao Informado`.

- `exclusivo_flag`
  - bucket para o campo `Exclusivo`.
  - quando ausente, recebe `Nao Informado`.

---

## 4. Variáveis auxiliares criadas internamente na engenharia de features

Essas variáveis aparecem no script de construção de features e ajudam a gerar a base final, mesmo quando não são mantidas no parquet final.

Script:

- `cvm-case/modeling/build_features_dataset.py`

- `fund_start_date`
  - melhor estimativa da data de início do fundo.
  - considera `Data_Constituicao`, `Data_Inicio`, `Data_Registro` e primeira aparição na base.

- `fund_age_days`
  - idade do fundo em dias.

- `quota_lag1`
  - valor da cota defasado em 1 dia útil.

- `vl_total_lag1`
  - valor total da carteira defasado em 1 dia útil.

- `nr_cotst_lag1`
  - número de cotistas defasado em 1 dia útil.

- `flow_pct_1d`
  - fluxo diário relativo ao `pl_lag1`.

- `ex_flow_return_1d`
  - retorno diário ex-fluxo.
  - aproximado por:
  - `(VL_PATRIM_LIQ - pl_lag1 - flow_dia) / pl_lag1`

- `class_median_ret_21d`
  - mediana cross-section de `ret_21d` na data.

- `class_median_ret_63d`
  - mediana cross-section de `ret_63d` na data.

- `class_median_vol_21d`
  - mediana cross-section de `vol_21d` na data.

- `class_median_flow_pct_21d_sum`
  - mediana cross-section de `flow_pct_21d_sum` na data.

- `has_full_history`
  - flag usada para manter apenas linhas com histórico completo nas janelas mínimas exigidas.

---

## 5. Variáveis dos artefatos de resultados do modelo

### 5.1. `flow_baseline_feature_importance.csv`

Arquivo:

- `cvm-case/artifacts/flow_baseline_feature_importance.csv`

- `feature`
  - nome da variável avaliada.

- `importance_mean`
  - importância média por permutation importance.
  - quanto maior, maior o impacto da variável na performance quando ela é embaralhada.

- `importance_std`
  - desvio padrão da importância nas repetições da permutation importance.

### 5.2. `flow_baseline_holdout_predictions.parquet`

Arquivo:

- `cvm-case/artifacts/flow_baseline_holdout_predictions.parquet`

- `ENTITY_KEY`
  - entidade da previsão.

- `CNPJ_FUNDO`
  - CNPJ da classe.

- `Denominacao_Social`
  - nome do fundo.

- `DT_COMPTC`
  - data da observação de holdout.

- `target_flow_pct_t1_t21_clipped`
  - valor real do target no holdout.

- `prediction`
  - previsão do modelo.

- `baseline_median_prediction`
  - previsão do baseline ingênuo, igual à mediana do target no treino.

### 5.3. `flow_baseline_results.json`

Arquivo:

- `cvm-case/artifacts/flow_baseline_results.json`

Campos principais:

- `problem_type`
  - tipo do problema.
  - no projeto atual: `regression`.

- `target_column`
  - coluna de target usada no modelo.

- `target_original_column`
  - versão original do target antes do clipping.

#### Split

- `train_dates`
  - quantidade de datas no treino.

- `validation_dates`
  - quantidade de datas na validação.

- `test_dates`
  - quantidade de datas no teste.

- `train_period`
  - início e fim do período de treino.

- `validation_period`
  - início e fim do período de validação.

- `test_period`
  - início e fim do período de teste.

#### Amostra

- `rows_total`
  - número total de linhas da base final de modelagem.

- `rows_train`
  - linhas no treino.

- `rows_train_fit`
  - subconjunto do treino efetivamente usado no ajuste do modelo.

- `rows_validation`
  - linhas na validação.

- `rows_test`
  - linhas no teste.

- `entities_total`
  - entidades totais da base final.

#### Métricas

- `validation_baseline.mae`
  - MAE do baseline na validação.

- `validation_baseline.rmse`
  - RMSE do baseline na validação.

- `validation_model.mae`
  - MAE do modelo na validação.

- `validation_model.rmse`
  - RMSE do modelo na validação.

- `test_baseline.mae`
  - MAE do baseline no teste.

- `test_baseline.rmse`
  - RMSE do baseline no teste.

- `test_model.mae`
  - MAE do modelo no teste.

- `test_model.rmse`
  - RMSE do modelo no teste.

#### Walk-forward

- `fold`
  - índice da janela walk-forward.

- `train_start`
  - início do treino daquele fold.

- `train_end`
  - fim do treino daquele fold.

- `eval_start`
  - início da janela de avaliação daquele fold.

- `eval_end`
  - fim da janela de avaliação daquele fold.

- `rows_train`
  - linhas do treino naquele fold.

- `rows_train_fit`
  - linhas efetivamente usadas no ajuste naquele fold.

- `rows_eval`
  - linhas da janela de avaliação naquele fold.

- `metrics.mae`
  - MAE do fold.

- `metrics.rmse`
  - RMSE do fold.

#### Top features

- `top_features.feature`
  - nome da variável mais relevante.

- `top_features.importance_mean`
  - importância média da variável.

- `top_features.importance_std`
  - desvio da importância.

---

## 6. Variáveis dos resumos em JSON

### 6.1. `funds_raw_quality.json`

Arquivo:

- `cvm-case/data/processed/funds_raw_quality.json`

#### Fonte

- `daily_informe_used`
  - indica que o informe diário foi usado.

- `registry_used`
  - indica que o cadastro foi usado.

#### Qualidade do informe diário

- `duplicate_rows_before_cleaning`
  - linhas duplicadas antes da limpeza.

- `duplicate_keys_before_cleaning`
  - chaves duplicadas por entidade e data antes da limpeza.

- `conflicting_duplicate_keys`
  - chaves duplicadas com conflito em métricas econômicas.

#### Qualidade do cadastro

- `registry_rows_before_dedup`
  - número de linhas do cadastro antes da deduplicação.

- `registry_duplicate_keys_before_cleaning`
  - número de CNPJs duplicados no cadastro antes da limpeza.

- `registry_rows_after_dedup`
  - linhas do cadastro após deduplicação.

#### Merge

- `rows_after_merge`
  - linhas após merge entre informe e cadastro.

- `funds_after_merge`
  - CNPJs distintos após merge.

- `merge_hit_rate`
  - taxa de linhas com match no cadastro.

- `rows_without_registry_match`
  - linhas sem correspondência no cadastro.

#### Nulos após merge

- `VL_QUOTA`
  - quantidade de nulos em `VL_QUOTA`.

- `VL_PATRIM_LIQ`
  - quantidade de nulos em `VL_PATRIM_LIQ`.

- `CAPTC_DIA`
  - quantidade de nulos em `CAPTC_DIA`.

- `RESG_DIA`
  - quantidade de nulos em `RESG_DIA`.

- `Classificacao`
  - quantidade de nulos em `Classificacao`.

- `Situacao`
  - quantidade de nulos em `Situacao`.

### 6.2. `funds_scope_summary.json`

Arquivo:

- `cvm-case/data/processed/funds_scope_summary.json`

#### Definição do escopo

- `classificacao`
  - classificação exigida no universo do case.

- `situacao`
  - situação exigida no universo do case.

- `min_observations_per_fund`
  - mínimo de observações por fundo.

- `min_valid_business_days`
  - mínimo de dias úteis válidos.

- `min_valid_day_ratio`
  - razão mínima de cobertura temporal.

- `target`
  - descrição textual do target.

#### Amostra

- `rows_after_scope_filter`
  - linhas após filtro do universo.

- `rows_model_ready`
  - linhas aptas para modelagem básica.

- `eligible_entities`
  - entidades elegíveis.

- `eligible_class_cnpjs`
  - CNPJs elegíveis.

- `period_start`
  - início do período final do escopo.

- `period_end`
  - fim do período final do escopo.

#### Qualidade de calendário

- `non_business_rows_removed`
  - linhas removidas por caírem em dias não úteis.

- `median_valid_day_ratio`
  - mediana da cobertura temporal.

- `p05_valid_day_ratio`
  - percentil 5 da cobertura temporal.

- `eligible_entities_after_calendar_filter`
  - número de entidades após aplicar o filtro de calendário.

#### Distribuição do target

- `median`
  - mediana do target percentual.

- `mean_clipped_1`
  - média do target após clipping em `[-1, 1]`.

- `p01`
  - percentil 1 do target.

- `p05`
  - percentil 5 do target.

- `p95`
  - percentil 95 do target.

- `p99`
  - percentil 99 do target.

- `share_abs_target_gt_1`
  - proporção de linhas com `|target| > 1`.

### 6.3. `funds_features_summary.json`

Arquivo:

- `cvm-case/data/processed/funds_features_summary.json`

#### Filtros

- `is_model_ready_required`
  - exige `is_model_ready = True`.

- `min_pl_lag1`
  - valor mínimo de patrimônio líquido defasado.

- `min_valid_day_ratio`
  - mínimo de cobertura temporal.

- `requires_full_history_windows`
  - janelas de histórico exigidas para manter uma linha.

- `target_clip_bounds`
  - limites do clipping do target.

#### Amostra

- `rows`
  - linhas na base final de modelagem.

- `entities`
  - entidades na base final.

- `period_start`
  - início do período final da base de features.

- `period_end`
  - fim do período final da base de features.

#### Distribuição do target

- `mean_clipped`
  - média do target clipado.

- `median_clipped`
  - mediana do target clipado.

- `p01_clipped`
  - percentil 1 do target clipado.

- `p99_clipped`
  - percentil 99 do target clipado.

- `top_decile_share`
  - proporção de observações no decil superior do target.

- `feature_columns`
  - lista das colunas usadas como features no modelo.