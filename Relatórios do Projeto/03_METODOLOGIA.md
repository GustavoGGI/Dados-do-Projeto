# 03 — Metodologia

Como o problema é formulado, quais colunas entram em cada etapa, como
o pipeline é montado, como o modelo é validado e como é avaliado.

---

# Parte A — Desenho e variáveis

## 1. Formulação

### 1.1 Pergunta operacional

> Dados os indicadores educacionais de uma escola de Roraima no ano
> `t`, qual a taxa de abandono esperada no ano `t+1` — nos anos finais
> do ensino fundamental e no ensino médio?

### 1.2 Unidade de análise

- **Escola-ano.** Cada linha é uma escola em um ano.
- Não é previsão por aluno, por turma ou por série específica.
- Alvo é uma taxa agregada, na escala percentual (0 a 100).

### 1.3 Desenho `t → t+1`

- Features: colunas do ano `t`.
- Alvo: coluna `*_T1` (do ano `t+1`).
- Colunas `_LAG1` (t−1) e `_DELTA1` (variação t − (t−1)) também são
  features legítimas.
- **Nunca** usar informação de `t+1` como feature.

### 1.4 Dois conjuntos separados

| Conjunto | Etapa | Alvo | Universo |
|---|---|---|---|
| **AF** | Anos finais (9º) | `ABANDONO_FUN_AF_T1` | Escolas que oferecem anos finais |
| **EM** | Ensino médio | `ABANDONO_MED_T1` | Escolas que oferecem EM |

**Por que separar:**

- Etapas têm redes, distribuições e comportamentos distintos.
- Missing estrutural é diferente.
- Permite comparar etapa atingida por política (Pé-de-Meia no EM) com
  etapa não atingida.

### 1.5 Um modelo por etapa

Não se treina um modelo único. Cada modelo vê só as features da sua
etapa. Evita padrões espúrios por causa do missing.

---

## 2. Features por etapa

### 2.1 Anos finais (AF)

**Numéricas:**

- `ATU_FUN_AF`, `ATU_FUN_TOTAL`.
- `TDI_FUN_AF`, `TDI_FUN_TOTAL`.
- `APROVACAO_FUN_AF`, `REPROVACAO_FUN_AF`, `ABANDONO_FUN_AF`.
- `ABANDONO_FUN_AF_LAG1`, `ABANDONO_FUN_AF_DELTA1`.
- `TDI_FUN_AF_DELTA1`, `ATU_FUN_AF_DELTA1`.
- `IED_FUN_ALTO`, `IED_FUN_N1`–`IED_FUN_N6`.
- `ATU_FUN_AI`, `TDI_FUN_AI`, `APROVACAO_FUN_AI`, `REPROVACAO_FUN_AI`,
  `ABANDONO_FUN_AI` (contexto).

**Flags:** `DISP_ATU`, `DISP_TDI`, `DISP_IED`, `DISP_REND`.

**Categóricas:** `LOCALIZACAO`, `DEPENDENCIA`, `CO_MUNICIPIO`.

### 2.2 Ensino médio (EM)

**Numéricas:**

- `ATU_MED_TOTAL`, `TDI_MED_TOTAL`.
- `APROVACAO_MED`, `REPROVACAO_MED`, `ABANDONO_MED`.
- `ABANDONO_MED_LAG1`, `ABANDONO_MED_DELTA1`.
- `TDI_MED_TOTAL_DELTA1`, `ATU_MED_TOTAL_DELTA1`.
- `IED_MED_ALTO`, `IED_MED_N1`–`IED_MED_N6`.
- Features do fundamental como contexto (decisão em aberto).

**Flags e categóricas:** iguais às do AF.

### 2.3 Nunca usar como feature

- **IDs e metadados:** `CO_ENTIDADE`, `NO_ENTIDADE`, `NO_MUNICIPIO`,
  `ANO`, `ANO_ALVO`.
- **Alvos irmãos:** para AF, remover `ABANDONO_MED_T1`; para EM,
  remover `ABANDONO_FUN_AF_T1`. Mesmo período, vazamento direto.
- **O próprio alvo.**

---

## 3. Leakage — as duas formas

### 3.1 Temporal

Usar informação de `t+1` para prever `t+1`. **Regra:** features vêm
de `t` ou antes.

### 3.2 Entre alvos

Os três `_T1` são do mesmo período. Usar um para prever o outro é
vazamento direto. **Regra:** sempre remover os outros `_T1`.

---

## 4. Decisões em aberto sobre features

### 4.1 Features cruzadas entre etapas

Usar features do EM para prever AF (ou vice-versa) implica imputar
metade dos valores (escolas que não oferecem a outra etapa).
**Decisão atual:** manter cada modelo apenas com features da sua
etapa + do fundamental como contexto.

