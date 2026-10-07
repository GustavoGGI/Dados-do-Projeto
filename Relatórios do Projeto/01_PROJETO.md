# 01 — Projeto

Contexto, pergunta, escopo, pessoas, estado atual e glossário. Tudo
que uma IA precisa saber sobre o projeto *antes* de olhar para os
dados.

---

# Parte A — Identificação e pergunta

## 1. Identificação

- **Título:** Risco de abandono escolar em Roraima
- **Tipo:** Projeto de iniciação científica (PIBIC/UERR, Edital 35/2026)
  **e** artigo da disciplina de Mineração de Dados.
- **Orientador:** Prof. Bruno Cesar Barreto Figueiredo.
- **Instituição:** Universidade Estadual de Roraima (UERR).
- **Repositório:** https://github.com/gabsma25/abandonoescolar
- **Status em outubro/2026:** em andamento. Pipeline de dados
  concluído; modelagem em iteração. Ritmo avaliado como "ótimo" pelo
  orientador em 30/09/2026.

## 2. Pergunta de pesquisa

> Com os indicadores educacionais de uma escola de Roraima no ano `t`,
> é possível estimar a taxa de abandono esperada no ano `t+1` — nos
> anos finais do ensino fundamental e no ensino médio — para apoiar
> ações preventivas de gestão?

## 3. Escopo

### O que o projeto faz

- Trabalha com **escola-ano** como unidade de análise.
- Foca nas **escolas de Roraima**.
- Cobre **anos finais do ensino fundamental** (9º ano) e **ensino
  médio** (1ª, 2ª, 3ª série).
- Usa dados **públicos** do INEP (Censo Escolar + Indicadores
  Educacionais).
- Prevê **taxa de abandono em `t+1`**, a partir de indicadores de `t`.
- Entrega **dois modelos**: um para anos finais, um para ensino médio.

### O que o projeto NÃO faz

- **Não prevê alunos individuais.** Análise agregada no nível da
  escola.
- **Não trata de evasão.** Abandono é o aluno que deixa de frequentar
  durante o ano letivo (existe por escola). Evasão é o aluno que não
  se matricula no ano seguinte (só é publicada de forma agregada).
  Este projeto trata de **abandono**.
- **Não ranqueia nem pune escolas.** O resultado destina-se a
  priorizar escolas para diagnóstico e apoio.
- **Não é causal.** Importância preditiva não é causalidade. Dizer
  "TDI contribuiu para a previsão" ≠ "TDI causa abandono".

## 4. Justificativa

- Abandono escolar é fenômeno crítico, especialmente em Roraima, onde
  há escolas indígenas, rurais, ribeirinhas e em assentamentos com
  dinâmicas próprias.
- O Estado precisa priorizar recursos de intervenção — não há equipe
  para acompanhar todas as escolas.
- Um modelo que antecipa um ano à frente quais escolas terão abandono
  elevado permite ação preventiva.
- A separação entre anos finais e ensino médio permite comparar uma
  etapa atingida por política específica (Pé-de-Meia, no EM) com
  outra não atingida (fundamental) — comparação útil mesmo sem grupo
  de controle.

## 5. Produtos esperados

- **PIBIC:** relatório técnico-científico.
- **Disciplina:** artigo.
- **Código:** repositório público com scraper, base longitudinal e
  notebooks.
- **Base reproduzível:** sha256 do manifesto garante
  reprodutibilidade.

## 6. Base legal e ética

- Dados públicos do INEP (Lei de Acesso à Informação).
- Nenhum dado pessoal de aluno.
- Unidade de análise agregada (escola), sem identificação individual.
- Uso explicitamente não punitivo.

## 7. Delimitações temporais

- **Período coberto:** 2019 a 2025.
- **Defasagem do desfecho:** o abandono de `t+1` só é conhecido bem
  depois do fim de `t+1` (segunda etapa do Censo Escolar, coletada no
  ano seguinte).
- **Último ano com alvo conhecido:** 2025.
- **2026 em diante:** só poderá ser previsto quando o Censo
  correspondente for publicado.

