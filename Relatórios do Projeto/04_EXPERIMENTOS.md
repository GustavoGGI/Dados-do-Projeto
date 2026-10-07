# 04 — Experimentos

Histórico do que foi tentado, o que cada tentativa ensinou, e o que
os números significam.

---

# Parte A — Smoke test

## 1. O que foi

- Split aleatório dentro de 2025.
- Alvo: `ABANDONO_FUN_AF_T1`.
- Só escolas públicas, alvo não nulo.
- 243 escolas (194 treino / 49 teste).

## 2. Resultados

| Modelo | MAE | RMSE | R² |
|---|---|---|---|
| Ridge | 2,60 | 4,09 | 0,204 |
| RandomForest | 2,49 | 3,98 | 0,245 |
| HistGradientBoosting | 2,44 | 3,82 | **0,303** |

## 3. Como interpretar

- **Objetivo:** validar o pipeline, não medir performance.
- **O R² 0,303 é enganoso.** Split aleatório dentro do mesmo ano é
  muito mais fácil que prever um ano futuro.
- **Não usar como resultado científico.** Só confirma que o pipeline
  roda de ponta a ponta.

---

# Parte B — v1_old

## 4. O que foi

- Pipeline metodologicamente correto:
  - Filtra `REDE_PUBLICA == 1`.
  - Usa `Pipeline` do sklearn.
  - `OneHotEncoder` para categóricas.
  - Split temporal (treino 2020–2023, validação 2024, teste 2025).
  - Imputação dentro do pipeline.

## 5. Resultados

### Anos finais

| Modelo | MAE_val | RMSE_val | R²_val | MAE_teste | RMSE_teste | R²_teste |
|---|---|---|---|---|---|---|
| Ridge | 2,96 | 3,76 | −0,001 | 2,89 | 3,85 | **0,158** |
| RandomForest | 2,99 | 3,90 | −0,078 | 2,92 | 3,84 | **0,162** |
| HistGradientBoosting | 3,05 | 3,99 | −0,131 | 3,14 | 4,22 | −0,012 |

### Ensino médio

**Não disponível.** O notebook do v1_old só mostra os resultados de
anos finais; o ensino médio não foi executado (ou a saída não foi
preservada). Pendente: pedir ao Gustavo para rodar.

## 6. O que os números significam

### 6.1 R² negativo na validação de 2024

- Significa que em 2024 o modelo foi **pior que prever a média**.
- **Isso é informação importante, não resultado a esconder.**
- Mostra **instabilidade temporal**: o modelo aprendeu padrões de
  anos anteriores que não se aplicam a 2024.

### 6.2 R² 0,162 no teste de 2025

- Melhor que em 2024, mas modesto.
- Explica ~16% da variância além da média.

### 6.3 Ridge ≈ RandomForest ≈ HGB

- Sugere relações predominantemente lineares nos dados.
- Ou que o tamanho da amostra limita a vantagem de métodos não
  lineares.

## 7. Conclusão

- **Pipeline correto.**
- **Instabilidade temporal real.** Walk-forward revelaria isso
  melhor.
- **R² modesto mas real.**

---

# Parte C — v1 atual

## 8. O que foi

- Mesmos dados.
- **4 problemas metodológicos:**
  1. Não filtra escolas públicas.
  2. Imputação quebrada por tipo (só pega `float64`/`int64`).
  3. Imputação antes do split (leakage sutil).
  4. Categóricas descartadas (`select_dtypes`).

## 9. Resultados

Os modelos são avaliados por ano-alvo. O split temporal do v1 atual usa:

- Treino: 2020 a 2023.
- Teste: 2024 (alvo = 2025).

### Anos finais

| Modelo | MAE | RMSE | R² |
|---|---|---|---|
| RandomForest | 2,58 | 3,72 | 0,1843 |
| GradientBoosting | **2,46** | **3,69** | **0,2011** |

Melhor modelo: GradientBoosting (R² 0,2011).

### Ensino médio

| Modelo | MAE | RMSE | R² |
|---|---|---|---|
| RandomForest | **4,11** | **6,13** | **0,1214** |
| GradientBoosting | 4,13 | 6,23 | 0,0907 |

Melhor modelo: RandomForest (R² 0,1214).

### Comparação entre etapas

- **Anos finais** tem erro absoluto menor (MAE 2,46–2,58 p.p.) que
  **ensino médio** (MAE 4,11–4,13 p.p.).
- **Anos finais** tem R² maior (0,18–0,20) que **ensino médio**
  (0,09–0,12).
- Coerente com o que se sabe: o abandono no EM é mais volátil e mais
  alto (média 6,19) que nos anos finais (média 2,82).

## 10. Como interpretar

- **Números inflados** pelas 4 falhas.
- **Não comparar diretamente com v1_old** — o desenho é diferente.
- **Não usar como resultado científico** enquanto não corrigir.

## 11. Comparação rápida

| | v1_old | v1 atual |
|---|---|---|
| Filtra públicas | Sim | Não |
| Pipeline (sklearn) | Sim | Não |
| Categóricas | Sim | Não |
| Imputação dentro do pipeline | Sim | Não |
| Split | Temporal (treino 2020–2023, val 2024, teste 2025) | Temporal (treino 2020–2023, teste 2024) |
| Alvo do teste | 2025 | 2025 |
| R² AF (melhor) | 0,162 (RandomForest) | 0,2011 (GradientBoosting) |
| R² EM (melhor) | não disponível | 0,1214 (RandomForest) |