### 4.2 Categóricas

- `LOCALIZACAO` (2), `DEPENDENCIA` (4), `CO_MUNICIPIO` (15).
- **Decisão:** One-Hot para todas. Simples, interpretável, sem risco
  de leakage.

### 4.3 Pico de 2022

Três opções em aberto:

- **A:** incluir 2022 no treino normalmente.
- **B:** treinar sem 2022, testar em 2023+.
- **C:** usar 2022 como teste natural (treinar em anos "normais").

Recomendação preliminar: B ou C.

---

# Parte B — Pipeline

## 5. Ordem correta do pipeline

1. Carregar a base.
2. Filtrar para o alvo (AF ou EM).
3. Filtrar apenas escolas públicas (`REDE_PUBLICA == 1`).
4. Remover linhas com alvo nulo.
5. **Separar treino / validação / teste.**
6. **Ajustar o pré-processamento só no treino.**
7. **Aplicar no teste.**
8. Treinar o modelo.
9. Avaliar.

**Fazer 6 e 7 antes de 5 é leakage.**

## 6. Tratamento de missing

O missing é **estrutural**. Decisões:

- **Não imputar tudo cegamente.** Escola sem EM não deve ter
  `IED_MED_ALTO` imputado.
- **Filtrar por etapa primeiro.**
- **Imputar apenas o que sobrar.**

### 6.1 Imputer

```python
numeric_transformer = Pipeline([
    ('imputer', SimpleImputer(strategy='median')),
    ('scaler',  StandardScaler()),
])
categorical_transformer = Pipeline([
    ('imputer', SimpleImputer(strategy='constant', fill_value='Missing')),
    ('onehot',  OneHotEncoder(handle_unknown='ignore', sparse_output=False)),
])
```

Mediana porque há outliers fortes. `handle_unknown='ignore'`
para o teste não quebrar com categoria nova.

### 6.2 ColumnTransformer

```python
preprocessor = ColumnTransformer([
    ('num', numeric_transformer, num_cols),
    ('cat', categorical_transformer, cat_cols),
], remainder='drop')
```

`num_cols` e `cat_cols` definidos **depois** de remover alvo e alvos
irmãos. Erro comum: definir antes e incluir o alvo por engano.

---

## 7. Split

### 7.1 Aleatório

- Sorteio dentro do mesmo ano.
- **Uso:** apenas smoke test.
- **Problema:** superestima. Modelo vê escolas do mesmo ano no treino
  e teste.

### 7.2 Temporal

- Treina em anos anteriores, testa no seguinte.
- **Uso:** avaliação realista.
- **Limitação:** um único ponto de teste.

### 7.3 Walk-forward

- Treina em 2019–2020, testa 2021; treina em 2019–2021, testa 2022;
  e assim por diante.
- **Vantagem:** distribuição de R² entre folds, revela
  instabilidade.
- **Exemplo:** v1_old teve R² 0,162 no teste 2025 e R² −0,078 na
  validação 2024. Walk-forward tornaria isso explícito.

### 7.4 Decisão em aberto

| Opção | Treino | Validação | Teste |
|---|---|---|---|
| A | 2020–2022 | 2023 | 2024–2025 |
| B | 2020–2021 + 2023 | 2024 | 2025 |
| C | walk-forward | | |

Recomendação preliminar: B ou C.

---

## 8. Baseline de persistência

Antes de qualquer modelo:

> Previsão de abandono(t+1) = abandono(t) da mesma escola.

**Métricas esperadas:**

- MAE ≈ 2,5 p.p.
- RMSE ≈ 3,8 p.p.
- R² = 0 (por definição).

Todo modelo precisa bater esse baseline. R² 0,20 e MAE 2,4 é
marginalmente melhor. MAE 3,0 é pior, mesmo com R² positivo.

---

## 9. Problemas conhecidos no pipeline atual

O `v1.ipynb` tem 4 problemas:

### 9.1 Não filtra escolas públicas

Removido em relação ao v1_old. Privadas têm abandono menor; misturar
facilita artificialmente.
**Correção:** `df[df['REDE_PUBLICA'] == 1]`.

### 9.2 Imputação quebrada por tipo

Código filtra `float64`/`int64`, mas base usa `Float64`, `Int8`,
`Int16`. Depois um `fillna(0)` transforma ausência em zero.
**Correção:** `select_dtypes(include='number')`.

### 9.3 Imputação antes do split

Imputer aprende estatísticas do teste. Leakage sutil.
**Correção:** mover imputação para dentro do `Pipeline`.

### 9.4 Categóricas descartadas