---

# Parte B — Pessoas

O projeto é desenvolvido em grupo. Cada integrante contribui de forma
complementar — não há atribuição fixa de papéis; o trabalho é
distribuído conforme a necessidade de cada fase.

## Integrantes

- **Gustavo** — integrante do grupo.
- **Gabriela Monteiro** — integrante do grupo.
- **João Ricardo** — integrante do grupo.

## Orientação

- **Prof. Bruno Cesar Barreto Figueiredo** — orientador do projeto.

## Como o trabalho está organizado

- Encontros informais no grupo para alinhar o que cada um está
  fazendo.
- O orientador acompanha a evolução e dá retorno pontual sobre
  decisões metodológicas e resultados.
- Não há hierarquia rígida nem subgrupos fixos.

---

# Parte C — Estado atual

Data de referência: outubro/2026.

## Concluído

### Ambiente e dados

- Repositório clonado e rodando localmente.
- Bootstrap executado em **01/10/2026**, das 09:03 às 12:55
  (~3h52min):
  - 110 zips baixados do INEP (2,9 GB).
  - Extração, conferência por sha256, inventários, recorte de
    Roraima.
  - `git status docs/` limpo — estado reproduzido.

### Base longitudinal

- Gerada: **6.054 linhas × 59 colunas**.
- Cobre **2019–2025**, escola-ano, Roraima.
- Estrutura `ANO` (t) e `ANO_ALVO` (t+1) pronta.
- Alvos: `ABANDONO_FUN_T1`, `ABANDONO_FUN_AF_T1`, `ABANDONO_MED_T1`.
- Validações passaram: mesmas 6 escolas mudam de localização, mesmas
  105 mudam de nome ao longo da série.

### Experimentos de modelagem

- **Smoke test** (split aleatório em 2025) — validou o pipeline.
- **v1_old** — pipeline metodologicamente correto (filtra públicas,
  usa Pipeline, One-Hot, split temporal). Resultado para anos finais:
  R² 0,162 no teste 2025; R² −0,078 na validação 2024. **Ensino
  médio não foi executado.** Instabilidade temporal real entre 2024
  e 2025. Nota: o v1_old usou todas as features numéricas no modelo
  AF, inclusive do EM — contraria D15. Corrigir antes de reproduzir.
- **v1 atual** — pipeline com 4 problemas conhecidos (não filtra
  públicas, imputação quebrada por tipo, imputação antes do split,
  descarta categóricas). Resultado preliminar:
  - **AF:** RandomForest R² 0,1843 | GradientBoosting R² 0,2011.
  - **EM:** RandomForest R² 0,1214 | GradientBoosting R² 0,0907.

### Análise crítica

- Relatório do orientador (via LLM) com 12 pontos de melhoria. Aceito
  em quase totalidade.

### Achados científicos

- **TDI (distorção idade-série) é a variável mais importante** nos
  três casos analisados (v1_old AF, v1 atual AF, v1 atual EM).
  Consistente entre modelos e etapas.
- RMSE > MAE em ambos os modelos → existem outliers mal previstos.
- Modelo não generaliza entre anos (R² negativo na validação de
  2024).

## Pendente

### Dados externos do orientador

- `dados/externo/base_longitudinal_v1/` — seis arquivos entregues em
  17/09/2026, ainda ausentes no clone local.
- Necessários para comparação com a base reproduzível.
- Sha256 esperado em `dados/MANIFEST.csv`, com `estagio=externo`.

### Enriquecimento da base (Fase 3)

Ver `07_PLANOS.md`. Resumo:

- Escola indígena e localização diferenciada.
- Flag de elegibilidade.
- Flag de multisseriada.
- Esforço docente 2019–2020 e HAD.
- Pé-de-Meia.
- INSE (só para análise de grupos).

### Refinamento metodológico (Fase 2)

Ver `07_PLANOS.md`. Resumo:

- Corrigir os 4 problemas do v1 atual.
- Adicionar baseline de persistência.
- Validação walk-forward.

### Publicação

- Artigo da disciplina — pendente.
- Relatório PIBIC — pendente.

