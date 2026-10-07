# 07 — Planos

O que fazer nas próximas fases. Cada fase entrega um resultado
utilizável — não se começa a próxima sem fechar a anterior.

---

## Princípios gerais

1. **Corrigir antes de melhorar.** Não adianta trocar de algoritmo se
   o pipeline está furado.
2. **Congelar metodologia.** Uma vez definido o desenho, não mexer
   para "ver se melhora".
3. **Documentar decisões.** Toda escolha vai para
   `06_DECISOES_PROBLEMAS_PERGUNTAS.md`.
4. **Comparar com baseline sempre.**
5. **Um resultado utilizável por fase.**

---

# Fase 2 — Pipeline limpo e baseline

**Objetivo:** corrigir os 4 problemas do v1, adicionar baseline,
validar walk-forward.

## Passos

### 2.1 Corrigir o pipeline

- [ ] Filtrar `REDE_PUBLICA == 1`.
- [ ] Corrigir imputação (`select_dtypes(include='number')`).
- [ ] Mover imputação para dentro do `Pipeline`.
- [ ] Incluir categóricas via `ColumnTransformer`.
- [ ] Verificar ausência de leakage temporal.
- [ ] Verificar ausência de alvos irmãos como features.

### 2.2 Adicionar baseline de persistência

- [ ] Calcular `MAE`, `RMSE`, `R²` do baseline
      ("abandono(t+1) = abandono(t)").
- [ ] Reportar junto com os modelos.

### 2.3 Validar walk-forward

- [ ] Treinar em 2019–2020 → testar 2021.
- [ ] Treinar em 2019–2021 → testar 2022.
- [ ] Treinar em 2019–2022 → testar 2023.
- [ ] Treinar em 2019–2023 → testar 2024.
- [ ] Treinar em 2019–2024 → testar 2025.
- [ ] Reportar R² por fold.
- [ ] Discutir estabilidade temporal.

### 2.4 Decidir sobre o pico de 2022

- [ ] Conversar com o orientador (Q4).
- [ ] Implementar a decisão no split.

### 2.5 Congelar metodologia

- [ ] Documentar a versão final do pipeline.
- [ ] Registrar decisões em `06_DECISOES_PROBLEMAS_PERGUNTAS.md`.

## Saída

- Notebook `02_pipeline_limpo.ipynb`.
- Métricas comparadas com baseline.
- Walk-forward completo.

## Documentar

- `06_DECISOES_PROBLEMAS_PERGUNTAS.md` — o que mudou em relação ao
  v1.
- `04_EXPERIMENTOS.md` — resultados limpos.

---

# Fase 3 — Enriquecimento

**Objetivo:** incorporar as variáveis discutidas com o orientador.

## Passos (em ordem de prioridade)

### 3.1 Escola indígena e localização diferenciada

- [ ] Extrair do Censo: `IN_ESCOLA_INDIGENA`, terra indígena,
      assentamento.
- [ ] Adicionar como colunas.
- [ ] Não usar como features por ora — usar para avaliar desempenho
      por grupo.

### 3.2 Flag de elegibilidade

- [ ] Criar `elegivel_analise` (0/1).
- [ ] Manter todas as escolas na base; filtrar só na hora de treinar.

### 3.3 Flag de multisseriada

- [ ] Criar `multisseriada`.
- [ ] Onde não houver média dos anos finais, usar a do fundamental.
- [ ] Criar coluna indicadora de substituição.

### 3.4 IED 2019–2020 e HAD

- [ ] Confirmar com o orientador (Q5).
- [ ] Se consistente, incluir na base.

### 3.5 Pé-de-Meia

- [ ] Criar flag pré/pós-2024.
- [ ] Se houver dados por escola, incluir nº de beneficiários / %.
- [ ] Analisar EM (atingido) vs. AF (não atingido).

### 3.6 INSE

- [ ] Carregar para 2019, 2021, 2023.
- [ ] Usar apenas para comparação de grupos.

## Saída

- Base enriquecida.
- `docs/metodologia_variaveis.md` atualizado.

## Documentar

- Cada nova variável em `02_DADOS.md` §32.
- Decisão de uso (feature ou análise) em
  `06_DECISOES_PROBLEMAS_PERGUNTAS.md`.

---

# Fase 4 — Classificação e Recall@K

**Objetivo:** transformar o problema em classificação binária e
avaliar com Recall@K.

## Passos

### 4.1 Definir "alto risco"

- [ ] Escolher limiar (5%? 10%? percentil 80?).
- [ ] Decisão com o orientador (Q10).

### 4.2 Treinar classificadores

- [ ] RandomForestClassifier.
- [ ] HistGradientBoostingClassifier.
- [ ] LogisticRegression (baseline).

### 4.3 Métricas

- [ ] Precisão, recall, F1.
- [ ] ROC-AUC, PR-AUC.
- [ ] **Recall@10, Recall@20, Recall@30, Recall@50.**
- [ ] Precision@10, Precision@20, Precision@30, Precision@50.

### 4.4 Comparar com baseline

- [ ] Baseline: ordenar pelo abandono em `t`.
- [ ] Reportar tabela lado a lado.

### 4.5 Análise de erros

- [ ] Onde o modelo erra mais?
- [ ] Que tipo de escola é mal prevista?
- [ ] Análise por grupo (capital/interior, indígena/rural,
      pequena/grande).

## Saída

- Notebook `03_classificacao.ipynb`.
- Tabela de Recall@K.
- Análise de erros.

---

# Fase 5 — Refinamento e publicação

**Objetivo:** consolidar resultados, escrever artigo e relatório.

## Passos

### 5.1 Refinamento

- [ ] Busca de hiperparâmetros (GridSearchCV simples).
- [ ] Comparar modelos finais.
- [ ] Análise de importância de variáveis (permutation importance,
      SHAP).
- [ ] Comparar anos finais vs. EM (efeito Pé-de-Meia).

### 5.2 Reprodutibilidade

- [ ] Congelar a base usada (sha256).
- [ ] Documentar todas as decisões.
- [ ] Documentar todos os problemas.
- [ ] README final com passo a passo.

### 5.3 Publicação

- [ ] Artigo da disciplina de Mineração de Dados.
- [ ] Relatório PIBIC.

## Saída

- Resultados finais consolidados.
- Artigo + relatório.

---

# Roadmap visual

```text
Fase 2 (pipeline limpo)
        │
        ▼
Fase 3 (enriquecimento)
        │
        ▼
Fase 4 (classificação + Recall@K)
        │
        ▼
Fase 5 (refinamento + publicação)
```

---

# Resumo do que fazer agora

**Próximo passo concreto:** Fase 2.

1. Corrigir os 4 problemas do v1.
2. Adicionar baseline.
3. Rodar walk-forward.
4. Decidir pico de 2022 com o orientador.

**Depois:** Fase 3. Enriquecimento só depois que o pipeline estiver
limpo.