`select_dtypes(include=[np.number])` elimina `LOCALIZACAO`,
`DEPENDENCIA`, `CO_MUNICIPIO`.
**Correção:** `ColumnTransformer`.

---

## 10. Modelos

### 10.1 Regressão (tarefa principal)

```python
modelos = {
    'Ridge': Ridge(alpha=1.0, random_state=RANDOM_STATE),
    'RandomForest': RandomForestRegressor(
        n_estimators=300, max_depth=10, min_samples_leaf=3,
        random_state=RANDOM_STATE, n_jobs=-1,
    ),
    'HistGradientBoosting': HistGradientBoostingRegressor(
        max_iter=300, learning_rate=0.05, max_depth=6,
        random_state=RANDOM_STATE,
    ),
}
```

### 10.2 Classificação (segunda tarefa, Fase 4)

Transformar alvo em binário (`abandono_t1 > limiar`). Treinar
classificadores. Avaliar com precisão/recall/F1 e Recall@K. Ver
`07_PLANOS.md`.

---

## 11. Reprodutibilidade

- `RANDOM_STATE = 1` fixo.
- `np.random.seed(RANDOM_STATE)`.
- `random_state=RANDOM_STATE` explícito em modelos e split.

---

# Parte C — Métricas

## 12. Regressão

### 12.1 MAE — Erro Médio Absoluto

```text
MAE = média(|y_real − y_previsto|)
```

Em média, por quantos pontos percentuais (p.p.) o modelo erra. Mesma
unidade do alvo. Fácil de interpretar.

### 12.2 RMSE — Raiz do Erro Quadrático Médio

```text
RMSE = sqrt(média((y_real − y_previsto)²))
```

Sempre ≥ MAE.

- Se RMSE ≈ MAE: erros uniformes.
- Se RMSE ≫ MAE: existem outliers.

### 12.3 R² — Coeficiente de Determinação

```text
R² = 1 − (SQ_resíduos / SQ_total)
```

Fração da variância do alvo explicada além da média.

- R² = 1,0 — perfeito.
- R² = 0,0 — igual a prever a média.
- R² < 0 — pior que a média.

**Armadilha:** R² não é acurácia. R² = 0,20 significa "explicou
20% da variância além da média".

No projeto: R² entre 0,10 e 0,30 é modesto mas real. R² negativo
é informação importante.

### 12.4 Como reportar

- MAE e RMSE em pontos percentuais (p.p.), não em "%".
- R² sem unidade.
- Sempre comparar com o baseline.

---

## 13. Classificação (Fase 4)

### 13.1 Acurácia

Acertos totais / total. Enganosa em classes desbalanceadas. Não
usar como métrica principal.

### 13.2 Precisão

"Das escolas apontadas como alto risco, quantas realmente eram."

`VP / (VP + FP)`

### 13.3 Recall

"Das escolas que realmente tiveram alto abandono, quantas o modelo
antecipou."

`VP / (VP + FN)`

**Métrica crítica do projeto.** Errar dizendo que uma escola não está
em risco significa perder a chance de agir preventivamente.

### 13.4 F1

Média harmônica entre precisão e recall.

### 13.5 ROC-AUC

Área sob a curva ROC. Otimista em classes desbalanceadas.

### 13.6 PR-AUC

Área sob a curva Precisão-Recall. Mais informativa em classes
desbalanceadas. **Preferir.**

---

## 14. Métricas operacionais — Recall@K

Pergunta operacional:

> Se o Estado tivesse recursos para atuar preventivamente em apenas
> 30 escolas, quantas das escolas que efetivamente apresentariam
> abandono elevado o sistema conseguiria indicar um ano antes?

### 14.1 Como calcular

1. Ordenar escolas por risco previsto (decrescente).
2. Pegar as K primeiras.
3. Comparar com as K de maior abandono real.

- **Recall@K:** das escolas que realmente tiveram alto abandono,
  quantas estão entre as K previstas.
- **Precision@K:** das K previstas, quantas realmente tiveram.

### 14.2 Valores de K

Top 10, 20, 30, 50.

### 14.3 Por que é a métrica mais importante

- Aderente ao uso real.
- Interpretável fora da estatística.
- Combina com o desenho (priorizar, não prever com precisão).

Exemplo forte: "priorizando 30 das 235 escolas, o modelo
identificou 72% das que depois tiveram abandono elevado".

---

## 15. Prioridade das métricas

1. **Recall@K** — métrica operacional principal.
2. **MAE, RMSE** — erro absoluto em p.p.
3. **R²** — capacidade explicativa global.
4. **Precision@K** — custo da priorização.
5. **PR-AUC** — classificação.
6. **Precisão, Recall, F1** — classificação.
7. **Acurácia** — só por completude.

Sempre comparar com o baseline de persistência.