---

# Parte D — Glossário

Dois grupos: **siglas do INEP** e **termos do projeto**.

## Siglas e termos do INEP

| Sigla | Nome | O que é |
|---|---|---|
| **Censo Escolar** | Censo Escolar da Educação Básica | Microdados anuais com infraestrutura, dependências, equipamentos, profissionais, oferta, acessibilidade, escola indígena, terra indígena, assentamento. |
| **tx_rend** | Taxa de Rendimento Escolar | Aprovação, reprovação e abandono, por escola e por série. Fonte do alvo. |
| **TDI** | Taxa de Distorção Idade-Série | % de alunos com 2+ anos de atraso. |
| **ATU** | Média de Alunos por Turma | Tamanho médio das turmas. |
| **IED** | Indicador de Esforço Docente | Carga e complexidade do trabalho docente (N1–N6 + ALTO). |
| **HAD** | Média de Horas-Aula Diárias | Número médio de horas-aula por dia. |
| **INSE** | Indicador de Nível Socioeconômico | Nível socioeconômico médio dos alunos. Depende do Saeb; cobre ~metade das escolas públicas. |
| **Saeb** | Sistema de Avaliação da Educação Básica | Avaliação federal; condiciona o INSE. |
| **Pé-de-Meia** | Programa Pé-de-Meia | Programa federal em vigor desde 2024. Foca permanência e frequência no EM público. |
| **INEP** | Instituto Nacional de Estudos e Pesquisas Educacionais Anísio Teixeira | Órgão federal responsável pelos dados. |

## Termos do projeto

### Unidade de análise

- **Escola-ano.** Cada linha é uma escola em um ano.
- **Anos finais.** 6º ao 9º ano. Foco no 9º.
- **Ensino médio.** 1ª, 2ª e 3ª séries.
- **Anos iniciais.** 1º ao 5º ano. Fora do escopo, mas presente na
  base como contexto.

### Desenho

- **t → t+1.** Features do ano `t`; alvo no ano `t+1`.
- **`ANO`.** Ano de referência das features.
- **`ANO_ALVO`.** Ano do desfecho. Sempre `ANO + 1`.
- **Sufixo `_T1`.** Marca alvos ("_T1" = target do ano seguinte).
- **Sufixo `_LAG1`.** Variável do ano anterior (t−1).
- **Sufixo `_DELTA1`.** Variação anual (t − (t−1)).

### Pré-processamento

- **Leakage (vazamento).** Usar, como feature, informação que não
  estaria disponível no momento da previsão.
  - **Temporal:** features e alvo do mesmo ano.
  - **Entre alvos:** usar `ABANDONO_FUN_T1` como feature para prever
    `ABANDONO_MED_T1` (mesmo período, variável irmã).
- **Baseline de persistência.** "abandono(t+1) = abandono(t)". Todo
  modelo real precisa bater esse baseline.
- **Missing estrutural.** Ausência que reflete o que a escola oferece,
  não erro.

### Split

- **Split aleatório.** Sorteio dentro do mesmo ano. Fácil, inflado.
- **Split temporal.** Treina em anos anteriores, testa no seguinte.
- **Walk-forward.** Validação ano a ano.

### Métricas

- **MAE** — erro médio absoluto (p.p.).
- **RMSE** — raiz do erro quadrático médio (p.p.).
- **R²** — fração da variância explicada além da média. **Não é
  acurácia.** Vai de −∞ a 1; negativo = pior que a média.
- **Precisão, Recall, F1** — classificação.
- **ROC-AUC, PR-AUC** — classificação em classes desbalanceadas.
- **Recall@K / Precision@K** — métrica operacional: das K escolas
  priorizadas, quantas realmente tinham alto abandono.

### Alvo

- **Abandono.** Aluno que deixa de frequentar durante o ano letivo.
  Existe por escola. **Alvo do projeto.**
- **Evasão.** Aluno que não se matricula no ano seguinte. Publicada
  agregada. **Não é o alvo.**
- **Zeros no alvo.** Alta fração de escolas com taxa = 0.