**Observações:**

- O v1 atual **não inclui validação separada** — só treino e teste.
- O v1_old **não mostrou resultado de EM** no notebook anexado.
- Apesar do R² aparentemente melhor do v1 atual, ele é
  metodologicamente **pior** (4 problemas em §8).
- **Não comparar diretamente** os números dos dois — os desenhos são
  diferentes.

---

# Parte D — Análise crítica do orientador

## 12. Origem

Relatório gerado por LLM pago pelo orientador, com acesso aos dados
do projeto. Analisou os notebooks.

## 13. Pontos aceitos

- **R² não é acurácia.** Correta distinção.
- **RMSE > MAE indica outliers** — precisa análise específica.
- **TDI como variável principal** é achado, não só métrica.
- **Recall@K é mais útil que acurácia** para priorização.
- **Baseline de persistência falta.**
- **O R² 0,303 do smoke test é enganoso.**
- **Instabilidade temporal é questão científica, não bug.**
- **v1_old é metodologicamente melhor que v1 atual.**

## 14. Pontos a discutir

- **Pico de 2022:** o relatório não trata explicitamente. Precisa
  decisão com o orientador.
- **Uso de features do fundamental no modelo EM:** o relatório sugere
  remover. Não é unânime.
- **Categóricas:** o relatório é claro sobre incluir. Concordo.

## 15. Sequência recomendada pelo orientador

1. Somente escolas públicas.
2. Corrigir imputação e usar Pipeline.
3. Incorporar categóricas corretamente.
4. Retirar leakage.
5. Acrescentar enriquecimento (indígena, localização, HAD, IED
   2019/2020, Pé-de-Meia).
6. Criar baseline de persistência.
7. Executar walk-forward.
8. Manter regressão (MAE/RMSE/R²).
9. Acrescentar classificação (precisão, recall, F1, ROC-AUC, PR-AUC).
10. Acrescentar Recall@20/30/50.

**Concordo com a sequência.** Ver `07_PLANOS.md`.

---

# Parte E — Achados científicos

## 16. TDI é a variável mais importante

Nos três casos analisados (v1_old AF, v1 atual AF, v1 atual EM), a TDI
aparece em primeiro lugar. Mas as importâncias vêm de **modelos
diferentes** — ver separação abaixo.

### v1_old — anos finais (RandomForest)

| Variável | Importância |
|---|---|
| `TDI_FUN_TOTAL` | 16,90% |
| `ABANDONO_FUN_AF_DELTA1` | 5,26% |
| `TDI_FUN_AF_DELTA1` | 5,25% |
| `TDI_MED_TOTAL` | 5,17% |
| `TDI_FUN_AF` | 4,67% |

**Nota metodológica:** o v1_old usou **todas** as features numéricas
no modelo AF, inclusive as do EM. Isso contraria a decisão **D15**
("cada modelo só vê features da sua etapa"). Explica a presença de
`TDI_MED_TOTAL` no top 5 do modelo AF.

### v1 atual — anos finais (GradientBoosting)

| Variável | Importância |
|---|---|
| `TDI_FUN_TOTAL` | 20,08% |
| `TDI_FUN_AF` | 10,22% |
| `ABANDONO_FUN` | 9,12% |
| `REPROVACAO_FUN_AF` | 8,38% |
| `TDI_FUN_AF_DELTA1` | 5,11% |

### v1 atual — ensino médio (RandomForest)

| Variável | Importância |
|---|---|
| `TDI_MED_TOTAL` | 19,47% |
| `ATU_MED_TOTAL` | 10,16% |
| `ABANDONO_MED_DELTA1` | 9,80% |
| `ATU_MED_TOTAL_DELTA1` | 8,63% |
| `ABANDONO_MED_LAG1` | 8,33% |

### Como interpretar

- **TDI em primeiro lugar nos três casos.** Achado consistente,
  independente do modelo ou da etapa.
- **Importância preditiva ≠ causalidade.** Escrever "contribuiu para
  a previsão", não "causa".
- **Confirmar com permutation importance** e SHAP antes de publicar.
- **Atenção ao v1_old:** o modelo AF viu features do EM. Se for
  reproduzir, corrigir primeiro (aplicar D15).

## 17. Outliers

- RMSE > MAE em todos os modelos.
- **Análise específica necessária:** onde o modelo erra mais?
- Para um sistema preventivo, não adianta ter bom erro médio se
  justamente as escolas que terão 20% de abandono recebem previsão
  de 4%.

## 18. Instabilidade temporal

- R² positivo em 2025, negativo em 2024 (v1_old).
- **É questão científica, não bug.**
- Walk-forward tornaria explícito.
- Hipóteses:
  - Pico de 2022 distorce o treino.
  - Poucas observações por ano (~250 escolas).
  - Mudança de comportamento pós-pandemia.

## 19. Distinção importante

- **Importância de variável** ≠ causalidade.
- **R² 0,20** ≠ acurácia 20%.
- **Recall@K** é mais aderente ao uso real.
- **Baseline precisa ser reportado** para dar sentido aos números.

## 20. Estado científico atual

**O que foi demonstrado:**

- Existe sinal preditivo nos dados.
- TDI é a variável mais associada à previsão.
- Pipeline funciona.

**O que ainda não foi demonstrado:**

- Robustez do modelo entre anos.
- Comparação com baseline.
- Ganho operacional real (Recall@K).
- Generalização para 2026.

**Próximo passo:** corrigir pipeline e congelar metodologia antes de
tentar melhorar resultado.